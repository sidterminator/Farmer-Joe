/* The one chart form: two distributions, one above the other, on a shared
 * ruled grid. The top band is the season without protection and the bottom
 * band is the season with the farmer's plan, so a tighter spread reads as a
 * narrower, taller shape directly under the wider one.
 *
 * createPlot(figure) returns { render(spec), refresh() }.
 *
 * spec = {
 *   ariaLabel: string,
 *   lo, hi: number,                       // shared x range
 *   headroom: number,                     // y-axis top as a multiple of the first band's peak
 *   bands: [{ key, label, values(bins, lo, hi) -> Float64Array, mark: { value, label } | null }],
 *   xTicks(lo, hi) -> [{ value, label }],
 *   tip(bin, shares, lo, hi) -> { title, rows: [{ key, value, label }] }
 * }
 */
(function (B) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const MARGIN = { l: 44, r: 14, t: 6, b: 28 };
  const PITCH = 10;        // target distance between column centres, px
  const GAP = 2;           // surface gap between columns, px
  const RADIUS = 3;
  const BAND_HEAD = 22;    // room for the band's label
  const BAND_GAP = 14;

  function svgEl(name, attrs, parent) {
    const node = document.createElementNS(NS, name);
    if (attrs) for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }

  function niceStep(max, maxTicks) {
    const steps = [0.0025, 0.005, 0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5];
    for (let i = 0; i < steps.length; i++) if (max / steps[i] <= maxTicks) return steps[i];
    return 1;
  }

  function createPlot(figure) {
    const svg = figure.querySelector('svg');
    const tip = figure.querySelector('.tip');
    const clipId = 'clip-' + Math.random().toString(36).slice(2, 8);

    const defs = svgEl('defs', null, svg);
    const clip = svgEl('clipPath', { id: clipId }, defs);
    const gGrid = svgEl('g', { class: 'grid' }, svg);
    const gCols = svgEl('g', { class: 'cols', 'clip-path': 'url(#' + clipId + ')' }, svg);
    const gAxis = svgEl('g', { class: 'axis' }, svg);
    const gMarks = svgEl('g', { class: 'marks' }, svg);
    const cross = svgEl('line', { class: 'cross', visibility: 'hidden' }, svg);

    let spec = null;
    let geom = null;
    let shares = [];
    let yMax = 1;
    let nodes = [];
    let hover = -1;

    function measure() {
      const W = Math.max(260, figure.clientWidth);
      const H = Math.max(220, figure.clientHeight);
      const innerW = W - MARGIN.l - MARGIN.r;
      const bandH = (H - MARGIN.t - MARGIN.b - BAND_GAP) / 2;
      const bins = Math.max(16, Math.round(innerW / PITCH));
      return { W: W, H: H, innerW: innerW, bandH: bandH, bins: bins, pitch: innerW / bins };
    }

    function bandTop(b) { return MARGIN.t + b * (geom.bandH + BAND_GAP); }
    function bandBase(b) { return bandTop(b) + geom.bandH; }
    function xOfBin(k) { return MARGIN.l + (k + 0.5) * geom.pitch; }
    function xOfValue(v) { return MARGIN.l + ((v - spec.lo) / (spec.hi - spec.lo)) * geom.innerW; }
    function heightOf(share) { return (share / yMax) * (geom.bandH - BAND_HEAD); }

    function load() {
      shares = spec.bands.map(function (band) { return band.values(geom.bins, spec.lo, spec.hi); });
      // The scale is set by the first band with headroom above it, so that
      // band holds still while the second one grows or shrinks beneath it.
      const peaks = shares.map(function (s) { let p = 0; for (let k = 0; k < s.length; k++) p = Math.max(p, s[k]); return p; });
      yMax = Math.max(peaks[0] * (spec.headroom || 1.06), Math.max.apply(null, peaks) * 1.06, 1e-6);
    }

    function drawGrid() {
      gGrid.textContent = '';
      gAxis.textContent = '';
      const right = MARGIN.l + geom.innerW;
      const step = niceStep(yMax, 2.2);
      const pct = +(step * 100).toFixed(6);
      const decimals = Number.isInteger(pct) ? 0 : Number.isInteger(+(pct * 10).toFixed(6)) ? 1 : 2;

      // Vertical rules run through both bands: one grid for both pictures.
      const ticks = spec.xTicks(spec.lo, spec.hi);
      let lastRight = -Infinity;
      ticks.forEach(function (t) {
        const x = Math.round(xOfValue(t.value)) + 0.5;
        if (x < MARGIN.l + 8 || x > right - 8) return;
        const text = svgEl('text', { x: x, y: geom.H - 8, 'text-anchor': 'middle' }, gAxis);
        text.textContent = t.label;
        const half = text.getComputedTextLength() / 2;
        if (x - half < lastRight + 14) { gAxis.removeChild(text); return; }
        lastRight = x + half;
        svgEl('line', { class: 'rule-v', x1: x, x2: x, y1: bandTop(0) + BAND_HEAD, y2: bandBase(1) }, gGrid);
      });

      spec.bands.forEach(function (band, b) {
        const base = Math.round(bandBase(b)) + 0.5;
        for (let v = step; v <= yMax * 1.0001; v += step) {
          const y = Math.round(bandBase(b) - heightOf(v)) + 0.5;
          svgEl('line', { class: 'rule-h', x1: MARGIN.l, x2: right, y1: y, y2: y }, gGrid);
          const t = svgEl('text', { x: MARGIN.l - 8, y: y + 4, 'text-anchor': 'end' }, gAxis);
          t.textContent = (v * 100).toFixed(decimals) + '%';
        }
        svgEl('line', { class: 'baseline', x1: MARGIN.l, x2: right, y1: base, y2: base }, gGrid);
        svgEl('rect', { class: 'key key-' + band.key, x: MARGIN.l, y: bandTop(b) + 4, width: 10, height: 10, rx: 2 }, gAxis);
        const label = svgEl('text', { class: 'band-label', x: MARGIN.l + 16, y: bandTop(b) + 13 }, gAxis);
        label.textContent = band.label;
      });
    }

    function drawColumns(rebuild) {
      if (rebuild) {
        gCols.textContent = '';
        clip.textContent = '';
        nodes = spec.bands.map(function (band, b) {
          svgEl('rect', { x: MARGIN.l, y: bandTop(b), width: geom.innerW, height: geom.bandH }, clip);
          const g = svgEl('g', { class: 'band band-' + band.key }, gCols);
          const list = [];
          for (let k = 0; k < geom.bins; k++) list.push(svgEl('rect', { rx: RADIUS, y: bandBase(b), height: 0 }, g));
          return list;
        });
      }
      const w = Math.max(2, geom.pitch - GAP);
      spec.bands.forEach(function (band, b) {
        const base = bandBase(b);
        for (let k = 0; k < geom.bins; k++) {
          const share = shares[b][k];
          const h = share > 0 ? Math.max(1, heightOf(share)) : 0;
          const node = nodes[b][k];
          node.setAttribute('x', (MARGIN.l + k * geom.pitch + GAP / 2).toFixed(2));
          node.setAttribute('width', w.toFixed(2));
          // Each column runs past its baseline and is clipped there, so only
          // the data end is rounded.
          node.setAttribute('y', (base - h).toFixed(2));
          node.setAttribute('height', (h + RADIUS * 2).toFixed(2));
          node.setAttribute('class', 'col' + (k === hover ? ' is-hover' : ''));
        }
      });
    }

    function drawMarks() {
      gMarks.textContent = '';
      // On a narrow plot the label would sit on the columns; the table under
      // the chart carries the figure instead.
      if (geom.innerW < 420) return;
      const right = MARGIN.l + geom.innerW;
      spec.bands.forEach(function (band, b) {
        if (!band.mark) return;
        const x = Math.min(right - 2, Math.max(MARGIN.l + 2, xOfValue(band.mark.value)));
        const base = bandBase(b);
        const top = base - Math.min(geom.bandH - BAND_HEAD - 4, 46);
        svgEl('line', { class: 'mark-line', x1: x, x2: x, y1: top, y2: base }, gMarks);
        const text = svgEl('text', { class: 'mark-label', x: x - 7, y: top + 10, 'text-anchor': 'end' }, gMarks);
        text.textContent = band.mark.label;
        // Flip to the right of the line when there is no room on the left.
        if (x - 7 - text.getComputedTextLength() < MARGIN.l + 2) {
          text.setAttribute('x', x + 7);
          text.setAttribute('text-anchor', 'start');
        }
      });
    }

    function showTip(k) {
      if (k === hover && !tip.hidden) return;
      if (hover >= 0) nodes.forEach(function (list) { if (list[hover]) list[hover].classList.remove('is-hover'); });
      hover = k;
      if (k < 0 || !spec) {
        tip.hidden = true;
        cross.setAttribute('visibility', 'hidden');
        return;
      }
      nodes.forEach(function (list) { list[k].classList.add('is-hover'); });
      const x = Math.round(xOfBin(k)) + 0.5;
      cross.setAttribute('x1', x);
      cross.setAttribute('x2', x);
      cross.setAttribute('y1', bandTop(0) + BAND_HEAD);
      cross.setAttribute('y2', bandBase(1));
      cross.setAttribute('visibility', 'visible');
      fillTip(k);
      tip.hidden = false;
      const tw = tip.offsetWidth;
      const left = x + 14 + tw > geom.W - 6 ? x - 14 - tw : x + 14;
      tip.style.left = Math.max(6, left) + 'px';
      tip.style.top = bandTop(0) + BAND_HEAD + 'px';
    }

    function fillTip(k) {
      const content = spec.tip(k, shares, spec.lo, spec.hi);
      tip.textContent = '';
      const title = document.createElement('p');
      title.className = 'tip-title';
      title.textContent = content.title;
      tip.appendChild(title);
      content.rows.forEach(function (r) {
        const row = document.createElement('p');
        row.className = 'tip-row';
        const key = document.createElement('span');
        key.className = 'tip-key tip-key-' + r.key;
        const value = document.createElement('strong');
        value.textContent = r.value;
        const label = document.createElement('span');
        label.textContent = r.label;
        row.appendChild(key);
        row.appendChild(value);
        row.appendChild(label);
        tip.appendChild(row);
      });
    }

    function binFromEvent(e) {
      const rect = svg.getBoundingClientRect();
      const x = e.clientX - rect.left - MARGIN.l;
      if (x < 0 || x > geom.innerW) return -1;
      return Math.min(geom.bins - 1, Math.floor(x / geom.pitch));
    }

    function render(next) {
      if (next) spec = next;
      if (!spec) return;
      const g = measure();
      const rebuild = !geom || g.bins !== geom.bins || g.H !== geom.H || g.W !== geom.W || nodes.length !== spec.bands.length;
      geom = g;
      svg.setAttribute('viewBox', '0 0 ' + geom.W + ' ' + geom.H);
      svg.setAttribute('width', geom.W);
      svg.setAttribute('height', geom.H);
      figure.setAttribute('aria-label', spec.ariaLabel);
      hover = -1;
      tip.hidden = true;
      cross.setAttribute('visibility', 'hidden');
      load();
      drawGrid();
      drawColumns(rebuild);
      drawMarks();
    }

    /* Fast path while a quantity slider is dragged: same frame, new heights. */
    function refresh() {
      if (!spec || !geom) return;
      load();
      drawGrid();   // band labels can change with the selection
      drawColumns(false);
      drawMarks();
      if (hover >= 0 && !tip.hidden) fillTip(hover);
    }

    svg.addEventListener('pointermove', function (e) { if (geom) showTip(binFromEvent(e)); });
    svg.addEventListener('pointerleave', function () { showTip(-1); });
    figure.addEventListener('keydown', function (e) {
      if (!geom) return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        const start = hover < 0 ? Math.floor(geom.bins / 2) : hover;
        showTip(Math.min(geom.bins - 1, Math.max(0, start + (e.key === 'ArrowRight' ? 1 : -1))));
      } else if (e.key === 'Escape') {
        showTip(-1);
      }
    });
    figure.addEventListener('blur', function () { showTip(-1); });

    if ('ResizeObserver' in window) {
      let pending = 0;
      new ResizeObserver(function () {
        cancelAnimationFrame(pending);
        pending = requestAnimationFrame(function () { if (figure.clientWidth) render(); });
      }).observe(figure);
    } else {
      window.addEventListener('resize', function () { render(); });
    }

    return { render: render, refresh: refresh };
  }

  B.createPlot = createPlot;
})(window.FarmerJoe = window.FarmerJoe || {});
