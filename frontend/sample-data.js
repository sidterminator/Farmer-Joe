/* SAMPLE DATA and the seam for the real backend.
 *
 * The simulated seasons, the three July markets and their prices are made up
 * for the demo. Nothing built here is a live quote or a real forecast. The one
 * live piece is `liveMarkets`, which reads open markets from Kalshi's demo API.
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

  /* Sample assumption: weather at the settlement station tracks the farm's
   * less the farther away it is, and rain is more local than temperature. */
  function tracking(miles) {
    return {
      temperature: Math.min(0.97, Math.max(0.2, Math.exp(-miles / 600))),
      rain: Math.min(0.95, Math.max(0.12, Math.exp(-miles / 250)))
    };
  }

  /* farm: { crop, station, miles }  ->  scenario for that farm's nearest station. */
  function buildScenario(farm) {
    const z = getDraws();
    const crop = CROPS[farm.crop] || CROPS.corn;
    const st = farm.station;
    const track = tracking(farm.miles);

    // Hot Julys tend to be dry Julys.
    const HEAT_RAIN = -0.45;
    // Weather stress on the crop: heat hurts, rain helps. Scaled to unit variance.
    const A = -0.65;
    const C = 0.45;
    const stressSd = Math.sqrt(A * A + C * C + 2 * A * C * HEAT_RAIN);
    const FARM_WEATHER = 0.85;     // share of the farm's yield shock that is weather
    const NATIONAL_WEATHER = 0.6;  // the national crop follows local weather less closely

    const farmShock = new Float64Array(SEASONS);
    const hottest = new Float64Array(SEASONS);
    const rainfall = new Float64Array(SEASONS);
    const national = new Float64Array(SEASONS);
    const rainStrike = Math.max(0.5, Math.round(st.julyRain * 2) / 2);

    for (let i = 0; i < SEASONS; i++) {
      const heat = z[0][i];
      const rain = HEAT_RAIN * heat + Math.sqrt(1 - HEAT_RAIN * HEAT_RAIN) * z[1][i];
      const stress = (A * heat + C * rain) / stressSd;
      farmShock[i] = FARM_WEATHER * stress + Math.sqrt(1 - FARM_WEATHER * FARM_WEATHER) * z[2][i];

      const stationHeat = track.temperature * heat + Math.sqrt(1 - track.temperature * track.temperature) * z[3][i];
      const stationRain = track.rain * rain + Math.sqrt(1 - track.rain * track.rain) * z[4][i];
      hottest[i] = st.julyHot - 0.4 + 3.5 * stationHeat;
      rainfall[i] = Math.exp(Math.log(st.julyRain) + 0.45 * stationRain);
      national[i] = crop.nationalYield + crop.nationalSd * (NATIONAL_WEATHER * stress + Math.sqrt(1 - NATIONAL_WEATHER * NATIONAL_WEATHER) * z[5][i]);
    }

    const yieldStrike = Math.round(crop.nationalYield - 0.14 * crop.nationalSd);
    const tempPay = payouts(hottest, function (v) { return v >= st.julyHot; });
    const rainPay = payouts(rainfall, function (v) { return v >= rainStrike; });
    const yieldPay = payouts(national, function (v) { return v < yieldStrike; });
    // Sample prices sit a few points off the model's chance, so the screen
    // can show a cheap contract, an expensive one and one in between.
    const tempYes = cents(share(tempPay), -5);
    const rainYes = cents(share(rainPay), 7);
    const yieldYes = cents(share(yieldPay), 6);

    return {
      sample: true,
      seasons: SEASONS,
      farmShock: farmShock,
      tracking: track,
      markets: [
        {
          id: 'temp',
          name: 'Temp',
          worry: 'heat',
          question: 'Hottest July day in ' + st.city + ' is ' + st.julyHot + '°F or above',
          yesPaysWhen: 'the hottest July day in ' + st.city + ' reaches ' + st.julyHot + '°F',
          noPaysWhen: 'the hottest July day in ' + st.city + ' stays under ' + st.julyHot + '°F',
          settles: 'Settles Jul 31, 2027',
          yesCents: tempYes,
          noCents: 100 - tempYes,
          payoutYes: tempPay
        },
        {
          id: 'yield',
          name: 'Yield',
          worry: 'crop',
          question: 'U.S. ' + crop.lower + ' yield for 2027 comes in under ' + yieldStrike + ' bushels per acre',
          yesPaysWhen: 'the U.S. ' + crop.lower + ' yield for 2027 comes in under ' + yieldStrike + ' bushels per acre',
          noPaysWhen: 'the U.S. ' + crop.lower + ' yield for 2027 comes in at ' + yieldStrike + ' bushels per acre or more',
          settles: 'Settles Jan 12, 2028',
          yesCents: yieldYes,
          noCents: 100 - yieldYes,
          payoutYes: yieldPay
        },
        {
          id: 'rain',
          name: 'Rain',
          worry: 'drought',
          question: 'July rainfall in ' + st.city + ' is ' + rainStrike.toFixed(1) + ' inches or more',
          yesPaysWhen: 'July rainfall in ' + st.city + ' reaches ' + rainStrike.toFixed(1) + ' inches',
          noPaysWhen: 'July rainfall in ' + st.city + ' comes in under ' + rainStrike.toFixed(1) + ' inches',
          settles: 'Settles Jul 31, 2027',
          yesCents: rainYes,
          noCents: 100 - rainYes,
          payoutYes: rainPay
        }
      ]
    };
  }

  B.crops = CROPS;

  B.source = {
    /* Later: POST the farm to the team's server and return its scenario. */
    scenario: function (farm) {
      return Promise.resolve(buildScenario(farm));
    },

    /* Live: the open monthly rain market at the farm's nearest station, read
     * from Kalshi's demo API in the browser. */
    liveMarkets: function (station) {
      return B.kalshi.openEvent(station.rainSeries);
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
