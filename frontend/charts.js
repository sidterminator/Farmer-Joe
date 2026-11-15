/* The one chart: revenue by harvest. Harvests run along the bottom, dollars up
 * the side, and two lines cross it: the farm without a hedge and the farm with
 * the plan. A steadier farm is a flatter line.
 *
 * createPlot(figure) returns { render(spec), refresh() }.
 *
 * spec = {
 *   ariaLabel: string,
 *   xTitle: string,                                    // x-axis title (default 'Harvest')
 *   bad: boolean[],                                    // optional: bad years (red ringed dots + tags)
 *   badLabel(i, base, plan) -> string,                 // full tag for bad year i
 *   base: { label, values: number[] },                 // revenue per harvest, no hedge
 *   plan: { label, values() -> number[] | null },      // with the plan; null: no line
 *   money(v) -> string,                                // axis and tooltip format
 *   worst(v) -> string,                                // label for each line's lowest harvest
 *   tip(i, base, plan) -> { title, rows: [{ key, value, label }] }
 * }
 */
(function (B) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const MARGIN = { l: 58, r: 18, t: 16, b: 42 };

  function svgEl(name, attrs, parent) {
    const node = document.createElementNS(NS, name);
    if (attrs) for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }

  function niceStep(span, maxTicks) {
    const raw = span / maxTicks;
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  }

  function createPlot(figure) {
    const svg = figure.querySelector('svg');
    const tip = figure.querySelector('.tip');

    const gGrid = svgEl('g', { class: 'grid' }, svg);
    const gAxis = svgEl('g', { class: 'axis' }, svg);
    const gFloors = svgEl('g', { class: 'floors' }, svg);
    const cross = svgEl('line', { class: 'cross', visibility: 'hidden' }, svg);
    const baseLine = svgEl('path', { class: 'line line-base' }, svg);
    const gBaseDots = svgEl('g', { class: 'dots dots-base' }, svg);
    const planUnder = svgEl('path', { class: 'line line-under' }, svg);
    const planLine = svgEl('path', { class: 'line line-plan' }, svg);
    const gPlanDots = svgEl('g', { class: 'dots dots-plan' }, svg);
    const gBad = svgEl('g', { class: 'bad-years' }, svg);   // rings, connectors and tags on top

    let spec = null;
    let geom = null;
    let base = [];
    let plan = null;
    let lo = 0;
    let hi = 1;
    let hover = -1;

    function measure() {
      const W = Math.max(260, figure.clientWidth);
      const H = Math.max(200, figure.clientHeight);
      // A wide plot keeps a right-hand margin for the worst-harvest labels.
      const labels = W >= 520;
      return { W: W, H: H, labels: labels, innerW: W - MARGIN.l - (labels ? 104 : MARGIN.r), innerH: H - MARGIN.t - MARGIN.b };
    }

    function xOf(i) { return MARGIN.l + (base.length > 1 ? (i / (base.length - 1)) * geom.innerW : geom.innerW / 2); }
    function yOf(v) { return MARGIN.t + geom.innerH - ((v - lo) / (hi - lo)) * geom.innerH; }

    /* The dollar range comes from the farm without a hedge, with room above
     * and below, so that line holds still while the plan's line moves. */
    function load() {
      base = spec.base.values;
      plan = spec.plan.values();
      let min = Math.min.apply(null, base);
      let max = Math.max.apply(null, base);
      const room = (max - min) * 0.12 || max * 0.05;
      min -= room;
      max += room;
      if (plan) {
        min = Math.min(min, Math.min.apply(null, plan) - room * 0.3);
        max = Math.max(max, Math.max.apply(null, plan) + room * 0.3);
      }
      const step = niceStep(max - min, 4);
      lo = Math.floor(min / step) * step;
      hi = Math.ceil(max / step) * step;
      return step;
    }

    function drawGrid(step) {
      gGrid.textContent = '';
      gAxis.textContent = '';
      const right = MARGIN.l + geom.innerW;
      const bottom = MARGIN.t + geom.innerH;
      for (let v = lo; v <= hi + step * 0.001; v += step) {
        const y = Math.round(yOf(v)) + 0.5;
        svgEl('line', { class: v === lo ? 'baseline' : 'rule-h', x1: MARGIN.l, x2: right, y1: y, y2: y }, gGrid);
        const t = svgEl('text', { x: MARGIN.l - 10, y: y + 4, 'text-anchor': 'end' }, gAxis);
        t.textContent = spec.money(v);
      }
      // Harvest numbers: every one where they fit, otherwise every second.
      const every = geom.innerW / base.length < 22 ? 2 : 1;
      for (let i = 0; i < base.length; i++) {
        if ((i + 1) % every !== 0 && i !== 0) continue;
        const t = svgEl('text', { x: xOf(i), y: bottom + 18, 'text-anchor': 'middle' }, gAxis);
        t.textContent = String(i + 1);
      }
      const title = svgEl('text', { class: 'axis-title', x: MARGIN.l + geom.innerW / 2, y: geom.H - 4, 'text-anchor': 'middle' }, gAxis);
      title.textContent = spec.xTitle || 'Harvest';
    }

    function path(values) {
      let d = '';
      for (let i = 0; i < values.length; i++) d += (i ? 'L' : 'M') + xOf(i).toFixed(1) + ' ' + yOf(values[i]).toFixed(1);
      return d;
    }

    function dots(group, values) {
      const have = group.childNodes.length;
      for (let i = have; i < values.length; i++) svgEl('circle', { r: 4 }, group);
      while (group.childNodes.length > values.length) group.removeChild(group.lastChild);
      for (let i = 0; i < values.length; i++) {
        const c = group.childNodes[i];
        c.setAttribute('cx', xOf(i).toFixed(1));
        c.setAttribute('cy', yOf(values[i]).toFixed(1));
        c.setAttribute('class', i === hover ? 'is-hover' : '');
      }
    }

    /* A rule at each line's lowest harvest, labelled in the right-hand margin,
     * so the gap between the two worst years can be read straight off the
     * chart. On a narrow plot the rules stay and the table carries the figures. */
    function drawFloors() {
      gFloors.textContent = '';
      const right = MARGIN.l + geom.innerW;
      const floors = [{ key: 'base', v: Math.min.apply(null, base) }];
      if (plan) floors.push({ key: 'plan', v: Math.min.apply(null, plan) });
      floors.sort(function (a, b) { return a.v - b.v; });
      const ys = floors.map(function (f) { return Math.round(yOf(f.v)) + 0.5; });
      // Keep the two labels a line apart: the lower one moves down, the higher up.
      const text = ys.map(function (y) { return y + 4; });
      if (text.length === 2 && text[0] - text[1] < 15) {
        const mid = (text[0] + text[1]) / 2;
        text[0] = mid + 7.5;
        text[1] = mid - 7.5;
      }
      floors.forEach(function (f, i) {
        svgEl('line', { class: 'floor floor-' + f.key, x1: MARGIN.l, x2: right + (geom.labels ? 6 : 0), y1: ys[i], y2: ys[i] }, gFloors);
        if (!geom.labels) return;
        const t = svgEl('text', { class: 'floor-label', x: right + 10, y: text[i] }, gFloors);
        t.textContent = spec.worst(f.v, f.key);
      });
    }

    function drawLines() {
      drawFloors();
      baseLine.setAttribute('d', path(base));
      dots(gBaseDots, base);
      const d = plan ? path(plan) : '';
      planLine.setAttribute('d', d);
      planUnder.setAttribute('d', d);
      dots(gPlanDots, plan || []);
      drawBad();
    }

    /* Bad years: a red, larger dot with an outer ring on the "without" line (the ring keeps it
     * readable without colour), a thin connector up to the matching "with" dot, and a tag. If the
     * full tags would overlap, only the 3 worst get values; the rest say "Bad year". */
    function drawBad() {
      gBad.textContent = '';
      const flags = spec.bad || [];
      const idx = [];
      for (let i = 0; i < base.length; i++) if (flags[i]) idx.push(i);
      gBaseDots.childNodes.forEach(function (c, i) {
        if (flags[i]) c.setAttribute('class', (c.getAttribute('class') + ' is-bad').trim());
      });
      if (!idx.length) return;
      const left = MARGIN.l + 4;
      const right = MARGIN.l + geom.innerW - 4;
      const items = idx.map(function (i) {
        const yb = yOf(base[i]);
        const yp = plan ? yOf(plan[i]) : yb;
        return { i: i, x: xOf(i), yb: yb, yp: yp, text: spec.badLabel ? spec.badLabel(i, base, plan) : 'Bad year' };
      });
      // Measure real text widths, then clamp each tag inside the plot.
      function layout() {
        items.forEach(function (it) {
          if (it.el) gBad.removeChild(it.el);
          it.el = svgEl('text', { class: 'bad-tag', 'text-anchor': 'middle' }, gBad);
          it.el.textContent = it.text;
          it.w = it.el.getBBox ? it.el.getBBox().width : it.text.length * 6.5;
          it.cx = Math.min(right - it.w / 2, Math.max(left + it.w / 2, it.x));
        });
      }
      function clash(a, b) { return Math.abs(a.cx - b.cx) < (a.w + b.w) / 2 + 6; }
      layout();
      const anyClash = items.some(function (a, k) { return items.some(function (b, m) { return m > k && clash(a, b); }); });
      if (anyClash) {
        const worst = items.slice().sort(function (a, b) { return base[a.i] - base[b.i]; }).slice(0, 3)
          .map(function (it) { return it.i; });
        items.forEach(function (it) { if (worst.indexOf(it.i) < 0) it.text = 'Bad year'; });
        layout();
      }
      // Stagger any remaining clashes into rows above the pair of dots.
      const placed = [];
      items.slice().sort(function (a, b) { return a.cx - b.cx; }).forEach(function (it) {
        const top = Math.min(it.yb, it.yp);
        let r = 0;
        const yAt = function (row) { return Math.max(MARGIN.t + 10, top - 14 - row * 15); };
        while (placed.some(function (o) { return Math.abs(o.y - yAt(r)) < 14 && clash(o, it); })) r++;
        it.y = yAt(r);
        placed.push(it);
      });
      items.forEach(function (it) {
        if (plan) gBad.insertBefore(svgEl('line', { class: 'bad-link', x1: it.x, x2: it.x, y1: it.yb, y2: it.yp }), gBad.firstChild);
        gBad.insertBefore(svgEl('circle', { class: 'bad-ring', cx: it.x, cy: it.yb, r: 8.5 }), gBad.firstChild);
        if (plan) gBad.insertBefore(svgEl('circle', { class: 'bad-ring-plan', cx: it.x, cy: it.yp, r: 7 }), gBad.firstChild);
        it.el.setAttribute('x', it.cx.toFixed(1));
        it.el.setAttribute('y', it.y.toFixed(1));
      });
    }

    function showTip(i) {
      if (i === hover && !tip.hidden) return;
      hover = i;
      if (i < 0 || !spec) {
        tip.hidden = true;
        cross.setAttribute('visibility', 'hidden');
        drawLines();
        return;
      }
      const x = Math.round(xOf(i)) + 0.5;
      cross.setAttribute('x1', x);
      cross.setAttribute('x2', x);
      cross.setAttribute('y1', MARGIN.t);
      cross.setAttribute('y2', MARGIN.t + geom.innerH);
      cross.setAttribute('visibility', 'visible');
      drawLines();
      fillTip(i);
      tip.hidden = false;
      const tw = tip.offsetWidth;
      const left = x + 14 + tw > geom.W - 6 ? x - 14 - tw : x + 14;
      tip.style.left = Math.max(6, left) + 'px';
      tip.style.top = MARGIN.t + 'px';
    }

    function fillTip(i) {
      const content = spec.tip(i, base, plan);
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

    function nearest(e) {
      const rect = svg.getBoundingClientRect();
      const x = e.clientX - rect.left;
      if (x < MARGIN.l - 12 || x > MARGIN.l + geom.innerW + 12) return -1;
      const t = (x - MARGIN.l) / geom.innerW;
      return Math.min(base.length - 1, Math.max(0, Math.round(t * (base.length - 1))));
    }

    function render(next) {
      if (next) spec = next;
      if (!spec) return;
      geom = measure();
      svg.setAttribute('viewBox', '0 0 ' + geom.W + ' ' + geom.H);
      svg.setAttribute('width', geom.W);
      svg.setAttribute('height', geom.H);
      figure.setAttribute('aria-label', spec.ariaLabel);
      hover = -1;
      tip.hidden = true;
      cross.setAttribute('visibility', 'hidden');
      drawGrid(load());
      drawLines();
    }

    /* Fast path while an amount is dragged or a hedge is ticked: the plan's
     * line moves, and the frame is redrawn only if the dollar range changed. */
    function refresh() {
      if (!spec || !geom) return;
      const before = lo + ':' + hi;
      const step = load();
      if (lo + ':' + hi !== before) drawGrid(step);
      drawLines();
      if (hover >= 0 && !tip.hidden) fillTip(hover);
    }

    svg.addEventListener('pointermove', function (e) { if (geom) showTip(nearest(e)); });
    svg.addEventListener('pointerleave', function () { showTip(-1); });
    figure.addEventListener('keydown', function (e) {
      if (!geom) return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        const start = hover < 0 ? 0 : hover + (e.key === 'ArrowRight' ? 1 : -1);
        showTip(Math.min(base.length - 1, Math.max(0, start)));
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
