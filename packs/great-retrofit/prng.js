/* Portable PRNG (mulberry32): mirror of v3/src/retrofit_v3/common/rng.py.
 * Keep definitions identical; vectors in v3/test_v3/vectors/prng.json. */
(function (root) {
  'use strict';
  const TWO32 = 4294967296;

  function mix32(h) {
    h >>>= 0;
    h ^= h >>> 16; h = Math.imul(h, 0x85EBCA6B) >>> 0;
    h ^= h >>> 13; h = Math.imul(h, 0xC2B2AE35) >>> 0;
    h ^= h >>> 16;
    return h >>> 0;
  }

  function hashUniform(seed, i, j) {
    j = j || 0;
    let h = mix32((seed >>> 0) ^ Math.imul(i >>> 0, 0x9E3779B1));
    h = mix32(h ^ Math.imul(j >>> 0, 0x85EBCA6B));
    return h / TWO32;
  }

  class Rng {
    constructor(seed) { this.state = (seed || 0) >>> 0; }
    nextU32() {
      this.state = (this.state + 0x6D2B79F5) >>> 0;
      let t = this.state;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return (t ^ (t >>> 14)) >>> 0;
    }
    random() { return this.nextU32() / TWO32; }
    gaussian() {
      const u1 = 1 - this.random();
      const u2 = this.random();
      return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    }
    lognormal(mu, sigma) { return Math.exp(mu + sigma * this.gaussian()); }
    uniform(lo, hi) { return lo + (hi - lo) * this.random(); }
    randint(n) { return Math.floor(this.random() * n); }
    choice(arr) { return arr[this.randint(arr.length)]; }
    weightedIndex(weights) {
      let total = 0;
      for (const w of weights) total += w;
      const x = this.random() * total;
      let acc = 0;
      for (let k = 0; k < weights.length; k++) {
        acc += weights[k];
        if (x < acc) return k;
      }
      return weights.length - 1;
    }
  }

  const api = { Rng, mix32, hashUniform, makeRng: (s) => new Rng(s) };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RetrofitPRNG = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
