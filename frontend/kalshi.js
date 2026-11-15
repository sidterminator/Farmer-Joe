/* Kalshi market data, read straight from the browser.
 *
 * NOT WIRED TO A SCREEN RIGHT NOW: the "Live on Kalshi" panel was removed from
 * the advice screen, and index.html no longer loads this file. It is kept as
 * the working client for when live prices come back.
 *
 * This uses Kalshi's DEMO exchange, which answers market-data requests from a
 * web page. The production API refuses requests that carry a browser Origin,
 * and placing orders needs a signed API key on either one, so anything beyond
 * reading open markets belongs on the team's server.
 *
 * The only thing sent is a series ticker such as KXRAINCHIM.
 */
(function (B) {
  'use strict';

  const BASE = 'https://demo-api.kalshi.co/trade-api/v2';
  const TIMEOUT_MS = 8000;

  /* An ask of $0 or $1 means nobody is offering that side, not a real price. */
  function toCents(dollars) {
    const v = Math.round(parseFloat(dollars) * 100);
    return isFinite(v) && v > 0 && v < 100 ? v : null;
  }

  /* Resolves to the open event of a series:
   *   { ticker, title, fetchedAt, markets: [{ ticker, label, yesCents, noCents, closes }] }
   * or to null when the series has nothing open. Rejects when Kalshi cannot
   * be reached. */
  function openEvent(seriesTicker) {
    const controller = new AbortController();
    const timer = setTimeout(function () { controller.abort(); }, TIMEOUT_MS);
    const url = BASE + '/events?series_ticker=' + encodeURIComponent(seriesTicker) +
      '&status=open&with_nested_markets=true&limit=1';
    return fetch(url, { signal: controller.signal, headers: { Accept: 'application/json' } })
      .then(function (res) {
        if (!res.ok) throw new Error('Kalshi answered ' + res.status);
        return res.json();
      })
      .then(function (data) {
        const event = data && data.events && data.events[0];
        if (!event) return null;
        const markets = (event.markets || [])
          .filter(function (m) { return m.status === 'active'; })
          .sort(function (a, b) { return (a.floor_strike || a.cap_strike || 0) - (b.floor_strike || b.cap_strike || 0); })
          .map(function (m) {
            return {
              ticker: String(m.ticker || ''),
              label: String(m.yes_sub_title || m.subtitle || m.title || ''),
              yesCents: toCents(m.yes_ask_dollars),
              noCents: toCents(m.no_ask_dollars),
              closes: m.close_time || null
            };
          });
        return { ticker: String(event.event_ticker || ''), title: String(event.title || ''), fetchedAt: new Date(), markets: markets };
      })
      .finally(function () { clearTimeout(timer); });
  }

  B.kalshi = { base: BASE, openEvent: openEvent };
})(window.FarmerJoe = window.FarmerJoe || {});
