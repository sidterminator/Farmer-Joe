/* Hedge maths. Pure functions over plain arrays, no DOM.
 *
 * For each simulated season s:   income_s = revenue_s + n * (payout_s - price)
 * where payout is $1 or $0 and price is in dollars. See README.md for the
 * shape of the scenario these functions read.
 */
(function (B) {
  'use strict';

  function mean(a) {
    let s = 0;
    for (let i = 0; i < a.length; i++) s += a[i];
    return s / a.length;
  }

  function sd(a) {
    if (a.length < 2) return 0;
    const m = mean(a);
    let s = 0;
    for (let i = 0; i < a.length; i++) s += (a[i] - m) * (a[i] - m);
    return Math.sqrt(s / (a.length - 1));
  }

  function quantile(a, q) {
    const s = Float64Array.from(a).sort();
    const pos = (s.length - 1) * q;
    const lo = Math.floor(pos);
    const hi = Math.ceil(pos);
    return s[lo] + (s[hi] - s[lo]) * (pos - lo);
  }

  function covariance(a, b) {
    const ma = mean(a);
    const mb = mean(b);
    let s = 0;
    for (let i = 0; i < a.length; i++) s += (a[i] - ma) * (b[i] - mb);
    return s / (a.length - 1);
  }

  /* Mean and spread of the farm's own yields. With fewer than three seasons
   * the spread cannot be estimated, so the caller's fallback is used. */
  function farmYield(seasons, fallbackSd) {
    const ys = seasons.map(function (s) { return s.yield; });
    return {
      mean: mean(ys),
      sd: ys.length >= 3 ? sd(ys) : fallbackSd,
      ownSpread: ys.length >= 3
    };
  }

  /* Revenue per simulated season: acres x price x yield, where yield is the
   * farm's mean plus its spread times that season's standardised shock. */
  function farmIncome(scenario, farm) {
    const y = farmYield(farm.seasons, scenario.fallbackYieldSd);
    const z = scenario.farmShock;
    const out = new Float64Array(z.length);
    for (let i = 0; i < z.length; i++) {
      out[i] = farm.acres * farm.pricePerBu * Math.max(0, y.mean + y.sd * z[i]);
    }
    return out;
  }

  /* Payout per season and price in dollars for one side of a market. */
  function sideOf(market, side) {
    const yes = market.payoutYes;
    if (side === 'yes') return { payout: yes, price: market.yesCents / 100 };
    const no = new Uint8Array(yes.length);
    for (let i = 0; i < yes.length; i++) no[i] = 1 - yes[i];
    return { payout: no, price: market.noCents / 100 };
  }

  function hedgedIncome(revenue, side, contracts) {
    const out = new Float64Array(revenue.length);
    for (let i = 0; i < revenue.length; i++) {
      out[i] = revenue[i] + contracts * (side.payout[i] - side.price);
    }
    return out;
  }

  /* Minimum-variance hedge for a single contract: n = -Cov(X, R) / Var(X).
   * A negative answer means this side adds swing, so the answer is zero. */
  function steadiestContracts(revenue, side) {
    const x = Float64Array.from(side.payout);
    const v = covariance(x, x);
    if (v === 0) return 0;
    return Math.max(0, -covariance(x, revenue) / v);
  }

  function summary(a) {
    return { mean: mean(a), sd: sd(a), bad: quantile(a, 0.05) };
  }

  function chance(side) {
    return mean(side.payout);
  }

  /* Share of values per bin over [lo, hi), lightly smoothed (1-2-1) so the
   * shape reads as a distribution instead of sampling noise. */
  function histogram(a, lo, hi, bins) {
    const counts = new Float64Array(bins);
    const w = (hi - lo) / bins;
    for (let i = 0; i < a.length; i++) {
      const k = Math.floor((a[i] - lo) / w);
      if (k >= 0 && k < bins) counts[k] += 1;
    }
    const out = new Float64Array(bins);
    for (let k = 0; k < bins; k++) {
      const l = counts[Math.max(0, k - 1)];
      const r = counts[Math.min(bins - 1, k + 1)];
      out[k] = (l + 2 * counts[k] + r) / 4 / a.length;
    }
    return out;
  }

  B.model = {
    mean: mean,
    sd: sd,
    quantile: quantile,
    farmYield: farmYield,
    farmIncome: farmIncome,
    sideOf: sideOf,
    hedgedIncome: hedgedIncome,
    steadiestContracts: steadiestContracts,
    summary: summary,
    chance: chance,
    histogram: histogram
  };
})(window.Bizfax = window.Bizfax || {});
