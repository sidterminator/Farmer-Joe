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

  /* Pick `count` simulated seasons to stand in for all of them on a
   * harvest-by-harvest chart. One season comes from each slice of the revenue
   * range, so the group swings like the whole simulation does. Within each
   * slice the season is chosen so that, across the group, every market pays
   * out about as often as it does overall, in the same kinds of season and
   * together with the same other markets. That keeps the chart honest for any
   * mix of contracts drawn on it. Returns season indices, low revenue first.
   *
   * payouts: [Uint8Array] of Yes payouts, one per market. */
  function representativeSeasons(revenue, payouts, count) {
    const N = revenue.length;
    const order = Array.from({ length: N }, function (_, i) { return i; }).sort(function (a, b) { return revenue[a] - revenue[b]; });
    const mu = mean(revenue);
    const sigma = sd(revenue) || 1;
    const J = payouts.length;

    // Targets from the full simulation.
    const rate = payouts.map(function (x) { return mean(x); });
    const tilt = payouts.map(function (x) {
      let s = 0;
      for (let i = 0; i < N; i++) s += x[i] * (revenue[i] - mu) / sigma;
      return s / N;
    });
    const pair = [];
    for (let j = 0; j < J; j++) for (let k = j + 1; k < J; k++) {
      let s = 0;
      for (let i = 0; i < N; i++) s += payouts[j][i] * payouts[k][i];
      pair.push(s / N);
    }

    const size = Math.floor(N / count);
    const span = Math.min(size, 80);
    const pools = [];
    for (let c = 0; c < count; c++) {
      const mid = c * size + Math.floor(size / 2);
      pools.push(order.slice(mid - Math.floor(span / 2), mid + Math.ceil(span / 2)));
    }
    const chosen = pools.map(function (pool) { return pool[Math.floor(pool.length / 2)]; });

    function miss() {
      let e = 0;
      let p = 0;
      for (let j = 0; j < J; j++) {
        let r = 0;
        let t = 0;
        for (let c = 0; c < count; c++) {
          const i = chosen[c];
          r += payouts[j][i];
          t += payouts[j][i] * (revenue[i] - mu) / sigma;
        }
        e += 4 * Math.pow(r / count - rate[j], 2) + Math.pow(t / count - tilt[j], 2);
        for (let k = j + 1; k < J; k++) {
          let both = 0;
          for (let c = 0; c < count; c++) both += payouts[j][chosen[c]] * payouts[k][chosen[c]];
          e += Math.pow(both / count - pair[p++], 2);
        }
      }
      return e;
    }

    for (let pass = 0; pass < 3; pass++) {
      for (let c = 0; c < count; c++) {
        let best = chosen[c];
        let bestMiss = miss();
        for (let q = 0; q < pools[c].length; q++) {
          chosen[c] = pools[c][q];
          const m = miss();
          if (m < bestMiss) { bestMiss = m; best = pools[c][q]; }
        }
        chosen[c] = best;
      }
    }
    return chosen;
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
    representativeSeasons: representativeSeasons
  };
})(window.FarmerJoe = window.FarmerJoe || {});
