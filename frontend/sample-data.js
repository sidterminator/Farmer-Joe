/* SAMPLE DATA. Everything in this file is made up for the demo: the farm, the
 * three markets, their prices and the simulated seasons. Nothing here is a
 * live quote or a real forecast.
 *
 * This file is the seam for the real backend. `Bizfax.source` is the only
 * thing app.js talks to; replace its two functions with fetch() calls that
 * return the same shapes (documented in README.md) and the UI needs no change.
 */
(function (B) {
  'use strict';

  const SEASONS = 20000;

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

  function normalSource(rand) {
    let spare = null;
    return function () {
      if (spare !== null) { const v = spare; spare = null; return v; }
      let u = 0;
      while (u === 0) u = rand();
      const r = Math.sqrt(-2 * Math.log(u));
      const t = 2 * Math.PI * rand();
      spare = r * Math.sin(t);
      return r * Math.cos(t);
    };
  }

  function buildScenario() {
    const normal = normalSource(mulberry32(20261114));

    const farmShock = new Float64Array(SEASONS);
    const hottest = new Float64Array(SEASONS);
    const rainfall = new Float64Array(SEASONS);
    const national = new Float64Array(SEASONS);

    // Hot Julys tend to be dry Julys.
    const HEAT_RAIN = -0.45;
    // Weather stress on corn: heat hurts, rain helps. Scaled to unit variance.
    const A = -0.65;
    const C = 0.45;
    const stressSd = Math.sqrt(A * A + C * C + 2 * A * C * HEAT_RAIN);
    const FARM_WEATHER = 0.85;     // share of the farm's yield shock that is weather
    const NATIONAL_WEATHER = 0.6;  // the national crop follows local weather less closely

    for (let i = 0; i < SEASONS; i++) {
      const heat = normal();
      const rain = HEAT_RAIN * heat + Math.sqrt(1 - HEAT_RAIN * HEAT_RAIN) * normal();
      const stress = (A * heat + C * rain) / stressSd;

      farmShock[i] = FARM_WEATHER * stress + Math.sqrt(1 - FARM_WEATHER * FARM_WEATHER) * normal();
      hottest[i] = 94.6 + 3.5 * heat;                      // degrees F
      rainfall[i] = Math.exp(Math.log(3.4) + 0.45 * rain);   // inches
      national[i] = 181 + 7 * (NATIONAL_WEATHER * stress + Math.sqrt(1 - NATIONAL_WEATHER * NATIONAL_WEATHER) * normal());
    }

    function payouts(values, pays) {
      const out = new Uint8Array(values.length);
      for (let i = 0; i < values.length; i++) out[i] = pays(values[i]) ? 1 : 0;
      return out;
    }

    return {
      sample: true,
      fallbackYieldSd: 20,
      farmShock: farmShock,
      farm: {
        name: 'Sample farm',
        crop: 'corn',
        acres: 320,
        pricePerBu: 4.2,
        place: 'Kankakee County, Illinois',
        seasons: [
          { year: 2014, yield: 201 }, { year: 2015, yield: 178 }, { year: 2016, yield: 207 },
          { year: 2017, yield: 196 }, { year: 2018, yield: 211 }, { year: 2019, yield: 152 },
          { year: 2020, yield: 188 }, { year: 2021, yield: 214 }, { year: 2022, yield: 203 },
          { year: 2023, yield: 171 }, { year: 2024, yield: 219 }, { year: 2025, yield: 186 }
        ]
      },
      markets: [
        {
          id: 'temp',
          name: 'Temp',
          question: 'Hottest July day at Chicago Midway is 95°F or above',
          measure: 'Hottest July day at Chicago Midway',
          settles: 'Settles Jul 31, 2027',
          source: 'Chicago Midway',
          sourceLong: 'the Chicago Midway weather station',
          unit: 'degF',
          strike: 95,
          yesWhen: 'at-or-above',
          yesCents: 40,
          noCents: 60,
          underlying: hottest,
          payoutYes: payouts(hottest, function (v) { return v >= 95; })
        },
        {
          id: 'yield',
          name: 'Yield',
          question: 'U.S. corn yield for 2027 comes in under 180 bu/acre',
          measure: 'U.S. corn yield for 2027',
          settles: 'Settles Jan 12, 2028',
          source: 'USDA crop report',
          sourceLong: 'the USDA crop report',
          unit: 'bu/ac',
          strike: 180,
          yesWhen: 'below',
          yesCents: 50,
          noCents: 50,
          underlying: national,
          payoutYes: payouts(national, function (v) { return v < 180; })
        },
        {
          id: 'rain',
          name: 'Rain',
          question: 'July rainfall at Chicago O’Hare is 3.5 inches or more',
          measure: 'July rainfall at Chicago O’Hare',
          settles: 'Settles Jul 31, 2027',
          source: 'Chicago O’Hare',
          sourceLong: 'the Chicago O’Hare weather station',
          unit: 'in',
          strike: 3.5,
          yesWhen: 'at-or-above',
          yesCents: 60,
          noCents: 40,
          underlying: rainfall,
          payoutYes: payouts(rainfall, function (v) { return v >= 3.5; })
        }
      ]
    };
  }

  B.source = {
    /* Later: fetch('/api/scenario').then(r => r.json()) */
    scenario: function () {
      return Promise.resolve(buildScenario());
    },
    /* Later: POST the seasons to the backend. For now nothing leaves the
     * browser, and `stored: false` tells the UI to say so. */
    uploadSeasons: function (seasons) {
      return Promise.resolve({ ok: true, stored: false, count: seasons.length });
    }
  };
})(window.Bizfax = window.Bizfax || {});
