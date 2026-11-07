"""Core monthly loop. Structure only; economics lives in the pure modules.

Timing within a month t (full description: v3/docs/model-spec.md):
  1. rebates due this month reach households (and the state's cost); loan payments fall due; energy bills saved accrue
  2. canvassing pressure and building adoption shares are read (a snapshot: nobody reacts to decisions of this month)
  3. each household that "considers" evaluates its own part (NPV and financing) and, if its building has a shared
     measure not yet approved, whether it supports it
  4. public-service capacity (whole slots per month) is rationed among the subsidised candidates; chosen candidates pay
  5. buildings whose floor-area support reaches the threshold approve the shared measure if every owner can pay
     their floor-area share (and, for the public service, ceil(units x shared_share) slots are left); all owners then pay it
  6. a frame is emitted

All floating-point sums are plain loops in unit-id order so the JavaScript port agrees.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Callable, List, Optional, Tuple

from .common.rng import Rng, hash_uniform
from .credit import credit_limit
from .delivery import DELIVERY, QuoteContext
from .financing import loan_payment, plan_financing
from .frames import FRAME_SCHEMA_VERSION, Frame
from .npv import monthly_rate, npv_retrofit
from .ownership import OWNERSHIP
from .params import Params
from .results import AdoptionEvent, Result, VoteEvent
from .scene_entities import build_entities, synthetic_table

FREE_TIME_KEY = 1073741825      # hash_uniform stream for free-time spread (consideration uses j = month)


@dataclass
class _Unit:
    uid: int
    bidx: int
    area: float
    income: float
    tax: float
    savings: float
    horizon: int          # months the household expects to stay
    queue_draw: float
    quintile: int = 0
    free_hours: float = 0.0       # weekly hours neither worked nor committed
    tax_left: float = 0.0         # tax capacity not yet used by a rebate
    unit_base: float = 0.0        # base cost of the unit's own part
    shared_base: float = 0.0      # base cost of this unit's floor-area share of the shared measure
    needs_shared: bool = False
    unit_done: bool = False
    shared_paid: bool = False
    supporter: bool = False
    complete: bool = False
    paid_any: bool = False
    saving_frac: float = 0.0
    paid_price: float = 0.0
    paid_base: float = 0.0
    cash_net: float = 0.0
    loans: list = field(default_factory=list)   # (monthly payment, last month it falls due)


@dataclass
class _Eval:
    quote: object
    limit: float
    from_savings: float
    loan: float
    loan_rate: float
    npv: float


def _retenure(p: Params, buildings):
    """Apply Params.rental_share_* (PLACEHOLDER tenure rule) to buildings that carry their scene draw; others keep their tenure."""
    if p.rental_share_single is None and p.rental_share_multi is None:
        return buildings
    out = []
    for b in buildings:
        share = p.rental_share_single if b.units == 1 else p.rental_share_multi
        if b.rental_draw is None or share is None:
            out.append(b)
            continue
        tenure = "rental" if b.rental_draw < share else ("owner_occupied" if b.units == 1 else "condo")
        out.append(replace(b, tenure=tenure))
    return tuple(out)


def _population(p: Params, buildings):
    rng = Rng(p.seed)
    units, by_building = [], []
    uid = 0
    for bi, b in enumerate(buildings):
        ids = []
        for area in b.unit_areas:
            income = rng.lognormal(p.income_log_mean, p.income_log_sd)
            sav = rng.lognormal(0.0, p.savings_log_sd) * p.savings_scale * p.savings_months_of_income * income / 12.0
            yrs = rng.uniform(p.years_in_dwelling_min, p.years_in_dwelling_max)
            qd = rng.random()
            tax = max(0.0, p.tax_rate * (income - p.tax_free_allowance))
            units.append(_Unit(uid, bi, area, income, tax, sav, int(round(yrs * 12)), qd, tax_left=tax))
            ids.append(uid)
            uid += 1
        by_building.append(ids)
    order = sorted(range(len(units)), key=lambda i: (units[i].income, i))
    n = len(units)
    for rank, i in enumerate(order):
        units[i].quintile = min(5, 1 + rank * 5 // n) if n else 1
    for u in units:
        base = max(0.0, p.waking_hours_per_week - p.committed_hours_per_week - p.work_hours_by_quintile[u.quintile - 1])
        spread = 1.0 + p.free_time_spread * (2.0 * hash_uniform(p.seed, u.uid, FREE_TIME_KEY) - 1.0)
        u.free_hours = max(0.0, base * spread)
    return units, by_building


class Simulation:
    """Stepwise simulation. Mirrors the JavaScript `Simulation` class."""

    def __init__(self, params: Params):
        p = self.p = params
        buildings = p.buildings
        if not buildings:
            buildings = build_entities(synthetic_table(p.n_buildings, p.scene_seed), p.scene_rules, p.scene_seed).buildings
        buildings = _retenure(p, buildings)
        self.buildings = buildings
        self.units, self.by_b = _population(p, buildings)
        self.mode = DELIVERY[p.delivery_mode]
        self.r_m = monthly_rate(p.discount_rate)
        self.g_m = monthly_rate(p.energy_growth_annual)
        self.adopted_in_b = [0] * len(buildings)
        self.needs_shared = [p.shared_measure and OWNERSHIP[b.tenure].has_shared_parts(b) for b in buildings]
        self.approved = [False] * len(buildings)
        self.pending: dict = {}              # month -> [(unit id, rebate cash)]
        self.events: List[AdoptionEvent] = []
        self.votes: List[VoteEvent] = []
        self.public_cost = self.bills_saved = 0.0
        self.price_sum = self.base_sum = 0.0
        self.n_complete = 0
        self.q_trans = [0.0] * 5
        self.q_price = [0.0] * 5
        self.q_adopt = [0] * 5
        self.q_total = [0] * 5
        for u in self.units:
            self.q_total[u.quintile - 1] += 1
        self.carry = 0.0
        self.quota = p.public_capacity * len(self.units) / 12.0
        self.t = 0
        self._prepare_costs()
        self.frame = self._make_frame(0)

    # ---- setup ----
    def _prepare_costs(self):
        p = self.p
        for bi, b in enumerate(self.buildings):
            ids = self.by_b[bi]
            floor = 0.0
            for i in ids:
                floor += self.units[i].area
            shared_total = p.shared_share * p.cost_per_m2 * floor
            for i in ids:
                u = self.units[i]
                u.needs_shared = self.needs_shared[bi]
                if u.needs_shared:
                    u.unit_base = u.area * p.cost_per_m2 * (1.0 - p.shared_share)
                    u.shared_base = shared_total * u.area / floor      # cost split by floor area
                else:
                    u.unit_base = u.area * p.cost_per_m2

    # ---- small helpers ----
    def _can_adopt(self, bi: int) -> bool:
        b = self.buildings[bi]
        return OWNERSHIP[b.tenure].can_adopt(b)

    def _unit_frac(self, u) -> float:
        return (1.0 - self.p.shared_share) if u.needs_shared else 1.0

    def _limit(self, u) -> float:
        p = self.p
        return credit_limit(p.credit_access, u.income, income_threshold=p.credit_income_threshold,
                            loan_to_income_cap=p.credit_loan_to_income)

    def _loan_rate(self, u) -> float:
        p = self.p
        return p.loan_rate + (p.loan_rate_risk_premium if u.income < p.credit_income_threshold else 0.0)

    def _quote(self, u, base: float):
        return self.mode.quote(QuoteContext(base, u.tax_left, u.quintile, self.p))

    def _is_advocate(self, u) -> bool:
        return u.supporter or u.paid_any

    def _spend(self, u) -> float:
        """Weekly canvassing hours of a household: advocates in co-owned buildings, within their free time."""
        b = self.buildings[u.bidx]
        if not self._is_advocate(u) or not OWNERSHIP[b.tenure].has_shared_parts(b):
            return 0.0
        return min(u.free_hours, self.p.canvass_target_hours)

    def _evaluate(self, u, base: float, frac: float, t: int, level: float) -> Optional[_Eval]:
        """Quote, financing and NPV of paying `base` (a part of the retrofit) now. None if it cannot be financed."""
        p = self.p
        quote = self._quote(u, base)
        lim = from_sav = loan = 0.0
        rate = self._loan_rate(u)
        if quote.requires_financing:
            lim = self._limit(u)
            plan = plan_financing(quote.household_upfront, u.savings, lim, p.savings_usable_share)
            if not plan.feasible:
                return None
            from_sav, loan = plan.from_savings, plan.loan
        v = npv_retrofit(
            monthly_saving=u.area * p.saving_per_m2_year / 12.0 * frac * level,
            horizon_months=u.horizon - t, monthly_discount=self.r_m, monthly_energy_growth=self.g_m,
            cash_from_savings=from_sav, loan_payment=loan_payment(loan, rate, p.loan_term_months),
            loan_months=p.loan_term_months, rebate=quote.rebate, rebate_lag_months=quote.rebate_lag_months)
        return _Eval(quote, lim, from_sav, loan, rate, v)

    def _pay(self, u, ev: _Eval, kind: str, base: float, frac: float, t: int):
        """The household pays for a part: books the event, the state's outlay, the rebate and the loan."""
        p, q = self.p, ev.quote
        self.public_cost += q.state_pays_now
        if q.rebate:
            if q.rebate_lag_months == 0:        # lag 0 = paid in the month of the retrofit (phase 1 of this month has already run)
                self.public_cost += q.rebate
                u.cash_net += q.rebate
            else:                               # lag is a whole number >= 1 (Params rounds it): delivered in phase 1 of month t + lag
                self.pending.setdefault(t + q.rebate_lag_months, []).append((u.uid, q.rebate))
        k = u.quintile - 1
        self.q_price[k] += q.price
        self.q_trans[k] += q.state_pays_now + q.rebate
        self.events.append(AdoptionEvent(t, u.uid, self.buildings[u.bidx].id, u.quintile, self.mode.name, q.price,
                                         ev.from_savings, ev.loan, u.savings, ev.limit, q.state_pays_now, q.rebate,
                                         q.rebate_lag_months, u.tax_left, kind, base, q.eligible))
        u.savings -= ev.from_savings
        u.cash_net -= ev.from_savings
        u.tax_left = max(0.0, u.tax_left - q.rebate)
        if ev.loan > 0:
            u.loans.append((loan_payment(ev.loan, ev.loan_rate, p.loan_term_months), t + p.loan_term_months))
        u.paid_any = True
        u.paid_price += q.price
        u.paid_base += base
        u.saving_frac += frac
        if kind == "shared":
            u.shared_paid = True
        else:
            u.unit_done = True
        if u.unit_done and (u.shared_paid or not u.needs_shared) and not u.complete:
            u.complete = True
            self.adopted_in_b[u.bidx] += 1
            self.q_adopt[k] += 1
            self.price_sum += u.paid_price
            self.base_sum += u.paid_base
            self.n_complete += 1

    def _yes_share(self, bi: int) -> float:
        yes = tot = 0.0
        for i in self.by_b[bi]:
            u = self.units[i]
            tot += u.area
            if u.supporter:
                yes += u.area
        return yes / tot if tot else 0.0

    # ---- frame ----
    def _make_frame(self, t: int) -> Frame:
        p, buildings, units = self.p, self.buildings, self.units
        bfr, counts = [], {"not_retrofitted": 0, "partial": 0, "retrofitted": 0, "not_modelled": 0}
        shared_counts = {"pending": 0, "approved": 0}
        tenure_counts = {"owner_occupied": 0, "condo": 0, "rental": 0}
        # can each not-yet-retrofitted unit finance what it still has to pay now? (per quintile, and per building)
        front_tot, front_ok, cannot_in_b = [0] * 5, [0] * 5, [0] * len(buildings)
        for u in units:
            if u.complete or not self._can_adopt(u.bidx):
                continue
            base = (0.0 if u.unit_done else u.unit_base) + (u.shared_base if (u.needs_shared and not u.shared_paid) else 0.0)
            quote = self._quote(u, base)
            ok = (not quote.requires_financing) or plan_financing(quote.household_upfront, u.savings, self._limit(u), p.savings_usable_share).feasible
            front_tot[u.quintile - 1] += 1
            if ok:
                front_ok[u.quintile - 1] += 1
            else:
                cannot_in_b[u.bidx] += 1
        for bi, b in enumerate(buildings):
            if not self._can_adopt(bi):
                state = "not_modelled"
            elif self.adopted_in_b[bi] == 0:
                state = "not_retrofitted"
            elif self.adopted_in_b[bi] < b.units:
                state = "partial"
            else:
                state = "retrofitted"
            counts[state] += 1
            tenure_counts[b.tenure] += 1
            if not self.needs_shared[bi]:
                sstate, yes = "none", 0.0
            elif self.approved[bi]:
                sstate, yes = "approved", self._yes_share(bi)
                shared_counts["approved"] += 1
            else:
                sstate, yes = "pending", self._yes_share(bi)
                shared_counts["pending"] += 1
            qs = [units[i].quintile for i in self.by_b[bi]]
            bfr.append({"id": b.id, "state": state, "tenure": b.tenure, "units": b.units,
                        "adopted_share": self.adopted_in_b[bi] / b.units,
                        "income_q_mean": sum(qs) / len(qs), "shared_state": sstate, "vote_yes_share": yes,
                        "units_cannot_front": cannot_in_b[bi]})
        front = [front_ok[k] / front_tot[k] if front_tot[k] else None for k in range(5)]
        canv, leis, cash_sum, cash_n = [0.0] * 5, [0.0] * 5, [0.0] * 5, [0] * 5
        for u in units:
            k = u.quintile - 1
            s = self._spend(u)
            canv[k] += s
            leis[k] += u.free_hours - s
            if u.paid_any:
                cash_sum[k] += u.cash_net
                cash_n[k] += 1
        n = self.n_complete
        series = {
            "adoption_by_quintile": [self.q_adopt[k] / self.q_total[k] if self.q_total[k] else 0.0 for k in range(5)],
            "rebate_per_euro": [self.q_trans[k] / self.q_price[k] if self.q_price[k] else None for k in range(5)],
            "can_front_cost": front,
            "cost_per_retrofit": self.price_sum / n if n else None,
            "public_cost": self.public_cost,
            "bills_saved": self.bills_saved,
            "state_counts": counts,
            "adopted_units": n,
            "cost_per_retrofit_parts": {"base": self.base_sum / n, "markup": (self.price_sum - self.base_sum) / n} if n else None,
            "canvass_hours_by_quintile": [canv[k] / self.q_total[k] if self.q_total[k] else 0.0 for k in range(5)],
            "leisure_hours_by_quintile": [leis[k] / self.q_total[k] if self.q_total[k] else 0.0 for k in range(5)],
            "net_cash_by_quintile": [cash_sum[k] / cash_n[k] if cash_n[k] else None for k in range(5)],
            "shared_counts": shared_counts,
            "tenure_counts": tenure_counts,
        }
        return {"schema": FRAME_SCHEMA_VERSION, "t": t, "year": t / 12.0, "buildings": bfr, "series": series}

    # ---- step ----
    def step(self) -> Frame:
        p, t, units, buildings = self.p, self.t, self.units, self.buildings
        # 1. cash arriving and leaving
        for uid, amount in self.pending.pop(t, []):
            self.public_cost += amount
            units[uid].cash_net += amount
        level = (1.0 + self.g_m) ** t
        for u in units:
            for pay, last in u.loans:
                if t <= last:
                    u.cash_net -= pay
            if u.saving_frac > 0 and t < u.horizon:
                bill = u.area * p.saving_per_m2_year / 12.0 * u.saving_frac * level
                self.bills_saved += bill
                u.cash_net += bill
        # 2. snapshot
        snapshot = list(self.adopted_in_b)
        spend = [self._spend(u) for u in units]
        canv_total = [0.0] * len(buildings)
        for u in units:
            canv_total[u.bidx] += spend[u.uid]
        nb = p.neighbour_boost if p.peer_effect else 0.0
        # 3. considerations
        candidates = []
        for u in units:
            b = buildings[u.bidx]
            own = OWNERSHIP[b.tenure]
            if u.complete or not own.can_adopt(b) or t >= u.horizon:
                continue
            pressure = min(1.0, max(0.0, canv_total[u.bidx] - spend[u.uid]) / p.canvass_saturation_hours)
            prob = own.consider_probability(p.consider_prob_base, nb, snapshot[u.bidx] / b.units, p.canvass_boost, pressure)
            if hash_uniform(p.seed, u.uid, t) >= prob:
                continue
            if not u.unit_done:
                ev = self._evaluate(u, u.unit_base, self._unit_frac(u), t, level)
                if ev is not None and ev.npv > 0:
                    candidates.append((u, ev))
            if u.needs_shared and not self.approved[u.bidx] and not u.supporter:
                ev = self._evaluate(u, u.shared_base, p.shared_share, t, level)
                if ev is not None and ev.npv > 0:
                    u.supporter = True
        # 4. capacity, then payment
        slots_left = None
        if self.mode.name == "public_service":
            slots = int(self.quota + self.carry)
            self.carry = self.quota + self.carry - slots
            limited = sorted((c for c in candidates if c[1].quote.capacity_limited), key=lambda c: (c[0].queue_draw, c[0].uid))
            allowed = {c[0].uid for c in limited[:slots]}
            candidates = [c for c in candidates if (not c[1].quote.capacity_limited) or c[0].uid in allowed]
            slots_left = slots - len(allowed)
        for u, ev in candidates:
            self._pay(u, ev, "unit" if u.needs_shared else "whole", u.unit_base, self._unit_frac(u), t)
        # 5. shared-measure votes
        for bi, b in enumerate(buildings):
            if not self.needs_shared[bi] or self.approved[bi]:
                continue
            yes = self._yes_share(bi)
            if yes + 1e-9 < p.vote_threshold:
                continue
            need = 0
            if slots_left is not None:      # the public service does the shared work too: it needs capacity
                need = math.ceil(b.units * p.shared_share - 1e-9)
                if need > slots_left:
                    continue
            evs = []
            for i in self.by_b[bi]:
                u = units[i]
                e = self._evaluate(u, u.shared_base, p.shared_share, t, level)
                if e is None:
                    evs = None
                    break
                evs.append((u, e))
            if evs is None:
                continue                    # some owner cannot pay their share: the measure is blocked
            self.approved[bi] = True
            if slots_left is not None:
                slots_left -= need
            self.votes.append(VoteEvent(t, b.id, yes, p.vote_threshold, need))
            for u, e in evs:
                self._pay(u, e, "shared", u.shared_base, p.shared_share, t)
        self.t = t + 1
        self.frame = self._make_frame(self.t)
        return self.frame


def run_simulation(params: Params, on_step: Optional[Callable[[Frame], None]] = None) -> Result:
    sim = Simulation(params)
    frames: list = []

    def emit(fr: Frame):
        if params.keep_frames:
            frames.append(fr)
        if on_step is not None:
            on_step(fr)

    emit(sim.frame)
    for _ in range(params.horizon_months):
        emit(sim.step())
    return Result(params, frames, tuple(sim.events), tuple(sim.votes), sim.frame, len(sim.units), len(sim.buildings))
