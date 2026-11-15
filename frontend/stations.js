/* Cities with a weather station that Kalshi lists rain or temperature markets on.
 *
 * `series` is a real Kalshi series ticker for that city (read from the Kalshi
 * API's series list on 2026-11-14): the monthly rain series where one exists,
 * otherwise a daily rain or temperature series. Snow-only cities are left out.
 * Great Falls and Orlando have production markets that the demo exchange does
 * not carry, so the live panel shows nothing open for them.
 *
 * Everything else here is approximate. Coordinates are the city's main airport
 * to two decimals, and `julyHot` (a typical hottest July day, degrees F) and
 * `julyRain` (a typical July rainfall, inches) are round figures used only to
 * give the SAMPLE July markets believable thresholds. They are not climate
 * normals.
 */
(function (B) {
  'use strict';

  B.stations = [
    // Corn Belt and Plains
    { id: 'chi', city: 'Chicago', lat: 41.98, lon: -87.90, series: 'KXRAINCHIM', julyHot: 95, julyRain: 3.7 },
    { id: 'ind', city: 'Indianapolis', lat: 39.72, lon: -86.29, series: 'KXRAININDM', julyHot: 93, julyRain: 4.4 },
    { id: 'msp', city: 'Minneapolis', lat: 44.88, lon: -93.22, series: 'KXRAINMINM', julyHot: 94, julyRain: 4.0 },
    { id: 'mke', city: 'Milwaukee', lat: 42.95, lon: -87.90, series: 'KXRAINMKEM', julyHot: 92, julyRain: 3.7 },
    { id: 'msn', city: 'Madison', lat: 43.14, lon: -89.34, series: 'KXMSNLOWT', julyHot: 92, julyRain: 4.3 },
    { id: 'dtw', city: 'Detroit', lat: 42.21, lon: -83.35, series: 'KXRAINDTWM', julyHot: 93, julyRain: 3.4 },
    { id: 'sgf', city: 'Springfield, Missouri', label: 'Springfield', lat: 37.24, lon: -93.39, series: 'KXRAINSGFM', julyHot: 96, julyRain: 3.6 },
    { id: 'okc', city: 'Oklahoma City', lat: 35.39, lon: -97.60, series: 'KXRAINOKCM', julyHot: 102, julyRain: 2.9 },
    { id: 'den', city: 'Denver', lat: 39.85, lon: -104.66, series: 'KXRAINDENM', julyHot: 98, julyRain: 2.1 },
    { id: 'gtf', city: 'Great Falls, Montana', label: 'Great Falls', lat: 47.48, lon: -111.37, series: 'KXRAINGTF', julyHot: 97, julyRain: 1.4 },
    { id: 'lex', city: 'Lexington, Kentucky', label: 'Lexington', lat: 38.04, lon: -84.61, series: 'KXRAINLEXM', julyHot: 93, julyRain: 4.7 },
    { id: 'pit', city: 'Pittsburgh', lat: 40.49, lon: -80.23, series: 'KXRAINPITM', julyHot: 91, julyRain: 4.2 },
    // Texas and the South
    { id: 'dfw', city: 'Dallas', lat: 32.90, lon: -97.04, series: 'KXHIGHTDAL', julyHot: 103, julyRain: 2.2 },
    { id: 'aus', city: 'Austin', lat: 30.19, lon: -97.67, series: 'KXRAINAUSM', julyHot: 102, julyRain: 2.0 },
    { id: 'sat', city: 'San Antonio', lat: 29.53, lon: -98.47, series: 'KXRAINSATXM', julyHot: 101, julyRain: 2.4 },
    { id: 'cll', city: 'College Station', lat: 30.59, lon: -96.36, series: 'KXRAINCLLM', julyHot: 101, julyRain: 2.3 },
    { id: 'hou', city: 'Houston', lat: 29.98, lon: -95.36, series: 'KXRAINHOUM', julyHot: 98, julyRain: 3.8 },
    { id: 'msy', city: 'New Orleans', lat: 29.99, lon: -90.25, series: 'KXRAINNOLAM', julyHot: 95, julyRain: 6.0 },
    { id: 'atl', city: 'Atlanta', lat: 33.64, lon: -84.43, series: 'KXHIGHTATL', julyHot: 96, julyRain: 4.7 },
    { id: 'tpa', city: 'Tampa', lat: 27.97, lon: -82.53, series: 'KXRAINTPAM', julyHot: 94, julyRain: 7.6 },
    { id: 'mco', city: 'Orlando', lat: 28.43, lon: -81.31, series: 'KXRAINORL', julyHot: 96, julyRain: 7.3 },
    { id: 'pbi', city: 'West Palm Beach', lat: 26.68, lon: -80.10, series: 'KXRAINWPBM', julyHot: 94, julyRain: 6.0 },
    { id: 'mia', city: 'Miami', lat: 25.79, lon: -80.29, series: 'KXRAINMIAM', julyHot: 94, julyRain: 7.0 },
    // East
    { id: 'dca', city: 'Washington, DC', label: 'Washington', lat: 38.85, lon: -77.04, series: 'KXRAINDCM', julyHot: 97, julyRain: 4.3 },
    { id: 'phl', city: 'Philadelphia', lat: 39.87, lon: -75.24, series: 'KXRAINPHILM', julyHot: 96, julyRain: 4.4 },
    { id: 'ttn', city: 'Trenton', lat: 40.28, lon: -74.81, series: 'KXRAINTTNM', julyHot: 96, julyRain: 4.9 },
    { id: 'ewr', city: 'Newark', lat: 40.69, lon: -74.17, series: 'KXRAINEWRM', julyHot: 97, julyRain: 4.7 },
    { id: 'nyc', city: 'New York', lat: 40.78, lon: -73.97, series: 'KXRAINNYCM', julyHot: 95, julyRain: 4.6 },
    { id: 'pvd', city: 'Providence', lat: 41.72, lon: -71.43, series: 'KXRAINPVDM', julyHot: 94, julyRain: 3.3 },
    { id: 'bos', city: 'Boston', lat: 42.36, lon: -71.01, series: 'KXRAINBOSM', julyHot: 95, julyRain: 3.3 },
    // West
    { id: 'sea', city: 'Seattle', lat: 47.45, lon: -122.31, series: 'KXRAINSEAM', julyHot: 90, julyRain: 0.7 },
    { id: 'apc', city: 'Napa', lat: 38.21, lon: -122.28, series: 'KXRAINNAPAM', julyHot: 100, julyRain: 0.05 },
    { id: 'sfo', city: 'San Francisco', lat: 37.62, lon: -122.38, series: 'KXHIGHTSFO', julyHot: 82, julyRain: 0.05 },
    { id: 'sjc', city: 'San Jose', lat: 37.36, lon: -121.93, series: 'KXSJCLOWT', julyHot: 97, julyRain: 0.05 },
    { id: 'lax', city: 'Los Angeles', lat: 33.94, lon: -118.41, series: 'KXRAINLAXM', julyHot: 86, julyRain: 0.1 },
    { id: 'san', city: 'San Diego', lat: 32.73, lon: -117.19, series: 'KXHIGHTSAN', julyHot: 82, julyRain: 0.1 },
    { id: 'las', city: 'Las Vegas', lat: 36.08, lon: -115.15, series: 'KXRAINLVM', julyHot: 113, julyRain: 0.4 },
    { id: 'phx', city: 'Phoenix', lat: 33.43, lon: -112.01, series: 'KXHIGHTPHX', julyHot: 115, julyRain: 0.9 }
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
