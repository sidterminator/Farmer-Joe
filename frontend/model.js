/* Hedge maths. Pure functions over plain arrays, no DOM.
 *
 * For each simulated season s:
 *   income_s = revenue_s + sum over contracts j of  n_j * (payout_sj - price_j)
 * where payout is $1 or $0 and price is in dollars. README.md describes the
 * scenario these functions read.
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

  /* Revenue per simulated season: acres x price x yield, where yield is the
   * farm's normal yield plus its spread times that season's standardised shock. */
  function farmIncome(shock, farm) {
    const out = new Float64Array(shock.length);
    for (let i = 0; i < shock.length; i++) {
      out[i] = farm.acres * farm.price * Math.max(0, farm.yield + farm.yieldSd * shock[i]);
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

  /* The side that pays in the seasons the farm earns least. */
  function hedgeSide(revenue, market) {
    return covariance(Float64Array.from(market.payoutYes), revenue) <= 0 ? 'yes' : 'no';
  }

  /* legs: [{ payout, price, contracts }] */
  function planIncome(revenue, legs) {
    const out = Float64Array.from(revenue);
    for (let j = 0; j < legs.length; j++) {
      const leg = legs[j];
      if (!leg.contracts) continue;
      for (let i = 0; i < out.length; i++) out[i] += leg.contracts * (leg.payout[i] - leg.price);
    }
    return out;
  }

  function solve(A, b) {
    const n = b.length;
    const M = A.map(function (row, i) { return row.concat([b[i]]); });
    for (let col = 0; col < n; col++) {
      let pivot = col;
      for (let r = col + 1; r < n; r++) if (Math.abs(M[r][col]) > Math.abs(M[pivot][col])) pivot = r;
      if (Math.abs(M[pivot][col]) < 1e-12) return null;
      const tmp = M[col]; M[col] = M[pivot]; M[pivot] = tmp;
      for (let r = 0; r < n; r++) {
        if (r === col) continue;
        const f = M[r][col] / M[col][col];
        for (let c = col; c <= n; c++) M[r][c] -= f * M[col][c];
      }
    }
    return M.map(function (row, i) { return row[n] / row[i]; });
  }

  /* Solve S n = target over the allowed legs, dropping any leg whose answer
   * is negative (you cannot buy a negative number of contracts). */
  function solveNonNegative(S, target, allowed) {
    const n = new Array(target.length).fill(0);
    let active = allowed.slice();
    while (active.length) {
      const sol = solve(active.map(function (i) { return active.map(function (j) { return S[i][j]; }); }),
        active.map(function (i) { return target[i]; }));
      if (!sol) return n;
      let worst = -1;
      for (let a = 0; a < sol.length; a++) if (sol[a] < 0 && (worst < 0 || sol[a] < sol[worst])) worst = a;
      if (worst < 0) {
        active.forEach(function (i, a) { n[i] = sol[a]; });
        return n;
      }
      active = active.filter(function (_, a) { return a !== worst; });
    }
    return n;
  }

  /* How many of each contract to buy.
   *
   * legs: [{ payout, price }], each already on its hedging side.
   * opts.stability: 1 buys the steadiest mix whatever it costs. Lower values
   *   lean toward cost: maximise  mean - lambda * variance, which buys less of
   *   contracts the model thinks are overpriced, and never more than the
   *   steadiest amount.
   * opts.budget: cap on total cost in dollars; the mix is scaled down to fit.
   * opts.lot: round down to this many contracts.
   */
  function recommend(revenue, legs, opts) {
    const k = legs.length;
    if (!k) return { contracts: [], steadiest: [], trimmed: false };
    const X = legs.map(function (l) { return Float64Array.from(l.payout); });
    const cov = X.map(function (x) { return covariance(x, revenue); });
    const S = X.map(function (xi) { return X.map(function (xj) { return covariance(xi, xj); }); });
    const usable = [];
    for (let i = 0; i < k; i++) if (S[i][i] > 1e-9) usable.push(i);

    const steadiest = solveNonNegative(S, cov.map(function (v) { return -v; }), usable);

    const s = Math.min(1, Math.max(0.05, opts.stability));
    const tau = 2 * sd(revenue) * (1 - s) / s;
    const tilted = solveNonNegative(S, cov.map(function (v, i) { return tau * (mean(X[i]) - legs[i].price) - v; }), usable);
    const kept = usable.filter(function (i) { return tilted[i] > 0; });
    const cap = solveNonNegative(S, cov.map(function (v) { return -v; }), kept);
    let n = tilted.map(function (v, i) { return Math.max(0, Math.min(v, cap[i])); });

    let cost = 0;
    for (let i = 0; i < k; i++) cost += n[i] * legs[i].price;
    let trimmed = false;
    if (opts.budget >= 0 && cost > opts.budget) {
      const f = cost > 0 ? opts.budget / cost : 0;
      n = n.map(function (v) { return v * f; });
      trimmed = true;
    }
    const lot = opts.lot || 1;
    return {
      contracts: n.map(function (v) { return Math.floor(v / lot) * lot; }),
      steadiest: steadiest.map(function (v) { return Math.round(v / lot) * lot; }),
      trimmed: trimmed
    };
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
    farmIncome: farmIncome,
    sideOf: sideOf,
    hedgeSide: hedgeSide,
    planIncome: planIncome,
    recommend: recommend,
    summary: summary,
    chance: chance,
    histogram: histogram
  };
})(window.FarmerJoe = window.FarmerJoe || {});
