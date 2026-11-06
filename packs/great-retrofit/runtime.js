/* The Great Retrofit, model v3: JavaScript port of v3/src/retrofit_v3 (Python is the reference).
 *
 * Same module split as Python, as sections of one file so a pack build can inline it:
 *   npv, financing, rebate, credit, ownership, delivery, sceneEntities, Params, Simulation.
 * ALL randomness goes through v3/js/prng.js (mulberry32 and hashUniform). Never Math.random.
 * Names and the frame schema are the Python ones (snake_case, see v3/docs/frame-schema.md).
 *
 * EVERY default in DEFAULTS is a PLACEHOLDER awaiting the economists (v3/docs/placeholders.md).
 * Nothing computed from them is a finding.
 *
 * Two layers:
 *   core    runSimulation(params, onStep) -> {frames, events, ...}: frames identical to Python's (parity-tested).
 *   adapter PaperDolls.registerRuntime('great-retrofit', ...): wraps the core in the pack runtime interface.
 */
(function (root) {
  'use strict';

  const PRNG = root.RetrofitPRNG || (typeof require === 'function' ? require('../../v3/js/prng.js') : null);
  if (!PRNG) throw new Error('great-retrofit runtime: RetrofitPRNG (v3/js/prng.js) must be loaded first');
  const { Rng, hashUniform } = PRNG;

  const FRAME_SCHEMA_VERSION = 1;
  const BUILDING_STATES = ['not_retrofitted', 'partial', 'retrofitted', 'not_modelled'];
  const TENURES = ['owner_occupied', 'condo', 'rental'];
  const DELIVERY_MODES = ['rebate_market', 'passthrough', 'public_service'];
  const ENERGY_SCENARIOS = ['flat', 'rising', 'shock'];
  const CREDIT_ACCESS = ['income_tested', 'open', 'none'];

  // ---- Python-compatible helpers -------------------------------------------------------------
  // Python's round() is half-to-even; Math.round is half-up.
  function pyRound(x) {
    const f = Math.floor(x), d = x - f;
    if (d < 0.5) return f;
    if (d > 0.5) return f + 1;
    return f % 2 === 0 ? f : f + 1;
  }
  // CPython 3.12 sum() of floats uses Neumaier compensated summation; mirrored so sums agree bit for bit.
  function pySum(xs) {
    let f = 0, c = 0;
    for (const x of xs) {
      const t = f + x;
      if (Math.abs(f) >= Math.abs(x)) c += (f - t) + x; else c += (x - t) + f;
      f = t;
    }
    if (c && isFinite(c)) f += c;
    return f;
  }

  // ---- validation (common/validation.py) -----------------------------------------------------
  const vPositive = (v, n) => { if (!(v > 0)) throw new Error(`${n} must be positive, got ${v}`); };
  const vNonneg = (v, n) => { if (!(v >= 0)) throw new Error(`${n} must be non-negative, got ${v}`); };
  const vProb = (v, n) => { if (!(v >= 0 && v <= 1)) throw new Error(`${n} must be in [0, 1], got ${v}`); };
  const vIntPos = (v, n) => { if (!Number.isInteger(v) || v <= 0) throw new Error(`${n} must be a positive integer, got ${v}`); };

  // ---- npv.py --------------------------------------------------------------------------------
  const npv = {
    monthlyRate(annual) { return Math.pow(1.0 + annual, 1.0 / 12.0) - 1.0; },
    annuityPv(firstPayment, rate, nMonths, growth) {
      growth = growth || 0.0;
      if (nMonths <= 0 || firstPayment === 0.0) return 0.0;
      const q = (1.0 + growth) / (1.0 + rate);
      if (Math.abs(q - 1.0) < 1e-12) return firstPayment / (1.0 + rate) * nMonths;
      return firstPayment / (1.0 + rate) * (1.0 - Math.pow(q, nMonths)) / (1.0 - q);
    },
    npvRetrofit(a) {
      const pvSavings = npv.annuityPv(a.monthly_saving, a.monthly_discount, a.horizon_months, a.monthly_energy_growth);
      const pvRebate = a.rebate ? a.rebate / Math.pow(1.0 + a.monthly_discount, a.rebate_lag_months) : 0.0;
      const pvLoan = npv.annuityPv(a.loan_payment, a.monthly_discount, a.loan_months);
      return pvSavings + pvRebate - a.cash_from_savings - pvLoan;
    },
  };

  // ---- financing.py --------------------------------------------------------------------------
  const financing = {
    planFinancing(upfront, savings, creditLimit, savingsUsableShare) {
      if (savingsUsableShare === undefined) savingsUsableShare = 1.0;
      const usable = Math.max(0.0, savings) * savingsUsableShare;
      const fromSavings = Math.min(usable, upfront);
      const loan = upfront - fromSavings;
      return { from_savings: fromSavings, loan, feasible: loan <= creditLimit + 1e-9 };
    },
    loanPayment(principal, annualRate, months) {
      if (principal <= 0 || months <= 0) return 0.0;
      const r = Math.pow(1.0 + annualRate, 1.0 / 12.0) - 1.0;
      if (r === 0.0) return principal / months;
      return principal * r / (1.0 - Math.pow(1.0 + r, -months));
    },
  };

  // ---- rebate.py -----------------------------------------------------------------------------
  const rebate = {
    rebateAmount(cost, deductionRate, taxPayable, refundable) {
      const gross = Math.max(0.0, deductionRate * cost);
      if (refundable) return Math.min(gross, cost);
      return Math.min(gross, Math.max(0.0, taxPayable), cost);
    },
    rebateArrivalMonth(adoptionMonth, lagMonths) { return adoptionMonth + lagMonths; },
  };

  // ---- credit.py -----------------------------------------------------------------------------
  const credit = {
    CREDIT_ACCESS,
    creditLimit(access, income, incomeThreshold, loanToIncomeCap) {
      if (access === 'none') return 0.0;
      if (access === 'open') return loanToIncomeCap * income;
      if (access === 'income_tested') return income >= incomeThreshold ? loanToIncomeCap * income : 0.0;
      throw new Error(`unknown credit access rule '${access}'; expected one of ${CREDIT_ACCESS.join(', ')}`);
    },
  };

  // ---- ownership.py (strategies) -------------------------------------------------------------
  const ownership = {
    owner_occupied: {
      name: 'owner_occupied',
      canAdopt() { return true; },
      considerProbability(base) { return Math.min(1.0, base); },
    },
    condo: {   // shared-part voting and cost splitting NOT implemented (questions 13-14)
      name: 'condo',
      canAdopt() { return true; },
      considerProbability(base, boost, share) { return Math.min(1.0, base + boost * share); },
    },
    rental: {  // stub: landlord logic arrives in model v2
      name: 'rental',
      canAdopt() { return false; },
      considerProbability() { return 0.0; },
    },
  };

  // ---- delivery.py (strategies) --------------------------------------------------------------
  // ctx: {base_cost, tax_payable, income_quintile, params}
  const quote = (eligible, price, upfront, requires, statePaysNow, reb, lag, capLimited) => ({
    eligible, price, household_upfront: upfront, requires_financing: requires,
    state_pays_now: statePaysNow, rebate: reb, rebate_lag_months: lag, capacity_limited: capLimited,
  });
  const delivery = {
    rebate_market: {
      name: 'rebate_market',
      quote(ctx) {
        const p = ctx.params, price = ctx.base_cost * (1.0 + p.vendor_margin);
        const reb = rebate.rebateAmount(price, p.deduction_rate, ctx.tax_payable, p.refundable);
        return quote(true, price, price, true, 0.0, reb, p.rebate_lag_months, false);
      },
    },
    passthrough: {
      name: 'passthrough',
      quote(ctx) {
        const p = ctx.params, price = ctx.base_cost * (1.0 + p.vendor_margin);
        const eligible = !p.means_test || ctx.income_quintile <= p.means_test_max_quintile;
        return quote(eligible, price, 0.0, false, price, 0.0, 0, false);
      },
    },
    public_service: {
      name: 'public_service',
      quote(ctx) {
        const p = ctx.params, price = ctx.base_cost * (1.0 + p.public_overhead);
        const eligible = !p.means_test || ctx.income_quintile <= p.means_test_max_quintile;
        return quote(eligible, price, 0.0, false, price, 0.0, 0, true);
      },
    },
  };

  // ---- scene_entities.py ---------------------------------------------------------------------
  const SCENE_RULE_DEFAULTS = {          // all PLACEHOLDER
    usable_fraction: 0.8, avg_unit_area: 80.0, rental_share_single: 0.10, rental_share_multi: 0.30, unit_area_spread: 0.2,
  };
  function sceneRules(o) {
    const r = Object.assign({}, SCENE_RULE_DEFAULTS, o || {});
    vProb(r.usable_fraction, 'usable_fraction'); vPositive(r.avg_unit_area, 'avg_unit_area');
    vProb(r.rental_share_single, 'rental_share_single'); vProb(r.rental_share_multi, 'rental_share_multi');
    vProb(r.unit_area_spread, 'unit_area_spread');
    return Object.freeze(r);
  }
  const makeSpec = (id, tenure, unit_areas) => ({ id, tenure, unit_areas: unit_areas.slice(), units: unit_areas.length, floor_area: pySum(unit_areas) });

  // rows: {id, area (footprint m2), storeys, residential}. Returns {buildings, excluded: [[id, reason]], scene_ids}.
  function buildEntities(rows, rules, sceneSeed) {
    rules = rules || sceneRules(); sceneSeed = sceneSeed || 0;
    const buildings = [], excluded = [];
    let k = -1;
    for (const row of rows) {
      k++;
      const sid = String(row.id);
      if (!row.residential) { excluded.push([sid, 'non_residential']); continue; }
      const area = Number(row.area), storeys = Math.trunc(Number(row.storeys) || 1);
      if (!(area > 0) || !(storeys > 0)) { excluded.push([sid, 'invalid_geometry']); continue; }
      const gross = area * storeys * rules.usable_fraction;
      const nUnits = Math.max(1, pyRound(gross / rules.avg_unit_area));
      const rentalShare = nUnits === 1 ? rules.rental_share_single : rules.rental_share_multi;
      let tenure;
      if (hashUniform(sceneSeed, k, 1) < rentalShare) tenure = 'rental';
      else tenure = nUnits === 1 ? 'owner_occupied' : 'condo';
      const rng = new Rng(Math.floor(hashUniform(sceneSeed, k, 2) * 4294967296));
      const raw = [];
      for (let i = 0; i < nUnits; i++) raw.push(1.0 + rules.unit_area_spread * (2.0 * rng.random() - 1.0));
      const s = pySum(raw);
      buildings.push(makeSpec(sid, tenure, raw.map(w => gross * w / s)));
    }
    return { buildings, excluded, scene_ids: buildings.map(b => b.id) };
  }
  function syntheticTable(n, sceneSeed) {
    const rng = new Rng(sceneSeed || 0), rows = [];
    for (let i = 0; i < n; i++) {
      rows.push({ id: 'b' + i, area: rng.lognormal(4.7, 0.4), storeys: rng.choice([1, 2, 2, 3, 3, 4, 5, 6]), residential: true });
    }
    return rows;
  }
  const sceneEntities = { sceneRules, buildEntities, syntheticTable, makeSpec };

  // ---- params.py -----------------------------------------------------------------------------
  const DEFAULTS = {
    // run control
    seed: 0, scene_seed: 0, horizon_months: 180, keep_frames: true, buildings: [], n_buildings: 200,
    // policy levers (sliders)
    deduction_rate: 0.3,            // PLACEHOLDER
    refundable: false,              // PLACEHOLDER
    rebate_lag_months: 12,          // PLACEHOLDER
    credit_access: 'income_tested', // PLACEHOLDER
    loan_rate: 0.04,                // PLACEHOLDER
    delivery_mode: 'rebate_market', // PLACEHOLDER
    vendor_margin: 0.15,            // PLACEHOLDER
    public_overhead: 0.10,          // PLACEHOLDER
    public_capacity: 0.05,          // PLACEHOLDER
    means_test: false,              // PLACEHOLDER
    means_test_max_quintile: 2,     // PLACEHOLDER
    energy_scenario: 'rising',      // PLACEHOLDER
    // energy price paths
    energy_growth_flat: 0.0,        // PLACEHOLDER
    energy_growth_rising: 0.03,     // PLACEHOLDER
    energy_growth_shock: 0.08,      // PLACEHOLDER
    // retrofit physics and cost
    cost_per_m2: 300.0,             // PLACEHOLDER
    saving_per_m2_year: 20.0,       // PLACEHOLDER
    // household decision
    discount_rate: 0.04,            // PLACEHOLDER
    consider_prob_base: 0.05,       // PLACEHOLDER
    neighbour_boost: 0.30,          // PLACEHOLDER
    savings_usable_share: 1.0,      // PLACEHOLDER
    // credit
    credit_income_threshold: 25000.0, // PLACEHOLDER
    credit_loan_to_income: 1.0,       // PLACEHOLDER
    loan_term_months: 120,            // PLACEHOLDER
    // synthetic household population
    income_log_mean: 10.3,          // PLACEHOLDER
    income_log_sd: 0.5,             // PLACEHOLDER
    tax_rate: 0.25,                 // PLACEHOLDER
    tax_free_allowance: 10000.0,    // PLACEHOLDER
    savings_months_of_income: 3.0,  // PLACEHOLDER
    savings_scale: 1.0,             // PLACEHOLDER
    savings_log_sd: 0.8,            // PLACEHOLDER
    years_in_dwelling_min: 5.0,     // PLACEHOLDER
    years_in_dwelling_max: 25.0,    // PLACEHOLDER
  };

  // Accepts a plain object (snake_case, like Python's Params fields); unknown keys are an error. Returns a frozen Params.
  // `buildings` may be specs {id, tenure, unit_areas}; `scene_rules` a partial rules object.
  function Params(over) {
    over = over || {};
    for (const k of Object.keys(over)) if (!(k in DEFAULTS) && k !== 'scene_rules') throw new Error(`unknown parameter '${k}'`);
    const p = Object.assign({}, DEFAULTS, over);
    p.scene_rules = sceneRules(over.scene_rules);
    p.buildings = (over.buildings || []).map(b => makeSpec(b.id, b.tenure, b.unit_areas));
    vIntPos(p.horizon_months, 'horizon_months'); vIntPos(p.n_buildings, 'n_buildings'); vIntPos(p.loan_term_months, 'loan_term_months');
    vNonneg(p.rebate_lag_months, 'rebate_lag_months');
    for (const n of ['deduction_rate', 'vendor_margin', 'public_overhead', 'public_capacity', 'consider_prob_base', 'neighbour_boost', 'savings_usable_share', 'tax_rate']) vProb(p[n], n);
    for (const n of ['cost_per_m2', 'saving_per_m2_year', 'income_log_sd', 'savings_log_sd', 'years_in_dwelling_min', 'years_in_dwelling_max']) vPositive(p[n], n);
    for (const n of ['loan_rate', 'discount_rate', 'credit_income_threshold', 'credit_loan_to_income', 'tax_free_allowance', 'savings_months_of_income', 'savings_scale']) vNonneg(p[n], n);
    if (p.years_in_dwelling_max < p.years_in_dwelling_min) throw new Error('years_in_dwelling_max must be >= years_in_dwelling_min');
    if (!DELIVERY_MODES.includes(p.delivery_mode)) throw new Error(`delivery_mode must be one of ${DELIVERY_MODES.join(', ')}, got '${p.delivery_mode}'`);
    if (!CREDIT_ACCESS.includes(p.credit_access)) throw new Error(`credit_access must be one of ${CREDIT_ACCESS.join(', ')}, got '${p.credit_access}'`);
    if (!ENERGY_SCENARIOS.includes(p.energy_scenario)) throw new Error(`energy_scenario must be one of ${ENERGY_SCENARIOS.join(', ')}, got '${p.energy_scenario}'`);
    if (!(p.means_test_max_quintile >= 1 && p.means_test_max_quintile <= 5)) throw new Error('means_test_max_quintile must be in 1..5');
    p.energy_growth_annual = p['energy_growth_' + p.energy_scenario];
    return Object.freeze(p);
  }

  // ---- model.py ------------------------------------------------------------------------------
  function population(p, buildings) {
    const rng = new Rng(p.seed), units = [], byBuilding = [];
    let uid = 0;
    buildings.forEach((b, bi) => {
      const ids = [];
      for (const area of b.unit_areas) {
        const income = rng.lognormal(p.income_log_mean, p.income_log_sd);
        const sav = rng.lognormal(0.0, p.savings_log_sd) * p.savings_scale * p.savings_months_of_income * income / 12.0;
        const yrs = rng.uniform(p.years_in_dwelling_min, p.years_in_dwelling_max);
        const qd = rng.random();
        const tax = Math.max(0.0, p.tax_rate * (income - p.tax_free_allowance));
        units.push({ uid, bidx: bi, area, income, tax, savings: sav, horizon: pyRound(yrs * 12), queue_draw: qd, quintile: 0, adopted: false });
        ids.push(uid); uid++;
      }
      byBuilding.push(ids);
    });
    const n = units.length;
    const order = units.map((_, i) => i).sort((a, b) => (units[a].income - units[b].income) || (a - b));
    order.forEach((i, rank) => { units[i].quintile = n ? Math.min(5, 1 + Math.floor(rank * 5 / n)) : 1; });
    return { units, byBuilding };
  }

  // Stepwise simulation. new Simulation(params) holds the t = 0 frame; step() advances one month and returns the new frame.
  class Simulation {
    constructor(params) {
      const p = this.p = (params && 'energy_growth_annual' in params) ? params : Params(params);   // already a Params, or a plain object
      this.buildings = p.buildings.length ? p.buildings
        : buildEntities(syntheticTable(p.n_buildings, p.scene_seed), p.scene_rules, p.scene_seed).buildings;
      const pop = population(p, this.buildings);
      this.units = pop.units; this.byB = pop.byBuilding;
      this.mode = delivery[p.delivery_mode];
      this.rM = npv.monthlyRate(p.discount_rate);
      this.gM = npv.monthlyRate(p.energy_growth_annual);
      this.adoptedInB = this.buildings.map(() => 0);
      this.pending = new Map();
      this.events = [];
      this.publicCost = 0.0; this.billsSaved = 0.0; this.priceSum = 0.0;
      this.qTrans = [0, 0, 0, 0, 0]; this.qPrice = [0, 0, 0, 0, 0]; this.qAdopt = [0, 0, 0, 0, 0]; this.qTotal = [0, 0, 0, 0, 0];
      for (const u of this.units) this.qTotal[u.quintile - 1]++;
      this.carry = 0.0;
      this.quota = p.public_capacity * this.units.length / 12.0;
      this.t = 0;
      this.frame = this._makeFrame(0);
    }

    _quote(u) {
      const p = this.p;
      return this.mode.quote({ base_cost: u.area * p.cost_per_m2, tax_payable: u.tax, income_quintile: u.quintile, params: p });
    }
    _limit(u) {
      const p = this.p;
      return credit.creditLimit(p.credit_access, u.income, p.credit_income_threshold, p.credit_loan_to_income);
    }
    _canAdopt(bi) { const b = this.buildings[bi]; return ownership[b.tenure].canAdopt(b); }

    _makeFrame(t) {
      const p = this.p, buildings = this.buildings, units = this.units;
      const bfr = [], counts = { not_retrofitted: 0, partial: 0, retrofitted: 0, not_modelled: 0 };
      buildings.forEach((b, bi) => {
        let state;
        if (!ownership[b.tenure].canAdopt(b)) state = 'not_modelled';
        else if (this.adoptedInB[bi] === 0) state = 'not_retrofitted';
        else if (this.adoptedInB[bi] < b.units) state = 'partial';
        else state = 'retrofitted';
        counts[state]++;
        const ids = this.byB[bi];
        let qsum = 0;
        for (const i of ids) qsum += units[i].quintile;
        bfr.push({ id: b.id, state, tenure: b.tenure, units: b.units, adopted_share: this.adoptedInB[bi] / b.units, income_q_mean: qsum / ids.length });
      });
      const front = [];
      for (let q = 1; q <= 5; q++) {
        let tot = 0, nFront = 0;
        for (const u of units) {
          if (u.quintile !== q || u.adopted || !this._canAdopt(u.bidx)) continue;
          tot++;
          const qt = this._quote(u);
          if (!qt.eligible) continue;
          if (!qt.requires_financing) nFront++;
          else if (financing.planFinancing(qt.household_upfront, u.savings, this._limit(u), p.savings_usable_share).feasible) nFront++;
        }
        front.push(tot ? nFront / tot : null);
      }
      const ne = this.events.length;
      const series = {
        adoption_by_quintile: this.qAdopt.map((a, k) => (this.qTotal[k] ? a / this.qTotal[k] : 0.0)),
        rebate_per_euro: this.qTrans.map((x, k) => (this.qPrice[k] ? x / this.qPrice[k] : null)),
        can_front_cost: front,
        cost_per_retrofit: ne ? this.priceSum / ne : null,
        public_cost: this.publicCost,
        bills_saved: this.billsSaved,
        state_counts: counts,
        adopted_units: ne,
      };
      return { schema: FRAME_SCHEMA_VERSION, t, year: t / 12.0, buildings: bfr, series };
    }

    step() {
      const p = this.p, t = this.t, units = this.units, buildings = this.buildings;
      if (this.pending.has(t)) { this.publicCost += this.pending.get(t); this.pending.delete(t); }
      const level = Math.pow(1.0 + this.gM, t);
      for (const e of this.events) {
        const u = units[e.unit];
        if (t < u.horizon) this.billsSaved += u.area * p.saving_per_m2_year / 12.0 * level;
      }
      const snapshot = this.adoptedInB.slice();
      let candidates = [];
      for (const u of units) {
        const b = buildings[u.bidx], own = ownership[b.tenure];
        if (u.adopted || !own.canAdopt(b) || t >= u.horizon) continue;
        const prob = own.considerProbability(p.consider_prob_base, p.neighbour_boost, snapshot[u.bidx] / b.units);
        if (hashUniform(p.seed, u.uid, t) >= prob) continue;
        const qt = this._quote(u);
        if (!qt.eligible) continue;
        let lim = 0.0, fromSav = 0.0, loan = 0.0;
        if (qt.requires_financing) {
          lim = this._limit(u);
          const plan = financing.planFinancing(qt.household_upfront, u.savings, lim, p.savings_usable_share);
          if (!plan.feasible) continue;
          fromSav = plan.from_savings; loan = plan.loan;
        }
        const v = npv.npvRetrofit({
          monthly_saving: u.area * p.saving_per_m2_year / 12.0 * level,
          horizon_months: u.horizon - t, monthly_discount: this.rM, monthly_energy_growth: this.gM,
          cash_from_savings: fromSav, loan_payment: financing.loanPayment(loan, p.loan_rate, p.loan_term_months),
          loan_months: p.loan_term_months, rebate: qt.rebate, rebate_lag_months: qt.rebate_lag_months,
        });
        if (v > 0) candidates.push({ u, qt, lim, fromSav, loan });
      }
      if (this.mode.name === 'public_service') {
        const slots = Math.floor(this.quota + this.carry);
        this.carry = this.quota + this.carry - slots;
        candidates.sort((a, b) => (a.u.queue_draw - b.u.queue_draw) || (a.u.uid - b.u.uid));
        candidates = candidates.slice(0, slots);
      }
      for (const { u, qt, lim, fromSav, loan } of candidates) {
        u.adopted = true;
        this.adoptedInB[u.bidx]++;
        this.publicCost += qt.state_pays_now;
        if (qt.rebate) {
          const m = t + qt.rebate_lag_months;
          this.pending.set(m, (this.pending.has(m) ? this.pending.get(m) : 0.0) + qt.rebate);
        }
        const k = u.quintile - 1;
        this.qAdopt[k]++; this.qPrice[k] += qt.price; this.qTrans[k] += qt.state_pays_now + qt.rebate;
        this.priceSum += qt.price;
        this.events.push({
          month: t, unit: u.uid, building: buildings[u.bidx].id, quintile: u.quintile, mode: this.mode.name, price: qt.price,
          from_savings: fromSav, loan, savings_at_adoption: u.savings, credit_limit: lim, state_pays_now: qt.state_pays_now,
          rebate: qt.rebate, rebate_lag_months: qt.rebate_lag_months, tax_payable: u.tax,
        });
        u.savings -= fromSav;
      }
      this.t = t + 1;
      this.frame = this._makeFrame(this.t);
      return this.frame;
    }
  }

  // Same contract as Python's run_simulation(params, on_step): on_step(frame) at t = 0 and after each month.
  function runSimulation(params, onStep) {
    const sim = new Simulation(params), p = sim.p, frames = [];
    const emit = fr => { if (p.keep_frames) frames.push(fr); if (onStep) onStep(fr); };
    emit(sim.frame);
    for (let i = 0; i < p.horizon_months; i++) emit(sim.step());
    return { params: p, frames, events: sim.events, final_frame: sim.frame, n_units: sim.units.length, n_buildings: sim.buildings.length };
  }

  // ---- pack adapter (paperdolls runtime interface) -------------------------------------------
  const STATE_INDEX = Object.fromEntries(BUILDING_STATES.map((s, i) => [s, i]));
  const TENURE_INDEX = Object.fromEntries(TENURES.map((s, i) => [s, i]));
  const nz = x => (x === null ? NaN : x);

  // v3 frame -> pack frame: category = index into the manifest's values, NaN for null, series as arrays aligned with `y`.
  function toPackFrame(fr) {
    const n = fr.buildings.length;
    const state = new Int8Array(n), tenure = new Int8Array(n), units = new Int16Array(n);
    const share = new Float64Array(n), incomeQ = new Float64Array(n);
    fr.buildings.forEach((b, i) => {
      state[i] = STATE_INDEX[b.state]; tenure[i] = TENURE_INDEX[b.tenure]; units[i] = b.units;
      share[i] = b.adopted_share; incomeQ[i] = b.income_q_mean;
    });
    const s = fr.series;
    return {
      t: fr.t,
      entities: { building: { state, tenure, adopted_share: share, units, income_q_mean: incomeQ } },
      series: {
        adoption_by_quintile: s.adoption_by_quintile.slice(),
        rebate_per_euro: s.rebate_per_euro.map(nz),
        can_front_cost: s.can_front_cost.map(nz),
        cost_per_retrofit: [nz(s.cost_per_retrofit)],
        public_cost: [s.public_cost],
        bills_saved: [s.bills_saved],
        buildings_by_state: BUILDING_STATES.map(k => s.state_counts[k]),
      },
    };
  }

  // Manifest params -> core Params. `ents.building.specs` (from bind.js, once the shell passes it) beats the synthetic scene.
  // The run length is not a parameter here: the shell asks for steps up to the manifest's time.steps.
  function paramsFromPack(p, ents, seed) {
    const o = Object.assign({}, p, { seed: seed | 0 });
    const b = ents && ents.building;
    if (b && b.specs && b.specs.length) o.buildings = b.specs;
    else if (b && b.count) o.n_buildings = b.count;
    return Params(o);
  }

  if (root.PaperDolls && typeof root.PaperDolls.registerRuntime === 'function') {
    root.PaperDolls.registerRuntime('great-retrofit', {
      init(p, ents, seed) { return { sim: new Simulation(paramsFromPack(p, ents, seed)) }; },
      step(h, n) {
        if (n === 0) return [toPackFrame(h.sim.frame)];
        const out = [];
        for (let i = 0; i < n; i++) out.push(toPackFrame(h.sim.step()));
        return out;
      },
      run(h, toT) {
        const out = [];
        while (h.sim.t < toT) out.push(toPackFrame(h.sim.step()));
        return out;
      },
    });
  }

  const api = {
    FRAME_SCHEMA_VERSION, BUILDING_STATES, TENURES, DELIVERY_MODES, ENERGY_SCENARIOS, CREDIT_ACCESS, DEFAULTS,
    npv, financing, rebate, credit, ownership, delivery, sceneEntities,
    Params, Simulation, runSimulation, toPackFrame, pyRound, pySum,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.GreatRetrofit = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
