/* Weather stations with a monthly rain series on Kalshi.
 *
 * `rainSeries` values are real Kalshi series tickers (read from the Kalshi
 * API's series list on 2026-11-14). Everything else here is approximate:
 * coordinates are the city's main airport to two decimals, and `julyHot`
 * (a typical hottest July day, degrees F) and `julyRain` (a typical July
 * rainfall, inches) are round figures used only to give the SAMPLE July
 * markets believable thresholds. They are not climate normals.
 */
(function (B) {
  'use strict';

  B.stations = [
    { id: 'chi', city: 'Chicago', lat: 41.98, lon: -87.90, rainSeries: 'KXRAINCHIM', julyHot: 95, julyRain: 3.7 },
    { id: 'ind', city: 'Indianapolis', lat: 39.72, lon: -86.29, rainSeries: 'KXRAININDM', julyHot: 93, julyRain: 4.4 },
    { id: 'msp', city: 'Minneapolis', lat: 44.88, lon: -93.22, rainSeries: 'KXRAINMINM', julyHot: 94, julyRain: 4.0 },
    { id: 'mke', city: 'Milwaukee', lat: 42.95, lon: -87.90, rainSeries: 'KXRAINMKEM', julyHot: 92, julyRain: 3.7 },
    { id: 'dtw', city: 'Detroit', lat: 42.21, lon: -83.35, rainSeries: 'KXRAINDTWM', julyHot: 93, julyRain: 3.4 },
    { id: 'sgf', city: 'Springfield, Missouri', lat: 37.24, lon: -93.39, rainSeries: 'KXRAINSGFM', julyHot: 96, julyRain: 3.6 },
    { id: 'okc', city: 'Oklahoma City', lat: 35.39, lon: -97.60, rainSeries: 'KXRAINOKCM', julyHot: 102, julyRain: 2.9 },
    { id: 'den', city: 'Denver', lat: 39.85, lon: -104.66, rainSeries: 'KXRAINDENM', julyHot: 98, julyRain: 2.1 },
    { id: 'lex', city: 'Lexington, Kentucky', lat: 38.04, lon: -84.61, rainSeries: 'KXRAINLEXM', julyHot: 93, julyRain: 4.7 },
    { id: 'pit', city: 'Pittsburgh', lat: 40.49, lon: -80.23, rainSeries: 'KXRAINPITM', julyHot: 91, julyRain: 4.2 },
    { id: 'sat', city: 'San Antonio', lat: 29.53, lon: -98.47, rainSeries: 'KXRAINSATXM', julyHot: 101, julyRain: 2.4 },
    { id: 'hou', city: 'Houston', lat: 29.98, lon: -95.36, rainSeries: 'KXRAINHOUM', julyHot: 98, julyRain: 3.8 },
    { id: 'msy', city: 'New Orleans', lat: 29.99, lon: -90.25, rainSeries: 'KXRAINNOLAM', julyHot: 95, julyRain: 6.0 },
    { id: 'tpa', city: 'Tampa', lat: 27.97, lon: -82.53, rainSeries: 'KXRAINTPAM', julyHot: 94, julyRain: 7.6 },
    { id: 'phl', city: 'Philadelphia', lat: 39.87, lon: -75.24, rainSeries: 'KXRAINPHILM', julyHot: 96, julyRain: 4.4 },
    { id: 'nyc', city: 'New York', lat: 40.78, lon: -73.97, rainSeries: 'KXRAINNYCM', julyHot: 95, julyRain: 4.6 },
    { id: 'dca', city: 'Washington, DC', lat: 38.85, lon: -77.04, rainSeries: 'KXRAINDCM', julyHot: 97, julyRain: 4.3 },
    { id: 'bos', city: 'Boston', lat: 42.36, lon: -71.01, rainSeries: 'KXRAINBOSM', julyHot: 95, julyRain: 3.3 },
    { id: 'sea', city: 'Seattle', lat: 47.45, lon: -122.31, rainSeries: 'KXRAINSEAM', julyHot: 90, julyRain: 0.7 }
  ];

  /* Great-circle distance in miles. */
  B.milesBetween = function (lat1, lon1, lat2, lon2) {
    const rad = Math.PI / 180;
    const a = Math.sin((lat2 - lat1) * rad / 2) ** 2 +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin((lon2 - lon1) * rad / 2) ** 2;
    return 3958.8 * 2 * Math.asin(Math.sqrt(a));
  };

  B.nearestStation = function (lat, lon) {
    let best = null;
    let bestMiles = Infinity;
    B.stations.forEach(function (s) {
      const d = B.milesBetween(lat, lon, s.lat, s.lon);
      if (d < bestMiles) { bestMiles = d; best = s; }
    });
    return { station: best, miles: bestMiles };
  };
})(window.FarmerJoe = window.FarmerJoe || {});
