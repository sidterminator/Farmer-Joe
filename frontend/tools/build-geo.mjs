// Rebuilds us-map.js and places.js. Not needed to run the app.
//
//   node tools/build-geo.mjs <states-albers-10m.json> <cities15000.txt>
//
// Sources:
//   https://cdn.jsdelivr.net/npm/us-atlas@3/states-albers-10m.json   (ISC licence; U.S. Census Bureau shapes)
//   https://download.geonames.org/export/dump/cities15000.zip          (GeoNames, CC BY 4.0)
//
// The map file is already projected (Albers USA, 975 x 610). map.js carries
// the matching projection for the lower 48 states, checked here against the
// state outlines.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const [topoPath, citiesPath] = process.argv.slice(2);
const out = join(dirname(fileURLToPath(import.meta.url)), '..');
const NS = 'window.FarmerJoe = window.FarmerJoe || {}';

const POSTAL = { Alabama: 'AL', Arizona: 'AZ', Arkansas: 'AR', California: 'CA', Colorado: 'CO', Connecticut: 'CT', Delaware: 'DE', 'District of Columbia': 'DC', Florida: 'FL', Georgia: 'GA', Idaho: 'ID', Illinois: 'IL', Indiana: 'IN', Iowa: 'IA', Kansas: 'KS', Kentucky: 'KY', Louisiana: 'LA', Maine: 'ME', Maryland: 'MD', Massachusetts: 'MA', Michigan: 'MI', Minnesota: 'MN', Mississippi: 'MS', Missouri: 'MO', Montana: 'MT', Nebraska: 'NE', Nevada: 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', Ohio: 'OH', Oklahoma: 'OK', Oregon: 'OR', Pennsylvania: 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', Tennessee: 'TN', Texas: 'TX', Utah: 'UT', Vermont: 'VT', Virginia: 'VA', Washington: 'WA', 'West Virginia': 'WV', Wisconsin: 'WI', Wyoming: 'WY' };

// ---- map ----
const topo = JSON.parse(readFileSync(topoPath, 'utf8'));
const { scale, translate } = topo.transform;
const arcs = topo.arcs.map((arc) => {
  let x = 0, y = 0;
  return arc.map(([dx, dy]) => { x += dx; y += dy; return [x * scale[0] + translate[0], y * scale[1] + translate[1]]; });
});

function simplify(points, tolerance) {
  if (points.length < 3) return points;
  const keep = new Uint8Array(points.length);
  keep[0] = keep[points.length - 1] = 1;
  const stack = [[0, points.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    const [ax, ay] = points[a], [bx, by] = points[b];
    const len = Math.hypot(bx - ax, by - ay) || 1e-9;
    let worst = 0, at = -1;
    for (let i = a + 1; i < b; i++) {
      const d = Math.abs((bx - ax) * (ay - points[i][1]) - (ax - points[i][0]) * (by - ay)) / len;
      if (d > worst) { worst = d; at = i; }
    }
    if (worst > tolerance) { keep[at] = 1; stack.push([a, at], [at, b]); }
  }
  return points.filter((_, i) => keep[i]);
}
const slim = arcs.map((a) => simplify(a, 0.3));

function ring(indices) {
  const pts = [];
  for (const i of indices) {
    const a = i >= 0 ? slim[i] : slim[~i].slice().reverse();
    for (let k = pts.length ? 1 : 0; k < a.length; k++) pts.push(a[k]);
  }
  return pts;
}
const states = [];
let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
for (const g of topo.objects.states.geometries) {
  const code = POSTAL[g.properties.name];
  if (!code) continue; // Alaska, Hawaii and territories are outside the lower-48 projection
  const polys = g.type === 'Polygon' ? [g.arcs] : g.arcs;
  const rings = polys.flatMap((p) => p.map(ring));
  for (const r of rings) for (const [x, y] of r) { minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y); }
  const d = rings.map((r) => 'M' + r.map(([x, y]) => x.toFixed(1) + ' ' + y.toFixed(1)).join('L') + 'Z').join('');
  states.push({ code, name: g.properties.name, d, rings });
}
states.sort((a, b) => a.code.localeCompare(b.code));
const pad = 8;
const box = [Math.floor(minX - pad), Math.floor(minY - pad), Math.ceil(maxX - minX + pad * 2), Math.ceil(maxY - minY + pad * 2)];

// ---- projection check (same maths as map.js) ----
const RAD = Math.PI / 180;
const n = (Math.sin(29.5 * RAD) + Math.sin(45.5 * RAD)) / 2;
const c = 1 + Math.sin(29.5 * RAD) * (2 * n - Math.sin(29.5 * RAD));
const r0 = Math.sqrt(c) / n;
const raw = (lam, phi) => { const r = Math.sqrt(c - 2 * n * Math.sin(phi)) / n; return [r * Math.sin(n * lam), r0 - r * Math.cos(n * lam)]; };
const centre = raw(-0.6 * RAD, 38.7 * RAD);
const project = (lat, lon) => { const p = raw((lon + 96) * RAD, lat * RAD); return [487.5 + 1300 * (p[0] - centre[0]), 305 - 1300 * (p[1] - centre[1])]; };
const inside = (pt, r) => { let hit = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) hit = !hit; } return hit; };
const stateAt = (lat, lon) => { const p = project(lat, lon); const s = states.find((st) => st.rings.some((r) => inside(p, r))); return s ? s.code : null; };
const checks = [['Champaign', 40.12, -88.24, 'IL'], ['Chicago', 41.85, -87.65, 'IL'], ['Denver', 39.74, -104.98, 'CO'], ['Miami', 25.77, -80.19, 'FL'], ['Seattle', 47.61, -122.33, 'WA'], ['Bangor', 44.80, -68.77, 'ME'], ['El Paso', 31.76, -106.49, 'TX'], ['Fargo', 46.88, -96.79, 'ND'], ['Des Moines', 41.59, -93.62, 'IA']];
for (const [name, lat, lon, want] of checks) {
  const got = stateAt(lat, lon);
  if (got !== want) throw new Error(`projection check failed: ${name} landed in ${got}, expected ${want}`);
}

writeFileSync(join(out, 'us-map.js'),
  '/* Generated by tools/build-geo.mjs. State outlines from us-atlas (ISC licence), already in Albers USA\n * projection. Lower 48 states and DC only. */\n' +
  `(function (B) {\n  B.usMap = {\n    viewBox: ${JSON.stringify(box)},\n    states: ${JSON.stringify(states.map((s) => [s.code, s.name, s.d]))}\n  };\n})(${NS});\n`);

// ---- places ----
const seen = new Set();
const places = [];
let misplaced = 0;
for (const line of readFileSync(citiesPath, 'utf8').split('\n')) {
  const f = line.split('\t');
  if (f[8] !== 'US') continue;
  const code = f[10];
  if (!Object.values(POSTAL).includes(code)) continue;
  const name = f[1];
  const key = name + '|' + code;
  if (seen.has(key) || /[|;]/.test(name)) continue;
  seen.add(key);
  const lat = +f[4], lon = +f[5];
  if (stateAt(lat, lon) !== code) misplaced++;
  places.push([name, code, lat.toFixed(2), lon.toFixed(2), +f[14]]);
}
places.sort((a, b) => b[4] - a[4]);
writeFileSync(join(out, 'places.js'),
  '/* Generated by tools/build-geo.mjs. U.S. towns and cities of 15,000 people or more, largest first, from\n * GeoNames (geonames.org, CC BY 4.0). Format: name|state|lat|lon;... */\n' +
  `(function (B) {\n  B.placesRaw = ${JSON.stringify(places.map((p) => p.slice(0, 4).join('|')).join(';'))};\n})(${NS});\n`);

console.log(`states ${states.length}, viewBox ${box.join(' ')}, places ${places.length}, places outside their state outline ${misplaced} (coastal towns on a simplified outline)`);
