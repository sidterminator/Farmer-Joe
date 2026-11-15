/* PLACEHOLDER MODEL. This is the adviser: given a farm's simulated revenue and
 * the markets on offer, it says which ones to hedge and how many dollars to
 * put into each. Replace `suggest` with the team's real model and keep the
 * shape of what it returns; the screens need no change.
 *
 * What the placeholder does: buys the side of each market that pays in the
 * farm's bad seasons, sizes the mix to be as steady as possible, leans it
 * toward cost by the farmer's priority answer, and scales it to the budget
 * (model.recommend). It knows nothing about fees, spreads or liquidity.
 */
(function (B) {
  'use strict';

  const M = B.model;
  const LOT = 100;   // contracts are bought in hundreds

  /* suggest(revenue, markets, opts) -> [{ id, side, contracts, dollars }]
   *
   *   revenue   Float64Array, farm revenue per simulated season
   *   markets   [{ id, yesCents, noCents, payoutYes, side? }]; a `side` of
   *             'yes' or 'no' pins that market to the farmer's own choice
   *   opts      { budget: dollars, stability: 0.2 (cost) .. 1 (stability) }
   *
   * A market it would not put money into comes back with dollars: 0. */
  function suggest(revenue, markets, opts) {
    const sides = markets.map(function (m) { return m.side || M.hedgeSide(revenue, m); });
    const legs = markets.map(function (m, i) { return M.sideOf(m, sides[i]); });
    const rec = M.recommend(revenue, legs, { budget: opts.budget, stability: opts.stability, lot: LOT });
    return {
      trimmed: rec.trimmed,
      picks: markets.map(function (m, i) {
        return { id: m.id, side: sides[i], contracts: rec.contracts[i], dollars: rec.contracts[i] * legs[i].price };
      })
    };
  }

  /* The most one market could usefully take on its own: the steadiest amount
   * with no budget. Used to scale that market's slider. */
  function ceiling(revenue, market, side) {
    const leg = M.sideOf(market, side);
    const contracts = M.recommend(revenue, [leg], { budget: -1, stability: 1, lot: LOT }).steadiest[0];
    return { contracts: contracts, dollars: contracts * leg.price };
  }

  B.advisor = { suggest: suggest, ceiling: ceiling, lot: LOT };
})(window.FarmerJoe = window.FarmerJoe || {});
