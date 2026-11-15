/* SAMPLE DATA and the seam for the real backend.
 *
 * The sample is deliberately EXAGGERATED so the demo's graph shows a large
 * gap between hedging and not hedging. See the note above buildScenario.
 *
 * The simulated seasons, the three July markets and their prices are made up
 * for the demo. Nothing built here is a live quote or a real forecast.
 *
 * `FarmerJoe.source` is the only data interface app.js uses. Replace its
 * functions with calls to the team's server and keep the shapes documented in
 * README.md; the screens need no change.
 */
(function (B) {
  'use strict';

  const SEASONS = 20000;

  const CROPS = {
    corn: { label: 'Corn', lower: 'corn', yield: 200, price: 4.5, spread: 0.10, nationalYield: 181, nationalSd: 7 },
    soybeans: { label: 'Soybeans', lower: 'soybean', yield: 60, price: 10.5, spread: 0.11, nationalYield: 52, nationalSd: 3 },
    wheat: { label: 'Wheat', lower: 'wheat', yield: 55, price: 5.75, spread: 0.14, nationalYield: 51, nationalSd: 3 }
  };

  /* Small seeded generator so the demo shows the same numbers every time. */
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function normals(count, seed) {
    const rand = mulberry32(seed);
    const out = new Float64Array(count);
    for (let i = 0; i < count; i += 2) {
      let u = 0;
      while (u === 0) u = rand();
      const r = Math.sqrt(-2 * Math.log(u));
      const t = 2 * Math.PI * rand();
      out[i] = r * Math.cos(t);
      if (i + 1 < count) out[i + 1] = r * Math.sin(t);
    }
    return out;
  }

  // Six independent draws per simulated season, made once.
  let draws = null;
  function getDraws() {
    if (!draws) draws = [1, 2, 3, 4, 5, 6].map(function (k) { return normals(SEASONS, 20261114 + k * 7919); });
    return draws;
  }

  function payouts(values, pays) {
    const out = new Uint8Array(values.length);
    for (let i = 0; i < values.length; i++) out[i] = pays(values[i]) ? 1 : 0;
    return out;
  }

  function share(values) {
    let s = 0;
    for (let i = 0; i < values.length; i++) s += values[i];
    return s / values.length;
  }

  function cents(chance, offset) {
    return Math.min(95, Math.max(5, Math.round(chance * 100) + offset));
  }

  /* EXAGGERATED ON PURPOSE (the user's request, 2026-11-14). The demo is meant
   * to make the effect of hedging easy to see, so this sample world is far
   * kinder to the hedge than a real one would be:
   *   - a hot July or a dry July each knocks a large, fixed amount off the
   *     farm's yield, and little else moves it;
   *   - the farm's weather is the station's weather, whatever the distance;
   *   - the contracts that pay in those years are priced far below the
   *     model's own chance of them paying.
   * None of this is a finding. Do not present these numbers as results. */
  const HOT_LOSS = 2.2;    // yield lost in a hot July, in units of the farm's yield spread
  const DRY_LOSS = 1.5;   // and in a dry one
  const OTHER = 0.25;      // everything else that moves the farm's yield
  const BARGAIN = 28;      // points below the model's chance that the hedging side costs

  /* farm: { crop, station, miles }  ->  scenario for that farm's nearest station. */
  function buildScenario(farm) {
    const z = getDraws();
    const crop = CROPS[farm.crop] || CROPS.corn;
    const st = farm.station;

    // Hot Julys tend to be dry Julys.
    const HEAT_RAIN = -0.45;
    const hottest = new Float64Array(SEASONS);
    const rainfall = new Float64Array(SEASONS);
    const rainStrike = Math.max(0.5, Math.round(st.julyRain * 2) / 2);
    for (let i = 0; i < SEASONS; i++) {
      const heat = z[0][i];
      const rain = HEAT_RAIN * heat + Math.sqrt(1 - HEAT_RAIN * HEAT_RAIN) * z[1][i];
      hottest[i] = st.julyHot - 0.4 + 3.5 * heat;
      rainfall[i] = Math.exp(Math.log(st.julyRain) + 0.45 * rain);
    }
    const tempPay = payouts(hottest, function (v) { return v >= st.julyHot; });
    const rainPay = payouts(rainfall, function (v) { return v >= rainStrike; });

    // The farm's yield falls by a set amount in a hot July and in a dry one,
    // centred so an average season sits at the farm's normal yield.
    const centre = HOT_LOSS * share(tempPay) + DRY_LOSS * (1 - share(rainPay));
    const farmShock = new Float64Array(SEASONS);
    const national = new Float64Array(SEASONS);
    for (let i = 0; i < SEASONS; i++) {
      const weather = centre - HOT_LOSS * tempPay[i] - DRY_LOSS * (1 - rainPay[i]);
      farmShock[i] = weather + OTHER * z[2][i];
      national[i] = crop.nationalYield + crop.nationalSd * (0.7 * weather + 0.7 * z[5][i]);
    }

    const yieldStrike = Math.round(crop.nationalYield - 0.14 * crop.nationalSd);
    const yieldPay = payouts(national, function (v) { return v < yieldStrike; });
    // Bargain prices: the side that pays in the farm's bad years costs far
    // less than the model's chance of it paying.
    const tempYes = cents(share(tempPay), -BARGAIN);
    const rainYes = cents(share(rainPay), BARGAIN);       // so No, the dry-July side, is the bargain
    const yieldYes = cents(share(yieldPay), -BARGAIN / 2);

    return {
      sample: true,
      exaggerated: true,
      seasons: SEASONS,
      farmShock: farmShock,
      markets: [
        {
          id: 'temp',
          name: 'Temp',
          preselect: true,
          question: st.city + ' hits ' + st.julyHot + '\u00b0F in July',
          yesCents: tempYes,
          noCents: 100 - tempYes,
          payoutYes: tempPay
        },
        {
          id: 'yield',
          name: 'Yield',
          preselect: false,
          question: 'U.S. ' + crop.lower + ' yield under ' + yieldStrike + ' bu/acre',
          caveat: 'May not exist on Kalshi.',
          yesCents: yieldYes,
          noCents: 100 - yieldYes,
          payoutYes: yieldPay
        },
        {
          id: 'rain',
          name: 'Rain',
          preselect: true,
          question: st.city + ' gets ' + rainStrike.toFixed(1) + ' in of July rain',
          yesCents: rainYes,
          noCents: 100 - rainYes,
          payoutYes: rainPay
        }
      ]
    };
  }

  B.crops = CROPS;

  /* Real data comes from server.py (POST /api/scenario) when the page is served by it.
   * Opened from disk, served by a plain static server, or on any error, we fall back to the
   * sample scenario above so the demo never shows a blank screen. */
  function decodeScenario(d) {
    const revenue = Float64Array.from(d.revenue);
    d.markets.forEach(function (m) {
      const bin = atob(m.payoutYes);
      const pay = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) pay[i] = bin.charCodeAt(i);
      m.payoutYes = pay;
    });
    d.revenue = revenue;
    return d;
  }

  function online() { return location.protocol !== 'file:' && typeof fetch === 'function'; }

  // Label the screens as real model output as soon as the API answers.
  if (online()) {
    fetch('/api/health').then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (j && j.ok) document.body.classList.add('real-data');
    }).catch(function () { /* sample mode */ });
  }

  B.source = {
    /* farm: { crop, station, miles, lat, lon, acres, yield, price, budget, stability, stationId } */
    scenario: function (farm) {
      if (!online() || farm.lat === null || farm.lat === undefined) return Promise.resolve(buildScenario(farm));
      return fetch('/api/scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: farm.lat, lon: farm.lon, crop: farm.crop, acres: farm.acres, yield: farm.yield,
          price: farm.price, budget: farm.budget, stability: farm.stability, stationId: farm.stationId
        })
      }).then(function (r) {
        if (!r.ok) throw new Error('server answered ' + r.status);
        return r.json();
      }).then(function (d) {
        document.body.classList.add('real-data');
        return decodeScenario(d);
      }).catch(function (err) {
        console.warn('Farmer Joe: using sample data (' + err.message + ')');
        document.body.classList.remove('real-data');
        return buildScenario(farm);
      });
    },

    /* Orders need a signed Kalshi API key, which a web page cannot keep safe,
     * so they go through the team's server. Until that exists this is false
     * and placeOrders refuses. Orders: [{ market, side, contracts, cents }]. */
    ordersConnected: false,
    placeOrders: function () {
      return Promise.reject(new Error('Order placement is not connected.'));
    }
  };
})(window.FarmerJoe = window.FarmerJoe || {});
