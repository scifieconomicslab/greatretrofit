/* The Great Retrofit, model v3: JavaScript port of v3/src/retrofit_v3 (Python is the reference).
 *
 * Same module split as Python, as sections of one file so a pack build can inline it:
 *   npv, financing, rebate, credit, ownership, delivery, sceneEntities, Params, Simulation.
 * ALL randomness goes through prng.js (a copy of v3/js/prng.js, kept identical by a test) (mulberry32 and hashUniform). Never Math.random.
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

  const PRNG = root.RetrofitPRNG || (typeof require === 'function' ? require('./prng.js') : null);
  if (!PRNG) throw new Error('great-retrofit runtime: RetrofitPRNG (prng.js) must be loaded first');
  const { Rng, hashUniform } = PRNG;

  const FRAME_SCHEMA_VERSION = 1;
  const BUILDING_STATES = ['not_retrofitted', 'partial', 'retrofitted', 'not_modelled'];
  const SHARED_STATES = ['none', 'pending', 'approved'];
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
      hasSharedParts() { return false; },
    },
    condo: {   // shared parts are decided by a vote in the Simulation loop; this says which buildings have them
      name: 'condo',
      canAdopt() { return true; },
      considerProbability(base, boost, share, canvassBoost, canvassPressure) {
        return Math.min(1.0, base + boost * share + (canvassBoost || 0.0) * (canvassPressure || 0.0));
      },
      hasSharedParts(b) { return b.units >= 2; },
    },
    rental: {  // stub: landlord logic arrives in model v2
      name: 'rental',
      canAdopt() { return false; },
      considerProbability() { return 0.0; },
      hasSharedParts() { return false; },
    },
  };

  // ---- delivery.py (strategies) --------------------------------------------------------------
  // ctx: {base_cost, tax_payable, income_quintile, params}
  const quote = (eligible, price, upfront, requires, statePaysNow, reb, lag, capLimited) => ({
    eligible, price, household_upfront: upfront, requires_financing: requires,
    state_pays_now: statePaysNow, rebate: reb, rebate_lag_months: lag, capacity_limited: capLimited,
  });
  const inScheme = ctx => !ctx.params.means_test || ctx.income_quintile <= ctx.params.means_test_max_quintile;
  // a household the scheme does not cover buys on the market: full price with margin, own financing, no subsidy
  const marketQuote = ctx => {
    const price = ctx.base_cost * (1.0 + ctx.params.vendor_margin);
    return quote(false, price, price, true, 0.0, 0.0, 0, false);
  };
  const delivery = {
    rebate_market: {
      name: 'rebate_market',
      quote(ctx) {
        const p = ctx.params;
        if (!inScheme(ctx)) return marketQuote(ctx);
        const price = ctx.base_cost * (1.0 + p.vendor_margin);
        const reb = rebate.rebateAmount(price, p.deduction_rate, ctx.tax_payable, p.refundable);
        return quote(true, price, price, true, 0.0, reb, p.rebate_lag_months, false);
      },
    },
    passthrough: {
      name: 'passthrough',
      quote(ctx) {
        const p = ctx.params;
        if (!inScheme(ctx)) return marketQuote(ctx);
        const price = ctx.base_cost * (1.0 + p.vendor_margin);
        return quote(true, price, 0.0, false, price, 0.0, 0, false);
      },
    },
    public_service: {
      name: 'public_service',
      quote(ctx) {
        const p = ctx.params;
        if (!inScheme(ctx)) return marketQuote(ctx);
        const price = ctx.base_cost * (1.0 + p.public_overhead);
        return quote(true, price, 0.0, false, price, 0.0, 0, true);
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
  const makeSpec = (id, tenure, unit_areas, rental_draw) => ({ id, tenure, unit_areas: unit_areas.slice(), units: unit_areas.length, floor_area: pySum(unit_areas), rental_draw: rental_draw === undefined ? null : rental_draw });

  // Largest number of dwellings of one scene building. A building above it (huge footprint times many levels: bad geometry) keeps its floor area
  // but is split into this many units and is listed in `capped` (SM-9). Same constant and rule as scene_entities.py.
  const MAX_UNITS_PER_BUILDING = 1000;
  // The id of a scene row: a row without an id is "#<index>" (index in the scene's building list), the paperdolls convention (sceneKey in viz/packruntime.js). Same as scene_key() in Python.
  const sceneKey = (id, index) => (id === undefined || id === null ? '#' + index : String(id));

  // rows: {id, area (footprint m2), storeys, residential}. Returns {buildings, excluded: [[id, reason]], scene_ids, capped: [[id, dwellings before the cap]]}.
  function buildEntities(rows, rules, sceneSeed) {
    rules = rules || sceneRules(); sceneSeed = sceneSeed || 0;
    const buildings = [], excluded = [], capped = [];
    let k = -1;
    for (const row of rows) {
      k++;
      const sid = sceneKey(row.id, k);
      if (!row.residential) { excluded.push([sid, 'non_residential']); continue; }
      const area = Number(row.area), storeys = Math.trunc(Number(row.storeys) || 1);
      const gross = area * storeys * rules.usable_fraction;
      if (!(area > 0 && storeys > 0 && Number.isFinite(gross))) { excluded.push([sid, 'invalid_geometry']); continue; }
      let nUnits = Math.max(1, pyRound(gross / rules.avg_unit_area));
      if (nUnits > MAX_UNITS_PER_BUILDING) { capped.push([sid, nUnits]); nUnits = MAX_UNITS_PER_BUILDING; }
      const rentalShare = nUnits === 1 ? rules.rental_share_single : rules.rental_share_multi;
      let tenure;
      const draw = hashUniform(sceneSeed, k, 1);
      if (draw < rentalShare) tenure = 'rental';
      else tenure = nUnits === 1 ? 'owner_occupied' : 'condo';
      const rng = new Rng(Math.floor(hashUniform(sceneSeed, k, 2) * 4294967296));
      const raw = [];
      for (let i = 0; i < nUnits; i++) raw.push(1.0 + rules.unit_area_spread * (2.0 * rng.random() - 1.0));
      const s = pySum(raw);
      buildings.push(makeSpec(sid, tenure, raw.map(w => gross * w / s), draw));
    }
    return { buildings, excluded, scene_ids: buildings.map(b => b.id), capped };
  }
  function syntheticTable(n, sceneSeed) {
    const rng = new Rng(sceneSeed || 0), rows = [];
    for (let i = 0; i < n; i++) {
      rows.push({ id: 'b' + i, area: rng.lognormal(4.7, 0.4), storeys: rng.choice([1, 2, 2, 3, 3, 4, 5, 6]), residential: true });
    }
    return rows;
  }
  const sceneEntities = { sceneRules, buildEntities, syntheticTable, makeSpec, sceneKey, MAX_UNITS_PER_BUILDING };

  // ---- params.py -----------------------------------------------------------------------------
  const DEFAULTS = {
    // run control
    seed: 0, scene_seed: 0, horizon_months: 180, keep_frames: true, buildings: [], n_buildings: 200,
    // policy levers (sliders)
    deduction_rate: 0.3,            // PLACEHOLDER
    refundable: false,              // PLACEHOLDER
    rebate_lag_months: 12,          // PLACEHOLDER months until the rebate arrives; 0 = paid in the month of the retrofit; fractions round half-to-even
    credit_access: 'income_tested', // PLACEHOLDER
    loan_rate: 0.04,                // PLACEHOLDER
    delivery_mode: 'rebate_market', // PLACEHOLDER
    vendor_margin: 0.15,            // PLACEHOLDER
    public_overhead: 0.10,          // PLACEHOLDER
    public_capacity: 0.05,          // PLACEHOLDER
    means_test: false,              // PLACEHOLDER
    means_test_max_quintile: 2,     // PLACEHOLDER
    energy_scenario: 'rising',      // PLACEHOLDER
    peer_effect: true,              // PLACEHOLDER
    loan_rate_risk_premium: 0.02,   // PLACEHOLDER
    // condo shared parts (vote)
    rental_share_single: 0.10,      // PLACEHOLDER share of single-unit buildings treated as rental; null keeps the tenure the scene rules gave
    rental_share_multi: 0.30,       // PLACEHOLDER share of multi-unit buildings treated as rental
    shared_measure: true,           // PLACEHOLDER
    shared_share: 0.4,              // PLACEHOLDER
    vote_threshold: 2.0 / 3.0,      // PLACEHOLDER
    // canvassing and the weekly time budget
    canvass_target_hours: 2.0,      // PLACEHOLDER
    canvass_boost: 0.2,             // PLACEHOLDER
    canvass_saturation_hours: 6.0,  // PLACEHOLDER
    waking_hours_per_week: 112.0,   // PLACEHOLDER
    committed_hours_per_week: 50.0, // PLACEHOLDER
    work_hours_by_quintile: [42.0, 38.0, 36.0, 40.0, 48.0], // PLACEHOLDER
    free_time_spread: 0.3,          // PLACEHOLDER
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
    p.buildings = (over.buildings || []).map(b => makeSpec(b.id, b.tenure, b.unit_areas, b.rental_draw));
    for (const n of ['rental_share_single', 'rental_share_multi']) if (p[n] !== null) vProb(p[n], n);
    vIntPos(p.horizon_months, 'horizon_months'); vIntPos(p.n_buildings, 'n_buildings'); vIntPos(p.loan_term_months, 'loan_term_months');
    vNonneg(p.rebate_lag_months, 'rebate_lag_months');
    if (!Number.isFinite(p.rebate_lag_months)) throw new Error(`rebate_lag_months must be finite, got ${p.rebate_lag_months}`);
    p.rebate_lag_months = pyRound(p.rebate_lag_months);      // whole months, half-to-even (as Python round)
    for (const n of ['deduction_rate', 'vendor_margin', 'public_overhead', 'public_capacity', 'consider_prob_base', 'neighbour_boost', 'savings_usable_share', 'tax_rate', 'shared_share', 'canvass_boost', 'free_time_spread']) vProb(p[n], n);
    for (const n of ['cost_per_m2', 'saving_per_m2_year', 'income_log_sd', 'savings_log_sd', 'years_in_dwelling_min', 'years_in_dwelling_max', 'canvass_saturation_hours', 'waking_hours_per_week']) vPositive(p[n], n);
    for (const n of ['loan_rate', 'loan_rate_risk_premium', 'canvass_target_hours', 'committed_hours_per_week', 'discount_rate', 'credit_income_threshold', 'credit_loan_to_income', 'tax_free_allowance', 'savings_months_of_income', 'savings_scale']) vNonneg(p[n], n);
    if (!(p.vote_threshold > 0 && p.vote_threshold <= 1)) throw new Error('vote_threshold must be in (0, 1]');
    p.work_hours_by_quintile = Array.from(p.work_hours_by_quintile, Number);
    if (p.work_hours_by_quintile.length !== 5 || p.work_hours_by_quintile.some(x => !(x >= 0))) throw new Error('work_hours_by_quintile must be 5 non-negative numbers');
    if (p.years_in_dwelling_max < p.years_in_dwelling_min) throw new Error('years_in_dwelling_max must be >= years_in_dwelling_min');
    if (!DELIVERY_MODES.includes(p.delivery_mode)) throw new Error(`delivery_mode must be one of ${DELIVERY_MODES.join(', ')}, got '${p.delivery_mode}'`);
    if (!CREDIT_ACCESS.includes(p.credit_access)) throw new Error(`credit_access must be one of ${CREDIT_ACCESS.join(', ')}, got '${p.credit_access}'`);
    if (!ENERGY_SCENARIOS.includes(p.energy_scenario)) throw new Error(`energy_scenario must be one of ${ENERGY_SCENARIOS.join(', ')}, got '${p.energy_scenario}'`);
    if (!(p.means_test_max_quintile >= 1 && p.means_test_max_quintile <= 5)) throw new Error('means_test_max_quintile must be in 1..5');
    p.energy_growth_annual = p['energy_growth_' + p.energy_scenario];
    return Object.freeze(p);
  }

  // ---- model.py ------------------------------------------------------------------------------
  // Timing within a month: see the header of v3/src/retrofit_v3/model.py. All float sums are plain loops in unit-id order.
  const FREE_TIME_KEY = 1073741825;     // hashUniform stream for the free-time spread (consideration uses j = month)

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
        units.push({
          uid, bidx: bi, area, income, tax, savings: sav, horizon: pyRound(yrs * 12), queue_draw: qd, quintile: 0,
          free_hours: 0.0, tax_left: tax, unit_base: 0.0, shared_base: 0.0, needs_shared: false,
          unit_done: false, shared_paid: false, supporter: false, complete: false, paid_any: false,
          saving_frac: 0.0, paid_price: 0.0, paid_base: 0.0, cash_net: 0.0, loans: [],
        });
        ids.push(uid); uid++;
      }
      byBuilding.push(ids);
    });
    const n = units.length;
    const order = units.map((_, i) => i).sort((a, b) => (units[a].income - units[b].income) || (a - b));
    order.forEach((i, rank) => { units[i].quintile = n ? Math.min(5, 1 + Math.floor(rank * 5 / n)) : 1; });
    for (const u of units) {
      const base = Math.max(0.0, p.waking_hours_per_week - p.committed_hours_per_week - p.work_hours_by_quintile[u.quintile - 1]);
      const spread = 1.0 + p.free_time_spread * (2.0 * hashUniform(p.seed, u.uid, FREE_TIME_KEY) - 1.0);
      u.free_hours = Math.max(0.0, base * spread);
    }
    return { units, byBuilding };
  }

  // Apply rental_share_* (PLACEHOLDER tenure rule) to buildings that carry their scene draw; others keep their tenure.
  function retenure(p, buildings) {
    if (p.rental_share_single === null && p.rental_share_multi === null) return buildings;
    return buildings.map(b => {
      const share = b.units === 1 ? p.rental_share_single : p.rental_share_multi;
      if (b.rental_draw === null || b.rental_draw === undefined || share === null) return b;
      const tenure = b.rental_draw < share ? 'rental' : (b.units === 1 ? 'owner_occupied' : 'condo');
      return Object.assign({}, b, { tenure });
    });
  }

  // Stepwise simulation. new Simulation(params) holds the t = 0 frame; step() advances one month and returns the new frame.
  class Simulation {
    constructor(params) {
      const p = this.p = (params && 'energy_growth_annual' in params) ? params : Params(params);   // already a Params, or a plain object
      this.buildings = retenure(p, p.buildings.length ? p.buildings
        : buildEntities(syntheticTable(p.n_buildings, p.scene_seed), p.scene_rules, p.scene_seed).buildings);
      const pop = population(p, this.buildings);
      this.units = pop.units; this.byB = pop.byBuilding;
      this.mode = delivery[p.delivery_mode];
      this.rM = npv.monthlyRate(p.discount_rate);
      this.gM = npv.monthlyRate(p.energy_growth_annual);
      this.adoptedInB = this.buildings.map(() => 0);
      this.needsShared = this.buildings.map(b => p.shared_measure && ownership[b.tenure].hasSharedParts(b));
      this.approved = this.buildings.map(() => false);
      this.pending = new Map();           // month -> [[unit id, rebate cash]]
      this.events = []; this.votes = [];
      this.publicCost = 0.0; this.billsSaved = 0.0; this.priceSum = 0.0; this.baseSum = 0.0; this.nComplete = 0;
      this.qTrans = [0, 0, 0, 0, 0]; this.qPrice = [0, 0, 0, 0, 0]; this.qAdopt = [0, 0, 0, 0, 0]; this.qTotal = [0, 0, 0, 0, 0];
      for (const u of this.units) this.qTotal[u.quintile - 1]++;
      this.carry = 0.0;
      this.quota = p.public_capacity * this.units.length / 12.0;
      this.t = 0;
      this._prepareCosts();
      this.frame = this._makeFrame(0);
    }

    _prepareCosts() {
      const p = this.p;
      this.buildings.forEach((b, bi) => {
        const ids = this.byB[bi];
        let floor = 0.0;
        for (const i of ids) floor += this.units[i].area;
        const sharedTotal = p.shared_share * p.cost_per_m2 * floor;
        for (const i of ids) {
          const u = this.units[i];
          u.needs_shared = this.needsShared[bi];
          if (u.needs_shared) {
            u.unit_base = u.area * p.cost_per_m2 * (1.0 - p.shared_share);
            u.shared_base = sharedTotal * u.area / floor;       // cost split by floor area
          } else {
            u.unit_base = u.area * p.cost_per_m2;
          }
        }
      });
    }

    _canAdopt(bi) { const b = this.buildings[bi]; return ownership[b.tenure].canAdopt(b); }
    _unitFrac(u) { return u.needs_shared ? 1.0 - this.p.shared_share : 1.0; }
    _limit(u) {
      const p = this.p;
      return credit.creditLimit(p.credit_access, u.income, p.credit_income_threshold, p.credit_loan_to_income);
    }
    _loanRate(u) { const p = this.p; return p.loan_rate + (u.income < p.credit_income_threshold ? p.loan_rate_risk_premium : 0.0); }
    _quote(u, base) {
      return this.mode.quote({ base_cost: base, tax_payable: u.tax_left, income_quintile: u.quintile, params: this.p });
    }
    _spend(u) {   // weekly canvassing hours: advocates in co-owned buildings, within their free time
      const b = this.buildings[u.bidx];
      if (!(u.supporter || u.paid_any) || !ownership[b.tenure].hasSharedParts(b)) return 0.0;
      return Math.min(u.free_hours, this.p.canvass_target_hours);
    }

    // Quote, financing and NPV of paying `base` (a part of the retrofit) now; null if it cannot be financed.
    _evaluate(u, base, frac, t, level) {
      const p = this.p, qt = this._quote(u, base);
      let lim = 0.0, fromSav = 0.0, loan = 0.0;
      const rate = this._loanRate(u);
      if (qt.requires_financing) {
        lim = this._limit(u);
        const plan = financing.planFinancing(qt.household_upfront, u.savings, lim, p.savings_usable_share);
        if (!plan.feasible) return null;
        fromSav = plan.from_savings; loan = plan.loan;
      }
      const v = npv.npvRetrofit({
        monthly_saving: u.area * p.saving_per_m2_year / 12.0 * frac * level,
        horizon_months: u.horizon - t, monthly_discount: this.rM, monthly_energy_growth: this.gM,
        cash_from_savings: fromSav, loan_payment: financing.loanPayment(loan, rate, p.loan_term_months),
        loan_months: p.loan_term_months, rebate: qt.rebate, rebate_lag_months: qt.rebate_lag_months,
      });
      return { quote: qt, limit: lim, from_savings: fromSav, loan, loan_rate: rate, npv: v };
    }

    // The household pays for a part: books the event, the state's outlay, the rebate and the loan.
    _pay(u, ev, kind, base, frac, t) {
      const p = this.p, q = ev.quote;
      this.publicCost += q.state_pays_now;
      if (q.rebate) {
        if (q.rebate_lag_months === 0) {        // lag 0 = paid in the month of the retrofit (phase 1 of this month has already run)
          this.publicCost += q.rebate;
          u.cash_net += q.rebate;
        } else {                                // lag is a whole number >= 1 (Params rounds it): delivered in phase 1 of month t + lag
          const m = t + q.rebate_lag_months;
          if (!this.pending.has(m)) this.pending.set(m, []);
          this.pending.get(m).push([u.uid, q.rebate]);
        }
      }
      const k = u.quintile - 1;
      this.qPrice[k] += q.price;
      this.qTrans[k] += q.state_pays_now + q.rebate;
      this.events.push({
        month: t, unit: u.uid, building: this.buildings[u.bidx].id, quintile: u.quintile, mode: this.mode.name, price: q.price,
        from_savings: ev.from_savings, loan: ev.loan, savings_at_adoption: u.savings, credit_limit: ev.limit,
        state_pays_now: q.state_pays_now, rebate: q.rebate, rebate_lag_months: q.rebate_lag_months, tax_payable: u.tax_left,
        kind, base_cost: base, subsidised: q.eligible,
      });
      u.savings -= ev.from_savings;
      u.cash_net -= ev.from_savings;
      u.tax_left = Math.max(0.0, u.tax_left - q.rebate);
      if (ev.loan > 0) u.loans.push([financing.loanPayment(ev.loan, ev.loan_rate, p.loan_term_months), t + p.loan_term_months]);
      u.paid_any = true;
      u.paid_price += q.price;
      u.paid_base += base;
      u.saving_frac += frac;
      if (kind === 'shared') u.shared_paid = true; else u.unit_done = true;
      if (u.unit_done && (u.shared_paid || !u.needs_shared) && !u.complete) {
        u.complete = true;
        this.adoptedInB[u.bidx]++;
        this.qAdopt[k]++;
        this.priceSum += u.paid_price;
        this.baseSum += u.paid_base;
        this.nComplete++;
      }
    }

    _yesShare(bi) {
      let yes = 0.0, tot = 0.0;
      for (const i of this.byB[bi]) {
        const u = this.units[i];
        tot += u.area;
        if (u.supporter) yes += u.area;
      }
      return tot ? yes / tot : 0.0;
    }

    _makeFrame(t) {
      const p = this.p, buildings = this.buildings, units = this.units;
      const bfr = [], counts = { not_retrofitted: 0, partial: 0, retrofitted: 0, not_modelled: 0 };
      const sharedCounts = { pending: 0, approved: 0 };
      const tenureCounts = { owner_occupied: 0, condo: 0, rental: 0 };
      // can each not-yet-retrofitted unit finance what it still has to pay now? (per quintile, and per building)
      const frontTot = [0, 0, 0, 0, 0], frontOk = [0, 0, 0, 0, 0], cannotInB = new Array(buildings.length).fill(0);
      for (const u of units) {
        if (u.complete || !this._canAdopt(u.bidx)) continue;
        const base = (u.unit_done ? 0.0 : u.unit_base) + ((u.needs_shared && !u.shared_paid) ? u.shared_base : 0.0);
        const qt = this._quote(u, base);
        const ok = !qt.requires_financing || financing.planFinancing(qt.household_upfront, u.savings, this._limit(u), p.savings_usable_share).feasible;
        frontTot[u.quintile - 1]++;
        if (ok) frontOk[u.quintile - 1]++; else cannotInB[u.bidx]++;
      }
      buildings.forEach((b, bi) => {
        let state;
        if (!this._canAdopt(bi)) state = 'not_modelled';
        else if (this.adoptedInB[bi] === 0) state = 'not_retrofitted';
        else if (this.adoptedInB[bi] < b.units) state = 'partial';
        else state = 'retrofitted';
        counts[state]++;
        tenureCounts[b.tenure]++;
        let sstate, yes;
        if (!this.needsShared[bi]) { sstate = 'none'; yes = 0.0; }
        else if (this.approved[bi]) { sstate = 'approved'; yes = this._yesShare(bi); sharedCounts.approved++; }
        else { sstate = 'pending'; yes = this._yesShare(bi); sharedCounts.pending++; }
        const ids = this.byB[bi];
        let qsum = 0;
        for (const i of ids) qsum += units[i].quintile;
        bfr.push({
          id: b.id, state, tenure: b.tenure, units: b.units, adopted_share: this.adoptedInB[bi] / b.units,
          income_q_mean: qsum / ids.length, shared_state: sstate, vote_yes_share: yes, units_cannot_front: cannotInB[bi],
        });
      });
      const front = frontOk.map((x, k) => (frontTot[k] ? x / frontTot[k] : null));
      const canv = [0, 0, 0, 0, 0], leis = [0, 0, 0, 0, 0], cashSum = [0, 0, 0, 0, 0], cashN = [0, 0, 0, 0, 0];
      for (const u of units) {
        const k = u.quintile - 1, s = this._spend(u);
        canv[k] += s;
        leis[k] += u.free_hours - s;
        if (u.paid_any) { cashSum[k] += u.cash_net; cashN[k]++; }
      }
      const n = this.nComplete;
      const series = {
        adoption_by_quintile: this.qAdopt.map((a, k) => (this.qTotal[k] ? a / this.qTotal[k] : 0.0)),
        rebate_per_euro: this.qTrans.map((x, k) => (this.qPrice[k] ? x / this.qPrice[k] : null)),
        can_front_cost: front,
        cost_per_retrofit: n ? this.priceSum / n : null,
        public_cost: this.publicCost,
        bills_saved: this.billsSaved,
        state_counts: counts,
        adopted_units: n,
        cost_per_retrofit_parts: n ? { base: this.baseSum / n, markup: (this.priceSum - this.baseSum) / n } : null,
        canvass_hours_by_quintile: canv.map((x, k) => (this.qTotal[k] ? x / this.qTotal[k] : 0.0)),
        leisure_hours_by_quintile: leis.map((x, k) => (this.qTotal[k] ? x / this.qTotal[k] : 0.0)),
        net_cash_by_quintile: cashSum.map((x, k) => (cashN[k] ? x / cashN[k] : null)),
        shared_counts: sharedCounts,
        tenure_counts: tenureCounts,
      };
      return { schema: FRAME_SCHEMA_VERSION, t, year: t / 12.0, buildings: bfr, series };
    }

    step() {
      const p = this.p, t = this.t, units = this.units, buildings = this.buildings;
      // 1. cash arriving and leaving
      if (this.pending.has(t)) {
        for (const [uid, amount] of this.pending.get(t)) { this.publicCost += amount; units[uid].cash_net += amount; }
        this.pending.delete(t);
      }
      const level = Math.pow(1.0 + this.gM, t);
      for (const u of units) {
        for (const [pay, last] of u.loans) if (t <= last) u.cash_net -= pay;
        if (u.saving_frac > 0 && t < u.horizon) {
          const bill = u.area * p.saving_per_m2_year / 12.0 * u.saving_frac * level;
          this.billsSaved += bill;
          u.cash_net += bill;
        }
      }
      // 2. snapshot
      const snapshot = this.adoptedInB.slice();
      const spend = units.map(u => this._spend(u));
      const canvTotal = buildings.map(() => 0.0);
      for (const u of units) canvTotal[u.bidx] += spend[u.uid];
      const nb = p.peer_effect ? p.neighbour_boost : 0.0;
      // 3. considerations
      let candidates = [];
      for (const u of units) {
        const b = buildings[u.bidx], own = ownership[b.tenure];
        if (u.complete || !own.canAdopt(b) || t >= u.horizon) continue;
        const pressure = Math.min(1.0, Math.max(0.0, canvTotal[u.bidx] - spend[u.uid]) / p.canvass_saturation_hours);
        const prob = own.considerProbability(p.consider_prob_base, nb, snapshot[u.bidx] / b.units, p.canvass_boost, pressure);
        if (hashUniform(p.seed, u.uid, t) >= prob) continue;
        if (!u.unit_done) {
          const ev = this._evaluate(u, u.unit_base, this._unitFrac(u), t, level);
          if (ev !== null && ev.npv > 0) candidates.push({ u, ev });
        }
        if (u.needs_shared && !this.approved[u.bidx] && !u.supporter) {
          const ev = this._evaluate(u, u.shared_base, p.shared_share, t, level);
          if (ev !== null && ev.npv > 0) u.supporter = true;
        }
      }
      // 4. capacity, then payment
      let slotsLeft = null;
      if (this.mode.name === 'public_service') {
        const slots = Math.floor(this.quota + this.carry);
        this.carry = this.quota + this.carry - slots;
        const limited = candidates.filter(c => c.ev.quote.capacity_limited)
          .sort((a, b) => (a.u.queue_draw - b.u.queue_draw) || (a.u.uid - b.u.uid));
        const allowed = new Set(limited.slice(0, slots).map(c => c.u.uid));
        candidates = candidates.filter(c => !c.ev.quote.capacity_limited || allowed.has(c.u.uid));
        slotsLeft = slots - allowed.size;
      }
      for (const { u, ev } of candidates) this._pay(u, ev, u.needs_shared ? 'unit' : 'whole', u.unit_base, this._unitFrac(u), t);
      // 5. shared-measure votes
      buildings.forEach((b, bi) => {
        if (!this.needsShared[bi] || this.approved[bi]) return;
        const yes = this._yesShare(bi);
        if (yes + 1e-9 < p.vote_threshold) return;
        let need = 0;
        if (slotsLeft !== null) {         // the public service does the shared work too: it needs capacity
          need = Math.ceil(b.units * p.shared_share - 1e-9);
          if (need > slotsLeft) return;
        }
        const evs = [];
        for (const i of this.byB[bi]) {
          const u = units[i], e = this._evaluate(u, u.shared_base, p.shared_share, t, level);
          if (e === null) return;         // some owner cannot pay their share: the measure is blocked
          evs.push([u, e]);
        }
        this.approved[bi] = true;
        if (slotsLeft !== null) slotsLeft -= need;
        this.votes.push({ month: t, building: b.id, yes_share: yes, threshold: p.vote_threshold, slots_used: need });
        for (const [u, e] of evs) this._pay(u, e, 'shared', u.shared_base, p.shared_share, t);
      });
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
    return { params: p, frames, events: sim.events, votes: sim.votes, final_frame: sim.frame, n_units: sim.units.length, n_buildings: sim.buildings.length };
  }

  // ---- pack adapter (paperdolls runtime interface) -------------------------------------------
  const STATE_INDEX = Object.fromEntries(BUILDING_STATES.map((s, i) => [s, i]));
  const TENURE_INDEX = Object.fromEntries(TENURES.map((s, i) => [s, i]));
  const SHARED_INDEX = Object.fromEntries(SHARED_STATES.map((s, i) => [s, i]));
  // No-data representation (pack-spec, "entities"): NaN in a number field or series point, -1 in a category. The v3 frame says null (frame-schema.md); only the
  // series the frame schema marks nullable are converted, and nothing else is ever NaN. Charts and tiles draw NaN as "no data", never as zero.
  const nz = x => (x === null ? NaN : x);

  // v3 frame -> pack frame: category = index into the manifest's values, NaN for null, series as arrays aligned with `y`.
  function toPackFrame(fr) {
    const n = fr.buildings.length;
    // units and units_done are Int32Array: Int16Array wrapped above 32767 dwellings (SM-9; bind also caps a building at MAX_UNITS_PER_BUILDING)
    const state = new Int8Array(n), tenure = new Int8Array(n), shared = new Int8Array(n), units = new Int32Array(n);
    const share = new Float64Array(n), incomeQ = new Float64Array(n), done = new Int32Array(n), cannot = new Int8Array(n);
    fr.buildings.forEach((b, i) => {
      done[i] = pyRound(b.adopted_share * b.units);
      cannot[i] = (b.units_cannot_front > 0 && b.units_cannot_front === b.units - done[i]) ? 1 : 0;   // every unit still to do cannot pay now
      state[i] = STATE_INDEX[b.state]; tenure[i] = TENURE_INDEX[b.tenure]; shared[i] = SHARED_INDEX[b.shared_state]; units[i] = b.units;
      share[i] = b.adopted_share; incomeQ[i] = b.income_q_mean;
    });
    const s = fr.series;
    return {
      t: fr.t,
      entities: { building: { state, tenure, adopted_share: share, units, units_done: done, cannot_front: cannot, income_q_mean: incomeQ, shared_state: shared } },
      series: {
        adoption_by_quintile: s.adoption_by_quintile.slice(),
        rebate_per_euro: s.rebate_per_euro.map(nz),
        can_front_cost: s.can_front_cost.map(nz),
        cost_per_retrofit: [nz(s.cost_per_retrofit)],
        public_cost: [s.public_cost],
        bills_saved: [s.bills_saved],
        buildings_by_state: BUILDING_STATES.map(k => s.state_counts[k]),
        cost_parts: s.cost_per_retrofit_parts ? [s.cost_per_retrofit_parts.base, s.cost_per_retrofit_parts.markup] : [NaN, NaN],
        canvass_hours: s.canvass_hours_by_quintile.slice(),
        leisure_hours: s.leisure_hours_by_quintile.slice(),
        net_cash_by_quintile: s.net_cash_by_quintile.map(nz),
        shared_by_state: [s.shared_counts.pending, s.shared_counts.approved],
        buildings_by_tenure: TENURES.map(k => s.tenure_counts[k]),
        rental_share: [fr.buildings.length ? s.tenure_counts.rental / fr.buildings.length : 0.0],
      },
    };
  }

  const NO_BUILDINGS_MESSAGE = 'great-retrofit: the scene has no residential building to model (0 model buildings), so there is nothing to run. ' +
    'Load a scene with homes, or check that its buildings are not all marked non-residential or of invalid size.';
  // Manifest params -> core Params. `ents.building.specs` (from bind.js, once the shell passes it) beats the synthetic scene.
  // The run length is not a parameter here: the shell asks for steps up to the manifest's time.steps.
  function paramsFromPack(p, ents, seed) {
    const o = Object.assign({}, p, { seed: seed | 0 });
    const b = ents && ents.building;
    // A scene was bound (specs given, count declared) and nothing in it is residential: say so. No fallback to the synthetic buildings (SM-7).
    if (b && ((Array.isArray(b.specs) && b.specs.length === 0) || b.count === 0)) throw new Error(NO_BUILDINGS_MESSAGE);
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
    FRAME_SCHEMA_VERSION, BUILDING_STATES, SHARED_STATES, TENURES, DELIVERY_MODES, ENERGY_SCENARIOS, CREDIT_ACCESS, DEFAULTS,
    npv, financing, rebate, credit, ownership, delivery, sceneEntities,
    Params, Simulation, runSimulation, toPackFrame, pyRound, pySum, NO_BUILDINGS_MESSAGE,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.GreatRetrofit = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
