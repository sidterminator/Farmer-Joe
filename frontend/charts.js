/* One chart form for the whole screen: a distribution drawn as fine vertical
 * ribs, with an optional dashed outline stitched over it.
 *
 * createPlot(figure) returns { render(spec), refreshLine() }.
 *
 * spec = {
 *   ariaLabel: string,
 *   domain(bins)            -> { lo, hi }
 *   ribs(bins, lo, hi)      -> { share: Float64Array, gold: Uint8Array | null }
 *   line(bins, lo, hi)      -> Float64Array | null       (the stitched outline)
 *   headroom: number,         // y-axis top as a multiple of the tallest rib
 *   xTicks(lo, hi)          -> [{ value, label }]
 *   yCaption: string,
 *   strike: { value, label } | null,
 *   labels(data, bins)      -> [{ series: 'rib'|'gold'|'line', bin, text, place: 'above'|'left'|'right' }]
 *   tip(bin, data, lo, hi)  -> { title, rows: [{ series, value, label }] }
 * }
 */
(function (B) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const MARGIN = { l: 46, r: 16, t: 30, b: 30 };
  const PITCH = 9;       // target distance between rib centres, px
  const GAP = 2;         // surface gap between ribs, px
  const RIB_RADIUS = 3;

  function svgEl(name, attrs, parent) {
    const node = document.createElementNS(NS, name);
    if (attrs) for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }

  function niceStep(max, maxTicks) {
    const steps = [0.0025, 0.005, 0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5];
    for (let i = 0; i < steps.length; i++) {
      if (max / steps[i] <= maxTicks) return steps[i];
    }
    return 1;
  }

  function createPlot(figure) {
    const svg = figure.querySelector('svg');
    const tip = figure.querySelector('.tip');
    const clipId = 'clip-' + Math.random().toString(36).slice(2, 8);

    const defs = svgEl('defs', null, svg);
    const clipRect = svgEl('rect', null, svgEl('clipPath', { id: clipId }, defs));
    const gGrid = svgEl('g', { class: 'grid' }, svg);
    const gRibs = svgEl('g', { class: 'ribs', 'clip-path': 'url(#' + clipId + ')' }, svg);
    const baseline = svgEl('line', { class: 'baseline' }, svg);
    const gStrike = svgEl('g', { class: 'strike' }, svg);
    const cross = svgEl('line', { class: 'cross' }, svg);
    const lineUnder = svgEl('path', { class: 'stitch-under' }, svg);
    const linePath = svgEl('path', { class: 'stitch' }, svg);
    const gAxis = svgEl('g', { class: 'axis' }, svg);
    const gLabels = svgEl('g', { class: 'dlabels' }, svg);

    let spec = null;
    let geom = null;
    let data = null;
    let ribNodes = [];
    let hover = -1;

    function measure() {
      const W = Math.max(240, figure.clientWidth);
      const H = Math.max(180, figure.clientHeight);
      const innerW = W - MARGIN.l - MARGIN.r;
      const innerH = H - MARGIN.t - MARGIN.b;
      const bins = Math.max(18, Math.round(innerW / PITCH));
      return { W: W, H: H, innerW: innerW, innerH: innerH, bins: bins, pitch: innerW / bins };
    }

    function xOfBin(k) { return MARGIN.l + (k + 0.5) * geom.pitch; }
    function xOfValue(v) { return MARGIN.l + ((v - data.lo) / (data.hi - data.lo)) * geom.innerW; }
    function yOfShare(s) { return MARGIN.t + geom.innerH - (s / data.yMax) * geom.innerH; }

    function computeYMax() {
      let ribMax = 0;
      let lineMax = 0;
      for (let k = 0; k < data.share.length; k++) ribMax = Math.max(ribMax, data.share[k]);
      if (data.line) for (let k = 0; k < data.line.length; k++) lineMax = Math.max(lineMax, data.line[k]);
      return Math.max(ribMax * spec.headroom, lineMax * 1.14, 1e-6);
    }

    function drawGrid() {
      gGrid.textContent = '';
      gAxis.textContent = '';
      const base = MARGIN.t + geom.innerH;
      const right = MARGIN.l + geom.innerW;

      const step = niceStep(data.yMax, 4);
      const decimals = step * 100 < 1 ? (step * 1000 % 5 === 0 && step * 100 % 1 !== 0 ? 2 : 1) : 0;
      for (let v = step; v <= data.yMax * 1.0001; v += step) {
        const y = Math.round(yOfShare(v)) + 0.5;
        svgEl('line', { x1: MARGIN.l, x2: right, y1: y, y2: y }, gGrid);
        const t = svgEl('text', { x: MARGIN.l - 8, y: y + 4, 'text-anchor': 'end' }, gAxis);
        t.textContent = (v * 100).toFixed(decimals) + '%';
      }
      const cap = svgEl('text', { x: MARGIN.l, y: 16, class: 'caption' }, gAxis);
      cap.textContent = spec.yCaption;

      baseline.setAttribute('x1', MARGIN.l);
      baseline.setAttribute('x2', right);
      baseline.setAttribute('y1', base + 0.5);
      baseline.setAttribute('y2', base + 0.5);

      const ticks = spec.xTicks(data.lo, data.hi);
      let lastRight = -Infinity;
      for (let i = 0; i < ticks.length; i++) {
        const x = xOfValue(ticks[i].value);
        if (x < MARGIN.l + 12 || x > right - 12) continue;
        const t = svgEl('text', { x: x, y: base + 20, 'text-anchor': 'middle' }, gAxis);
        t.textContent = ticks[i].label;
        const half = t.getComputedTextLength() / 2;
        if (x - half < lastRight + 14) { gAxis.removeChild(t); continue; }
        lastRight = x + half;
      }
    }

    function drawRibs(rebuild) {
      const base = MARGIN.t + geom.innerH;
      clipRect.setAttribute('x', MARGIN.l);
      clipRect.setAttribute('y', 0);
      clipRect.setAttribute('width', geom.innerW);
      clipRect.setAttribute('height', base);

      if (rebuild) {
        gRibs.textContent = '';
        ribNodes = [];
        for (let k = 0; k < geom.bins; k++) {
          ribNodes.push(svgEl('rect', { rx: RIB_RADIUS, y: base, height: 0 }, gRibs));
        }
      }
      const w = Math.max(2, geom.pitch - GAP);
      for (let k = 0; k < geom.bins; k++) {
        const share = data.share[k];
        const h = share > 0 ? Math.max(1, (share / data.yMax) * geom.innerH) : 0;
        const node = ribNodes[k];
        node.setAttribute('x', (MARGIN.l + k * geom.pitch + GAP / 2).toFixed(2));
        node.setAttribute('width', w.toFixed(2));
        // The rect runs past the baseline and is clipped there, so only the
        // data end is rounded.
        node.setAttribute('y', (base - h).toFixed(2));
        node.setAttribute('height', (h + RIB_RADIUS * 2).toFixed(2));
        node.setAttribute('class', (data.gold && data.gold[k] ? 'rib rib-gold' : 'rib') + (k === hover ? ' is-hover' : ''));
      }
    }

    function drawLine() {
      const line = data.line;
      if (!line) {
        linePath.setAttribute('d', '');
        lineUnder.setAttribute('d', '');
        return;
      }
      let peak = 0;
      for (let k = 0; k < line.length; k++) peak = Math.max(peak, line[k]);
      const floor = peak * 0.004;
      let first = 0;
      let last = line.length - 1;
      while (first < last && line[first] <= floor) first++;
      while (last > first && line[last] <= floor) last--;
      first = Math.max(0, first - 1);
      last = Math.min(line.length - 1, last + 1);
      let d = '';
      for (let k = first; k <= last; k++) {
        d += (k === first ? 'M' : 'L') + xOfBin(k).toFixed(1) + ' ' + yOfShare(line[k]).toFixed(1);
      }
      linePath.setAttribute('d', d);
      lineUnder.setAttribute('d', d);
    }

    function drawStrike() {
      gStrike.textContent = '';
      if (!spec.strike) return;
      const x = Math.round(xOfValue(spec.strike.value)) + 0.5;
      svgEl('line', { x1: x, x2: x, y1: MARGIN.t - 6, y2: MARGIN.t + geom.innerH }, gStrike);
      const t = svgEl('text', { x: x, y: 16, 'text-anchor': 'middle' }, gStrike);
      t.textContent = spec.strike.label;
    }

    function topAt(series, k) {
      const s = series === 'line' && data.line ? data.line[k] : data.share[k];
      return yOfShare(s);
    }

    function drawLabels() {
      gLabels.textContent = '';
      // On a narrow plot the labels would sit on the marks; the key above
      // the chart carries the names instead.
      if (geom.innerW < 420) return;
      const items = spec.labels(data, geom.bins);
      const right = MARGIN.l + geom.innerW;
      for (let i = 0; i < items.length; i++) {
        const it = items[i];
        const g = svgEl('g', { class: 'dlabel' }, gLabels);
        if (it.series === 'line') {
          svgEl('line', { class: 'key key-line', x1: 0, x2: 16, y1: -4, y2: -4 }, g);
        } else {
          svgEl('rect', { class: 'key ' + (it.series === 'gold' ? 'key-gold' : 'key-rib'), x: 0, y: -10, width: 5, height: 11, rx: 1.5 }, g);
        }
        const keyW = it.series === 'line' ? 16 : 5;
        const text = svgEl('text', { x: keyW + 6, y: 0 }, g);
        text.textContent = it.text;
        const width = keyW + 6 + text.getComputedTextLength();

        const bx = xOfBin(it.bin);
        let x;
        let y;
        if (it.place === 'left') {
          x = bx - 12 - width;
          y = topAt(it.series, it.bin) + 4;
        } else if (it.place === 'right') {
          x = bx + 12;
          y = topAt(it.series, it.bin) + 4;
        } else {
          x = bx - width / 2;
          y = topAt(it.series, it.bin) - 12;
        }
        x = Math.min(Math.max(x, MARGIN.l + 4), right - width - 4);
        y = Math.max(y, MARGIN.t + 12);
        g.setAttribute('transform', 'translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ')');
      }
    }

    function showTip(k) {
      if (k === hover && !tip.hidden) return;
      if (hover >= 0 && ribNodes[hover]) ribNodes[hover].classList.remove('is-hover');
      hover = k;
      if (k < 0 || !data) {
        tip.hidden = true;
        cross.setAttribute('visibility', 'hidden');
        return;
      }
      ribNodes[k].classList.add('is-hover');
      const x = Math.round(xOfBin(k)) + 0.5;
      cross.setAttribute('x1', x);
      cross.setAttribute('x2', x);
      cross.setAttribute('y1', MARGIN.t);
      cross.setAttribute('y2', MARGIN.t + geom.innerH);
      cross.setAttribute('visibility', 'visible');
      fillTip(k);
      tip.hidden = false;
      const tw = tip.offsetWidth;
      const left = x + 14 + tw > geom.W - 8 ? x - 14 - tw : x + 14;
      tip.style.left = Math.max(8, left) + 'px';
      tip.style.top = MARGIN.t + 6 + 'px';
    }

    function fillTip(k) {
      const content = spec.tip(k, data, data.lo, data.hi);
      tip.textContent = '';
      const title = document.createElement('p');
      title.className = 'tip-title';
      title.textContent = content.title;
      tip.appendChild(title);
      for (let i = 0; i < content.rows.length; i++) {
        const row = document.createElement('p');
        row.className = 'tip-row';
        const key = document.createElement('span');
        key.className = 'tip-key tip-key-' + content.rows[i].series;
        const value = document.createElement('strong');
        value.textContent = content.rows[i].value;
        const label = document.createElement('span');
        label.textContent = content.rows[i].label;
        row.appendChild(key);
        row.appendChild(value);
        row.appendChild(label);
        tip.appendChild(row);
      }
    }

    function binFromEvent(e) {
      const rect = svg.getBoundingClientRect();
      const x = e.clientX - rect.left - MARGIN.l;
      if (x < 0 || x > geom.innerW) return -1;
      return Math.min(geom.bins - 1, Math.floor(x / geom.pitch));
    }

    function load() {
      const d = spec.domain(geom.bins);
      const r = spec.ribs(geom.bins, d.lo, d.hi);
      data = { lo: d.lo, hi: d.hi, share: r.share, gold: r.gold, line: spec.line(geom.bins, d.lo, d.hi), yMax: 0 };
      data.yMax = computeYMax();
    }

    function render(next) {
      if (next) spec = next;
      if (!spec) return;
      const g = measure();
      const rebuild = !geom || g.bins !== geom.bins || ribNodes.length !== g.bins;
      geom = g;
      svg.setAttribute('viewBox', '0 0 ' + geom.W + ' ' + geom.H);
      svg.setAttribute('width', geom.W);
      svg.setAttribute('height', geom.H);
      figure.setAttribute('aria-label', spec.ariaLabel);
      const open = hover;
      hover = -1;
      load();
      drawGrid();
      drawRibs(rebuild);
      drawStrike();
      drawLine();
      drawLabels();
      if (open >= 0 && open < geom.bins && !tip.hidden) { tip.hidden = true; showTip(open); } else showTip(-1);
    }

    /* Fast path for the hedge slider: only the stitched outline changes. */
    function refreshLine() {
      if (!spec || !data) return;
      data.line = spec.line(geom.bins, data.lo, data.hi);
      const yMax = computeYMax();
      if (yMax > data.yMax * 1.001 || yMax < data.yMax * 0.999) {
        data.yMax = yMax;
        drawGrid();
        drawRibs(false);
      }
      drawLine();
      drawLabels();
      if (hover >= 0 && !tip.hidden) fillTip(hover);
    }

    svg.addEventListener('pointermove', function (e) { showTip(binFromEvent(e)); });
    svg.addEventListener('pointerleave', function () { showTip(-1); });
    figure.addEventListener('keydown', function (e) {
      if (!geom) return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        const start = hover < 0 ? Math.floor(geom.bins / 2) : hover;
        const k = Math.min(geom.bins - 1, Math.max(0, start + (e.key === 'ArrowRight' ? 1 : -1)));
        showTip(k);
      } else if (e.key === 'Escape') {
        showTip(-1);
      }
    });
    figure.addEventListener('blur', function () { showTip(-1); });

    if ('ResizeObserver' in window) {
      let pending = 0;
      new ResizeObserver(function () {
        cancelAnimationFrame(pending);
        pending = requestAnimationFrame(function () { render(); });
      }).observe(figure);
    } else {
      window.addEventListener('resize', function () { render(); });
    }

    return { render: render, refreshLine: refreshLine };
  }

  B.createPlot = createPlot;
})(window.Bizfax = window.Bizfax || {});
