/* The farm map: lower 48 states, every city with a Kalshi weather station
 * (named), and the farm pin.
 *
 * createMap(svg, { onPick }) returns { setFarm(farm, animate), project, unproject }.
 *   onPick({ lat, lon, state })  fires when the farmer clicks on land.
 *   farm = { lat, lon, label, station } or null, where station is one of
 *   FarmerJoe.stations.
 *
 * us-map.js is already drawn in Albers USA at 975 x 610. The projection below
 * is the same one (lower 48 only), so a latitude and longitude land on the
 * right spot of that drawing, and a click can be turned back into one.
 */
(function (B) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const RAD = Math.PI / 180;
  const EASE_OUT = 'cubic-bezier(0.23, 1, 0.32, 1)';

  const n = (Math.sin(29.5 * RAD) + Math.sin(45.5 * RAD)) / 2;
  const c = 1 + Math.sin(29.5 * RAD) * (2 * n - Math.sin(29.5 * RAD));
  const r0 = Math.sqrt(c) / n;
  function raw(lam, phi) {
    const r = Math.sqrt(c - 2 * n * Math.sin(phi)) / n;
    return [r * Math.sin(n * lam), r0 - r * Math.cos(n * lam)];
  }
  const centre = raw(-0.6 * RAD, 38.7 * RAD);

  function project(lat, lon) {
    const p = raw((lon + 96) * RAD, lat * RAD);
    return [487.5 + 1300 * (p[0] - centre[0]), 305 - 1300 * (p[1] - centre[1])];
  }

  function unproject(x, y) {
    const X = (x - 487.5) / 1300 + centre[0];
    const Y = centre[1] - (y - 305) / 1300;
    const r0y = r0 - Y;
    const r = Math.sqrt(X * X + r0y * r0y);
    return {
      lat: Math.asin((c - r * r * n * n) / (2 * n)) / RAD,
      lon: Math.atan2(X, r0y) / n / RAD - 96
    };
  }

  function el(name, attrs, parent) {
    const node = document.createElementNS(NS, name);
    if (attrs) for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }

  function reducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function overlap(a, b) {
    return a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
  }

  function createMap(svg, opts) {
    const box = B.usMap.viewBox;
    svg.setAttribute('viewBox', box.join(' '));

    const land = el('g', { class: 'land' }, svg);
    B.usMap.states.forEach(function (s) {
      el('path', { class: 'state', d: s[2], 'data-code': s[0] }, land);
    });

    const link = el('line', { class: 'station-link', visibility: 'hidden' }, svg);
    const dots = el('g', { class: 'stations' }, svg);
    const names = el('g', { class: 'city-labels' }, svg);
    const cities = B.stations.map(function (s) {
      const p = project(s.lat, s.lon);
      const g = el('g', { class: 'city-label' }, names);
      const text = el('text', null, g);
      text.textContent = s.label || s.city;
      return { station: s, p: p, dot: el('circle', { class: 'station', cx: p[0].toFixed(1), cy: p[1].toFixed(1) }, dots), g: g, text: text };
    });

    const pinAnchor = el('g', { class: 'pin-anchor', visibility: 'hidden' }, svg);
    const ring = el('circle', { class: 'pin-ring', r: 7 }, pinAnchor);
    const pin = el('g', { class: 'pin' }, pinAnchor);
    el('path', { class: 'pin-body', d: 'M0 0C-6.5-9.5-11-14.5-11-21a11 11 0 1 1 22 0c0 6.5-4.5 11.5-11 21z' }, pin);
    el('circle', { class: 'pin-eye', cx: 0, cy: -21, r: 4 }, pin);

    let farm = null;
    let running = [];

    /* Drawing units per screen pixel, so markers and names keep their size on
     * screen whatever size the map is drawn at. */
    function unit() {
      const ctm = svg.getScreenCTM();
      return ctm && ctm.a > 0 ? 1 / ctm.a : 1;
    }

    /* Name every city without letting names sit on each other, on a dot or on
     * the pin. Each name tries a ring of spots around its dot, the crowded
     * cities first, and is left off if none is free. On a very small map only
     * the nearest city is named; the list under the map always has them all. */
    function nameCities(k) {
      const small = svg.getBoundingClientRect().width < 420;
      const dotR = 5 * k;
      const taken = cities.map(function (cty) {
        return { owner: cty, x0: cty.p[0] - dotR, y0: cty.p[1] - dotR, x1: cty.p[0] + dotR, y1: cty.p[1] + dotR };
      });
      if (farm) {
        const f = project(farm.lat, farm.lon);
        taken.push({ owner: null, x0: f[0] - 13 * k, y0: f[1] - 35 * k, x1: f[0] + 13 * k, y1: f[1] + 3 * k });
      }
      const reach = 70 * k;
      const crowd = new Map(cities.map(function (a) {
        return [a, cities.filter(function (b) { return b !== a && Math.hypot(a.p[0] - b.p[0], a.p[1] - b.p[1]) < reach; }).length];
      }));
      const order = cities.slice().sort(function (a, b) {
        const near = (farm && b.station === farm.station ? 1 : 0) - (farm && a.station === farm.station ? 1 : 0);
        return near || crowd.get(b) - crowd.get(a);
      });
      order.forEach(function (cty) {
        const nearest = !!farm && cty.station === farm.station;
        cty.g.classList.toggle('is-nearest', nearest);
        cty.dot.classList.toggle('is-nearest', nearest);
        if (small && !nearest) { cty.g.setAttribute('visibility', 'hidden'); return; }
        const w = cty.text.getComputedTextLength() * k;
        const h = 12 * k;
        const x = cty.p[0];
        const y = cty.p[1];
        const spots = [
          ['start', x + 7 * k, y + 4 * k], ['end', x - 7 * k, y + 4 * k],
          ['middle', x, y - 8 * k], ['middle', x, y + 16 * k],
          ['start', x + 5 * k, y - 6 * k], ['start', x + 5 * k, y + 14 * k],
          ['end', x - 5 * k, y - 6 * k], ['end', x - 5 * k, y + 14 * k],
          ['start', x + 9 * k, y - 10 * k], ['start', x + 9 * k, y + 18 * k],
          ['end', x - 9 * k, y - 10 * k], ['end', x - 9 * k, y + 18 * k],
          ['middle', x, y - 20 * k], ['middle', x, y + 28 * k],
          ['start', x + 16 * k, y - 18 * k], ['start', x + 16 * k, y + 26 * k],
          ['end', x - 16 * k, y - 18 * k], ['end', x - 16 * k, y + 26 * k]
        ];
        let chosen = null;
        for (let i = 0; i < spots.length && !chosen; i++) {
          const s = spots[i];
          const left = s[0] === 'start' ? s[1] : s[0] === 'end' ? s[1] - w : s[1] - w / 2;
          const b = { owner: cty, x0: left - 2 * k, y0: s[2] - h, x1: left + w + 2 * k, y1: s[2] + 3 * k };
          if (b.x0 < box[0] || b.x1 > box[0] + box[2] || b.y0 < box[1] || b.y1 > box[1] + box[3]) continue;
          if (taken.some(function (t) { return t.owner !== cty && overlap(t, b); })) continue;
          chosen = { spot: s, box: b };
        }
        if (!chosen && nearest) chosen = { spot: spots[0], box: null };
        if (!chosen) { cty.g.setAttribute('visibility', 'hidden'); return; }
        if (chosen.box) taken.push(chosen.box);
        cty.g.setAttribute('visibility', 'visible');
        cty.g.setAttribute('transform', 'translate(' + chosen.spot[1].toFixed(1) + ' ' + chosen.spot[2].toFixed(1) + ') scale(' + k.toFixed(3) + ')');
        cty.text.setAttribute('text-anchor', chosen.spot[0]);
      });
    }

    function place() {
      const k = unit();
      cities.forEach(function (cty) { cty.dot.setAttribute('r', (3.4 * k).toFixed(2)); });
      if (farm) {
        const f = project(farm.lat, farm.lon);
        const s = project(farm.station.lat, farm.station.lon);
        pinAnchor.setAttribute('transform', 'translate(' + f[0].toFixed(1) + ' ' + f[1].toFixed(1) + ') scale(' + k.toFixed(3) + ')');
        link.setAttribute('x1', f[0].toFixed(1));
        link.setAttribute('y1', f[1].toFixed(1));
        link.setAttribute('x2', s[0].toFixed(1));
        link.setAttribute('y2', s[1].toFixed(1));
      }
      nameCities(k);
    }

    function stop() {
      running.forEach(function (a) { a.cancel(); });
      running = [];
    }

    function play(node, frames, timing) {
      if (!node.animate) return;
      running.push(node.animate(frames, Object.assign({ easing: EASE_OUT, fill: 'backwards' }, timing)));
    }

    function setFarm(next, animate) {
      stop();
      farm = next;
      const shown = farm ? 'visible' : 'hidden';
      pinAnchor.setAttribute('visibility', shown);
      link.setAttribute('visibility', shown);
      place();
      const count = B.stations.length;
      svg.setAttribute('aria-label', farm
        ? 'Map of the lower 48 states with a farm pin at ' + farm.label + '. The nearest of ' + count + ' Kalshi weather stations is ' + farm.station.city + '.'
        : 'Map of the lower 48 states showing ' + count + ' cities with Kalshi weather stations. No farm pin yet.');
      if (!farm || !animate) return;

      if (reducedMotion()) {
        play(pinAnchor, [{ opacity: 0 }, { opacity: 1 }], { duration: 150, easing: 'ease' });
        return;
      }
      // The pin drops, a ring marks where it landed, then the line runs out
      // to the nearest station.
      play(pin, [
        { transform: 'translateY(-52px)', opacity: 0 },
        { transform: 'translateY(0)', opacity: 1 }
      ], { duration: 260 });
      play(ring, [
        { transform: 'scale(0.5)', opacity: 0.75 },
        { transform: 'scale(3.4)', opacity: 0 }
      ], { duration: 280, delay: 200, fill: 'both' });
      const length = Math.hypot(link.x2.baseVal.value - link.x1.baseVal.value, link.y2.baseVal.value - link.y1.baseVal.value);
      link.style.strokeDasharray = length;
      play(link, [{ strokeDashoffset: length }, { strokeDashoffset: 0 }], { duration: 280, delay: 240 });
    }

    svg.addEventListener('click', function (e) {
      const state = e.target.closest ? e.target.closest('.state') : null;
      if (!state) return;
      const ctm = svg.getScreenCTM();
      if (!ctm) return;
      const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
      const where = unproject(pt.x, pt.y);
      opts.onPick({ lat: where.lat, lon: where.lon, state: state.getAttribute('data-code') });
    });

    if ('ResizeObserver' in window) new ResizeObserver(place).observe(svg);
    else window.addEventListener('resize', place);

    setFarm(null, false);

    return { setFarm: setFarm, project: project, unproject: unproject };
  }

  B.createMap = createMap;
})(window.FarmerJoe = window.FarmerJoe || {});
