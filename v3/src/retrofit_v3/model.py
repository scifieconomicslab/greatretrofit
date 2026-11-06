"""Core monthly loop. Structure only; economics lives in the pure modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .common.rng import Rng, hash_uniform
from .credit import credit_limit
from .delivery import DELIVERY, QuoteContext
from .financing import loan_payment, plan_financing
from .frames import FRAME_SCHEMA_VERSION, Frame
from .npv import monthly_rate, npv_retrofit
from .ownership import OWNERSHIP
from .params import Params
from .results import AdoptionEvent, Result
from .scene_entities import build_entities, synthetic_table


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
    adopted: bool = False


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
            units.append(_Unit(uid, bi, area, income, tax, sav, int(round(yrs * 12)), qd))
            ids.append(uid)
            uid += 1
        by_building.append(ids)
    order = sorted(range(len(units)), key=lambda i: (units[i].income, i))
    n = len(units)
    for rank, i in enumerate(order):
        units[i].quintile = min(5, 1 + rank * 5 // n) if n else 1
    return units, by_building


def run_simulation(params: Params, on_step: Optional[Callable[[Frame], None]] = None) -> Result:
    p = params
    buildings = p.buildings
    if not buildings:
        buildings = build_entities(synthetic_table(p.n_buildings, p.scene_seed), p.scene_rules, p.scene_seed).buildings
    units, by_b = _population(p, buildings)
    n_units = len(units)
    mode = DELIVERY[p.delivery_mode]
    r_m = monthly_rate(p.discount_rate)
    g_m = monthly_rate(p.energy_growth_annual)
    adopted_in_b = [0] * len(buildings)
    pending: dict[int, float] = {}       # month -> rebate cash paid out
    events: list[AdoptionEvent] = []
    public_cost = bills_saved = 0.0
    price_sum = 0.0
    q_trans = [0.0] * 5; q_price = [0.0] * 5; q_adopt = [0] * 5
    q_total = [0] * 5
    for u in units:
        q_total[u.quintile - 1] += 1
    carry = 0.0
    frames: list = []

    def make_frame(t: int) -> Frame:
        bfr, counts = [], {"not_retrofitted": 0, "partial": 0, "retrofitted": 0, "not_modelled": 0}
        for bi, b in enumerate(buildings):
            if not OWNERSHIP[b.tenure].can_adopt(b):
                state = "not_modelled"
            elif adopted_in_b[bi] == 0:
                state = "not_retrofitted"
            elif adopted_in_b[bi] < b.units:
                state = "partial"
            else:
                state = "retrofitted"
            counts[state] += 1
            qs = [units[i].quintile for i in by_b[bi]]
            bfr.append({"id": b.id, "state": state, "tenure": b.tenure, "units": b.units,
                        "adopted_share": adopted_in_b[bi] / b.units,
                        "income_q_mean": sum(qs) / len(qs)})
        front = []
        for q in range(1, 6):
            tot = n_front = 0
            for u in units:
                if u.quintile != q or u.adopted or not OWNERSHIP[buildings[u.bidx].tenure].can_adopt(buildings[u.bidx]):
                    continue
                tot += 1
                quote = mode.quote(QuoteContext(u.area * p.cost_per_m2, u.tax, q, p))
                if not quote.eligible:
                    continue
                if not quote.requires_financing:
                    n_front += 1
                else:
                    lim = credit_limit(p.credit_access, u.income, income_threshold=p.credit_income_threshold,
                                       loan_to_income_cap=p.credit_loan_to_income)
                    n_front += plan_financing(quote.household_upfront, u.savings, lim, p.savings_usable_share).feasible
            front.append(n_front / tot if tot else None)
        series = {
            "adoption_by_quintile": [q_adopt[k] / q_total[k] if q_total[k] else 0.0 for k in range(5)],
            "rebate_per_euro": [q_trans[k] / q_price[k] if q_price[k] else None for k in range(5)],
            "can_front_cost": front,
            "cost_per_retrofit": price_sum / len(events) if events else None,
            "public_cost": public_cost,
            "bills_saved": bills_saved,
            "state_counts": counts,
            "adopted_units": len(events),
        }
        return {"schema": FRAME_SCHEMA_VERSION, "t": t, "year": t / 12.0, "buildings": bfr, "series": series}

    def emit(t: int) -> Frame:
        fr = make_frame(t)
        if p.keep_frames:
            frames.append(fr)
        if on_step is not None:
            on_step(fr)
        return fr

    last = emit(0)
    quota = p.public_capacity * n_units / 12.0
    for t in range(p.horizon_months):
        public_cost += pending.pop(t, 0.0)
        level = (1.0 + g_m) ** t
        # bills saved this month by units retrofitted earlier, while still in dwelling
        for e in events:
            u = units[e.unit]
            if t < u.horizon:
                bills_saved += u.area * p.saving_per_m2_year / 12.0 * level
        snapshot = list(adopted_in_b)
        candidates = []
        for u in units:
            b = buildings[u.bidx]
            own = OWNERSHIP[b.tenure]
            if u.adopted or not own.can_adopt(b) or t >= u.horizon:
                continue
            prob = own.consider_probability(p.consider_prob_base, p.neighbour_boost, snapshot[u.bidx] / b.units)
            if hash_uniform(p.seed, u.uid, t) >= prob:
                continue
            quote = mode.quote(QuoteContext(u.area * p.cost_per_m2, u.tax, u.quintile, p))
            if not quote.eligible:
                continue
            lim = from_sav = loan = 0.0
            if quote.requires_financing:
                lim = credit_limit(p.credit_access, u.income, income_threshold=p.credit_income_threshold,
                                   loan_to_income_cap=p.credit_loan_to_income)
                plan = plan_financing(quote.household_upfront, u.savings, lim, p.savings_usable_share)
                if not plan.feasible:
                    continue
                from_sav, loan = plan.from_savings, plan.loan
            npv = npv_retrofit(
                monthly_saving=u.area * p.saving_per_m2_year / 12.0 * level,
                horizon_months=u.horizon - t, monthly_discount=r_m, monthly_energy_growth=g_m,
                cash_from_savings=from_sav,
                loan_payment=loan_payment(loan, p.loan_rate, p.loan_term_months),
                loan_months=p.loan_term_months, rebate=quote.rebate, rebate_lag_months=quote.rebate_lag_months)
            if npv > 0:
                candidates.append((u, quote, lim, from_sav, loan))
        if mode.name == "public_service":
            slots = int(quota + carry)
            carry = quota + carry - slots
            candidates.sort(key=lambda c: (c[0].queue_draw, c[0].uid))
            candidates = candidates[:slots]
        for u, quote, lim, from_sav, loan in candidates:
            u.adopted = True
            adopted_in_b[u.bidx] += 1
            public_cost += quote.state_pays_now
            if quote.rebate:
                pending[t + quote.rebate_lag_months] = pending.get(t + quote.rebate_lag_months, 0.0) + quote.rebate
            k = u.quintile - 1
            q_adopt[k] += 1
            q_price[k] += quote.price
            q_trans[k] += quote.state_pays_now + quote.rebate
            price_sum += quote.price
            events.append(AdoptionEvent(t, u.uid, buildings[u.bidx].id, u.quintile, mode.name, quote.price,
                                        from_sav, loan, u.savings, lim, quote.state_pays_now, quote.rebate,
                                        quote.rebate_lag_months, u.tax))
            u.savings -= from_sav
        last = emit(t + 1)
    return Result(p, frames, tuple(events), last, n_units, len(buildings))
