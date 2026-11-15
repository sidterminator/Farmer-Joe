/* The one chart form: season income as a distribution. The season without
 * protection is drawn as columns, and the season with the farmer's plan is a
 * line laid over them, so a tighter spread reads as a taller, narrower outline
 * on the same axis.
 *
 * createPlot(figure) returns { render(spec), refresh() }.
 *
 * spec = {
 *   ariaLabel: string,
 *   lo, hi: number,                         // x range
 *   headroom: number,                       // y-axis top as a multiple of the columns' peak
 *   base: { label, values(bins, lo, hi) -> Float64Array },
 *   plan: { label, values(bins, lo, hi) -> Float64Array | null },   // null: no line
 *   xTicks(lo, hi) -> [{ value, label }],
 *   tip(bin, base, plan, lo, hi) -> { title, rows: [{ key, value, label }] }
 * }
 */
(function (B) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const MARGIN = { l: 44, r: 14, t: 14, b: 28 };
  const PITCH = 10;        // target distance between column centres, px
  const GAP = 2;           // surface gap between columns, px
  const RADIUS = 3;

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

  function peakOf(values) {
    let p = 0;
    for (let k = 0; k < values.length; k++) p = Math.max(p, values[k]);
    return p;
  }

  function createPlot(figure) {
    const svg = figure.querySelector('svg');
    const tip = figure.querySelector('.tip');
    const clipId = 'clip-' + Math.random().toString(36).slice(2, 8);

    const defs = svgEl('defs', null, svg);
    const clipRect = svgEl('rect', null, svgEl('clipPath', { id: clipId }, defs));
    const gGrid = svgEl('g', { class: 'grid' }, svg);
    const gCols = svgEl('g', { class: 'cols', 'clip-path': 'url(#' + clipId + ')' }, svg);
    const cross = svgEl('line', { class: 'cross', visibility: 'hidden' }, svg);
    const planUnder = svgEl('path', { class: 'plan-under' }, svg);
    const planLine = svgEl('path', { class: 'plan-line' }, svg);
    const gAxis = svgEl('g', { class: 'axis' }, svg);
    const gLabels = svgEl('g', { class: 'dlabels' }, svg);

    let spec = null;
    let geom = null;
    let base = null;
    let plan = null;
    let yMax = 1;
    let nodes = [];
    let hover = -1;

    function measure() {
      const W = Math.max(260, figure.clientWidth);
      const H = Math.max(200, figure.clientHeight);
      const innerW = W - MARGIN.l - MARGIN.r;
      const innerH = H - MARGIN.t - MARGIN.b;
      const bins = Math.max(16, Math.round(innerW / PITCH));
      return { W: W, H: H, innerW: innerW, innerH: innerH, bins: bins, pitch: innerW / bins };
    }

    function xOfBin(k) { return MARGIN.l + (k + 0.5) * geom.pitch; }
    function xOfValue(v) { return MARGIN.l + ((v - spec.lo) / (spec.hi - spec.lo)) * geom.innerW; }
    function yOf(share) { return MARGIN.t + geom.innerH - (share / yMax) * geom.innerH; }

    function load() {
      base = spec.base.values(geom.bins, spec.lo, spec.hi);
      plan = spec.plan.values(geom.bins, spec.lo, spec.hi);
      // The columns set the scale, with headroom, so they hold still while the
      // line over them grows or shrinks.
      yMax = Math.max(peakOf(base) * (spec.headroom || 1.1), plan ? peakOf(plan) * 1.1 : 0, 1e-6);
    }

    function drawGrid() {
      gGrid.textContent = '';
      gAxis.textContent = '';
      const bottom = MARGIN.t + geom.innerH;
      const right = MARGIN.l + geom.innerW;
      const step = niceStep(yMax, 4);
      const pct = +(step * 100).toFixed(6);
      const decimals = Number.isInteger(pct) ? 0 : Number.isInteger(+(pct * 10).toFixed(6)) ? 1 : 2;
      for (let v = step; v <= yMax * 1.0001; v += step) {
        const y = Math.round(yOf(v)) + 0.5;
        svgEl('line', { class: 'rule-h', x1: MARGIN.l, x2: right, y1: y, y2: y }, gGrid);
        const t = svgEl('text', { x: MARGIN.l - 8, y: y + 4, 'text-anchor': 'end' }, gAxis);
        t.textContent = (v * 100).toFixed(decimals) + '%';
      }
      svgEl('line', { class: 'baseline', x1: MARGIN.l, x2: right, y1: Math.round(bottom) + 0.5, y2: Math.round(bottom) + 0.5 }, gGrid);

      let lastRight = -Infinity;
      spec.xTicks(spec.lo, spec.hi).forEach(function (tick) {
        const x = xOfValue(tick.value);
        if (x < MARGIN.l + 8 || x > right - 8) return;
        const text = svgEl('text', { x: x, y: geom.H - 8, 'text-anchor': 'middle' }, gAxis);
        text.textContent = tick.label;
        const half = text.getComputedTextLength() / 2;
        if (x - half < lastRight + 14) { gAxis.removeChild(text); return; }
        lastRight = x + half;
      });
    }

    function drawColumns(rebuild) {
      const bottom = MARGIN.t + geom.innerH;
      clipRect.setAttribute('x', MARGIN.l);
      clipRect.setAttribute('y', 0);
      clipRect.setAttribute('width', geom.innerW);
      clipRect.setAttribute('height', bottom);
      if (rebuild) {
        gCols.textContent = '';
        nodes = [];
        for (let k = 0; k < geom.bins; k++) nodes.push(svgEl('rect', { rx: RADIUS, y: bottom, height: 0 }, gCols));
      }
      const w = Math.max(2, geom.pitch - GAP);
      for (let k = 0; k < geom.bins; k++) {
        const h = base[k] > 0 ? Math.max(1, (base[k] / yMax) * geom.innerH) : 0;
        const node = nodes[k];
        node.setAttribute('x', (MARGIN.l + k * geom.pitch + GAP / 2).toFixed(2));
        node.setAttribute('width', w.toFixed(2));
        // Each column runs past the baseline and is clipped there, so only the
        // data end is rounded.
        node.setAttribute('y', (bottom - h).toFixed(2));
        node.setAttribute('height', (h + RADIUS * 2).toFixed(2));
        node.setAttribute('class', 'col' + (k === hover ? ' is-hover' : ''));
      }
    }

    function drawLine() {
      if (!plan) {
        planLine.setAttribute('d', '');
        planUnder.setAttribute('d', '');
        return;
      }
      const floor = peakOf(plan) * 0.004;
      let first = 0;
      let last = plan.length - 1;
      while (first < last && plan[first] <= floor) first++;
      while (last > first && plan[last] <= floor) last--;
      first = Math.max(0, first - 1);
      last = Math.min(plan.length - 1, last + 1);
      let d = '';
      for (let k = first; k <= last; k++) d += (k === first ? 'M' : 'L') + xOfBin(k).toFixed(1) + ' ' + yOf(plan[k]).toFixed(1);
      planLine.setAttribute('d', d);
      planUnder.setAttribute('d', d);
    }

    /* A label on each shape: the columns on their left shoulder, the line on
     * its right. Skipped on narrow plots, where the key above the chart names
     * them instead. */
    function drawLabels() {
      gLabels.textContent = '';
      if (geom.innerW < 420) return;
      const right = MARGIN.l + geom.innerW;

      function put(text, keyKind, x, y, anchorEnd) {
        const g = svgEl('g', { class: 'dlabel' }, gLabels);
        const keyW = keyKind === 'plan' ? 16 : 10;
        if (keyKind === 'plan') svgEl('line', { class: 'key-plan', x1: 0, x2: 16, y1: -4, y2: -4 }, g);
        else svgEl('rect', { class: 'key-base', x: 0, y: -9, width: 10, height: 10, rx: 2 }, g);
        const t = svgEl('text', { x: keyW + 6, y: 0 }, g);
        t.textContent = text;
        const width = keyW + 6 + t.getComputedTextLength();
        let left = anchorEnd ? x - width : x;
        left = Math.min(Math.max(left, MARGIN.l + 4), right - width - 4);
        g.setAttribute('transform', 'translate(' + left.toFixed(1) + ' ' + Math.max(y, MARGIN.t + 12).toFixed(1) + ')');
      }

      const basePeak = base.indexOf(peakOf(base));
      let shoulder = basePeak;
      while (shoulder > 0 && base[shoulder] > base[basePeak] * 0.5) shoulder--;
      put(spec.base.label, 'base', xOfBin(shoulder) - 12, yOf(base[shoulder]) + 4, true);

      if (plan) {
        const planPeak = plan.indexOf(peakOf(plan));
        let edge = planPeak;
        while (edge < plan.length - 1 && plan[edge] > plan[planPeak] * 0.6) edge++;
        put(spec.plan.label, 'plan', xOfBin(edge) + 12, yOf(plan[edge]) + 4, false);
      }
    }

    function showTip(k) {
      if (k === hover && !tip.hidden) return;
      if (hover >= 0 && nodes[hover]) nodes[hover].classList.remove('is-hover');
      hover = k;
      if (k < 0 || !spec) {
        tip.hidden = true;
        cross.setAttribute('visibility', 'hidden');
        return;
      }
      nodes[k].classList.add('is-hover');
      const x = Math.round(xOfBin(k)) + 0.5;
      cross.setAttribute('x1', x);
      cross.setAttribute('x2', x);
      cross.setAttribute('y1', MARGIN.t);
      cross.setAttribute('y2', MARGIN.t + geom.innerH);
      cross.setAttribute('visibility', 'visible');
      fillTip(k);
      tip.hidden = false;
      const tw = tip.offsetWidth;
      const left = x + 14 + tw > geom.W - 6 ? x - 14 - tw : x + 14;
      tip.style.left = Math.max(6, left) + 'px';
      tip.style.top = MARGIN.t + 'px';
    }

    function fillTip(k) {
      const content = spec.tip(k, base, plan, spec.lo, spec.hi);
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
      const rebuild = !geom || g.bins !== geom.bins || nodes.length !== g.bins;
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
      drawLine();
      drawLabels();
    }

    /* Fast path while an amount is dragged or a market is ticked: the columns
     * hold still and the line over them moves. */
    function refresh() {
      if (!spec || !geom) return;
      const before = yMax;
      load();
      if (Math.abs(yMax - before) > before * 0.001) { drawGrid(); drawColumns(false); }
      drawLine();
      drawLabels();
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
