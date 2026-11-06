# v3: economic retrofit model (skeleton)

Monthly household decision (NPV over the stay horizon, plus ability to finance), three ownership types (owner-occupied, condo, rental stub) and three delivery modes (rebate with market vendor, pass-through, public service). **Structure only: every number is a placeholder** ([docs/placeholders.md](docs/placeholders.md)); do not quote results.

- `src/retrofit_v3/`: `params`, `model.run_simulation(params, on_step)`, pure modules (`npv`, `financing`, `rebate`, `credit`), strategies (`ownership`, `delivery`), `scene_entities`, `frames` (contract: [docs/frame-schema.md](docs/frame-schema.md)).
- `common/rng.py` and `js/prng.js`: mulberry32 plus helpers, identical in both languages; shared vectors in `test_v3/vectors/prng.json` (regenerate with `tools/gen_prng_vectors.py` only if the PRNG definition changes). All model randomness goes through it (stateless `hash_uniform` for per-agent, per-month draws, so changing a policy never shifts other agents' draws).
- Stdlib only (no numpy), to ease the JavaScript port.

Tests: `pytest v3` (also runs `node v3/js/test_prng.js` if node is installed).
