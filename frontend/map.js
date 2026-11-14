/* The farm map: lower 48 states, the Kalshi weather stations, and the farm pin.
 *
 * createMap(svg, { onPick }) returns { setFarm(farm, animate), project, unproject }.
 *   onPick({ lat, lon, state })  fires when the farmer clicks on land.
 *   farm = { lat, lon, label, station: { city, lat, lon } } or null.
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

  function createMap(svg, opts) {
    const box = B.usMap.viewBox;
    svg.setAttribute('viewBox', box.join(' '));

    const land = el('g', { class: 'land' }, svg);
    B.usMap.states.forEach(function (s) {
      el('path', { class: 'state', d: s[2], 'data-code': s[0] }, land);
    });

    const dots = el('g', { class: 'stations' }, svg);
    const stationDots = B.stations.map(function (s) {
      const p = project(s.lat, s.lon);
      return { station: s, node: el('circle', { class: 'station', cx: p[0].toFixed(1), cy: p[1].toFixed(1) }, dots) };
    });

    const link = el('line', { class: 'link', visibility: 'hidden' }, svg);
    const labelAnchor = el('g', { class: 'station-label', visibility: 'hidden' }, svg);
    const label = el('text', null, labelAnchor);
    const pinAnchor = el('g', { class: 'pin-anchor', visibility: 'hidden' }, svg);
    const ring = el('circle', { class: 'pin-ring', r: 7 }, pinAnchor);
    const pin = el('g', { class: 'pin' }, pinAnchor);
    el('path', { class: 'pin-body', d: 'M0 0C-6.5-9.5-11-14.5-11-21a11 11 0 1 1 22 0c0 6.5-4.5 11.5-11 21z' }, pin);
    el('circle', { class: 'pin-eye', cx: 0, cy: -21, r: 4 }, pin);

    let farm = null;
    let running = [];

    /* Markers keep the same size on screen whatever width the map is drawn at. */
    function unit() {
      const w = svg.getBoundingClientRect().width || box[2];
      return box[2] / w;
    }

    function place() {
      const k = unit();
      stationDots.forEach(function (d) { d.node.setAttribute('r', (3.4 * k).toFixed(2)); });
      if (!farm) return;
      const f = project(farm.lat, farm.lon);
      const s = project(farm.station.lat, farm.station.lon);
      pinAnchor.setAttribute('transform', 'translate(' + f[0].toFixed(1) + ' ' + f[1].toFixed(1) + ') scale(' + k.toFixed(3) + ')');
      link.setAttribute('x1', f[0].toFixed(1));
      link.setAttribute('y1', f[1].toFixed(1));
      link.setAttribute('x2', s[0].toFixed(1));
      link.setAttribute('y2', s[1].toFixed(1));
      // The label sits on the far side of the station from the farm.
      const east = s[0] >= f[0];
      labelAnchor.setAttribute('transform', 'translate(' + s[0].toFixed(1) + ' ' + s[1].toFixed(1) + ') scale(' + k.toFixed(3) + ')');
      label.setAttribute('x', east ? 9 : -9);
      label.setAttribute('y', 4);
      label.setAttribute('text-anchor', east ? 'start' : 'end');
      stationDots.forEach(function (d) { d.node.classList.toggle('is-nearest', d.station === farm.station); });
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
      labelAnchor.setAttribute('visibility', shown);
      if (!farm) {
        stationDots.forEach(function (d) { d.node.classList.remove('is-nearest'); });
        svg.setAttribute('aria-label', 'Map of the lower 48 states. Dots mark weather stations with Kalshi markets. No farm pin yet.');
        return;
      }
      label.textContent = farm.station.city;
      place();
      svg.setAttribute('aria-label', 'Map of the lower 48 states with a farm pin ' + farm.label + '. The nearest weather station is ' + farm.station.city + '.');
      if (!animate) return;

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
      ], { duration: 460, delay: 200, fill: 'both' });
      const length = Math.hypot(link.x2.baseVal.value - link.x1.baseVal.value, link.y2.baseVal.value - link.y1.baseVal.value);
      link.style.strokeDasharray = length;
      play(link, [{ strokeDashoffset: length }, { strokeDashoffset: 0 }], { duration: 280, delay: 240 });
      play(labelAnchor, [{ opacity: 0 }, { opacity: 1 }], { duration: 160, delay: 420, easing: 'ease' });
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
    place();

    return { setFarm: setFarm, project: project, unproject: unproject };
  }

  B.createMap = createMap;
})(window.FarmerJoe = window.FarmerJoe || {});
