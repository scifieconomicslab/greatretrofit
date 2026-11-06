// Run: node v3/js/test_prng.js   (checks the shared vectors in v3/test_v3/vectors/prng.json)
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { Rng, hashUniform } = require('./prng.js');
const V = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'test_v3', 'vectors', 'prng.json'), 'utf8'));

const rep = (n, f) => Array.from({ length: n }, f);
const close = (a, b, tol) => a.forEach((x, i) => assert.ok(Math.abs(x - b[i]) <= tol, `${x} vs ${b[i]}`));

for (const c of V.cases) {
  const g = () => new Rng(c.seed);
  let r = g(); assert.deepStrictEqual(rep(8, () => r.nextU32()), c.u32, 'u32 ' + c.seed);
  r = g(); assert.deepStrictEqual(rep(8, () => r.random()), c.random, 'random ' + c.seed);
  r = g(); close(rep(6, () => r.gaussian()), c.gaussian, 1e-12);
  r = g(); close(rep(6, () => r.lognormal(V.lognormal[0], V.lognormal[1])), c.lognormal, 1e-12);
  r = g(); assert.deepStrictEqual(rep(10, () => r.randint(10)), c.randint10);
  r = g(); assert.deepStrictEqual(rep(10, () => r.randint(1000)), c.randint1000);
  r = g(); assert.deepStrictEqual(rep(10, () => r.choice(V.choices)), c.choice);
  r = g(); assert.deepStrictEqual(rep(12, () => r.weightedIndex(V.weights)), c.weighted_index);
  r = g(); close(rep(5, () => r.uniform(-2, 3)), c.uniform, 1e-15);
  for (const [i, j, u] of c.hash_uniform) assert.strictEqual(hashUniform(c.seed, i, j), u);
}
console.log('prng.js: all vectors OK');
