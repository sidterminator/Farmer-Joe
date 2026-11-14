/* Screen logic: state, rendering and events. Reads data only through
 * Bizfax.source (sample-data.js) and does its sums through Bizfax.model. */
(function (B) {
  'use strict';

  const M = B.model;
  const SAVED_KEY = 'bizfax.saved';
  const MINUS = '−';

  function $(id) { return document.getElementById(id); }

  function make(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function icon(name) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'icon');
    svg.setAttribute('aria-hidden', 'true');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', '#i-' + name);
    svg.appendChild(use);
    return svg;
  }

  /* ---------- formatting ---------- */

  const whole = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
  const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

  function money(v) {
    const unit = Math.abs(v) >= 1e6 ? 1000 : 100;
    const r = Math.round(v / unit) * unit;
    return (r < 0 ? MINUS : '') + '$' + whole.format(Math.abs(r));
  }
  function signedMoney(v) {
    const unit = Math.abs(v) >= 1e6 ? 1000 : 100;
    const r = Math.round(v / unit) * unit;
    if (r === 0) return '$0';
    return (r < 0 ? MINUS : '+') + '$' + whole.format(Math.abs(r));
  }
  function dollars(v) { return '$' + whole.format(Math.round(v)); }
  function moneyShort(v) { return '$' + compact.format(v); }
  function percent(v, digits) { return (v * 100).toFixed(digits || 0) + '%'; }
  function signedPercent(v) {
    const r = Math.round(v * 100);
    if (r === 0) return '0%';
    return (r < 0 ? MINUS : '+') + Math.abs(r) + '%';
  }
  function plural(n, word) { return whole.format(n) + ' ' + word + (n === 1 ? '' : 's'); }

  function unitValue(v, unit, fixed) {
    if (unit === 'degF') return (fixed ? v.toFixed(1) : String(Math.round(v * 10) / 10)) + '°F';
    if (unit === 'in') return v.toFixed(1) + ' in';
    return Math.round(v) + ' ' + unit;
  }
  function unitPhrase(v, unit) {
    if (unit === 'in') return v.toFixed(1) + ' inches';
    if (unit === 'bu/ac') return Math.round(v) + ' bushels per acre';
    return unitValue(v, unit);
  }
  function unitTick(v, unit) {
    if (unit === 'degF') return Math.round(v) + '°';
    if (unit === 'in') return v.toFixed(1);
    return String(Math.round(v));
  }
  function unitCaption(unit) {
    if (unit === 'degF') return 'degrees F';
    if (unit === 'in') return 'inches';
    return unit === 'bu/ac' ? 'bushels per acre' : unit;
  }

  /* ---------- state ---------- */

  const state = {
    scenario: null,
    farm: null,
    marketId: null,
    side: 'yes',
    contracts: 0,
    tab: 'income',
    tableView: false,
    saved: new Set(),
    savedOnly: false,
    staged: null
  };

  let derived = null;   // revenue, side, steadiest, slider scale, income domain
  let plot = null;

  function market() {
    return state.scenario.markets.find(function (m) { return m.id === state.marketId; });
  }

  function loadSaved() {
    try {
      const raw = JSON.parse(localStorage.getItem(SAVED_KEY) || '[]');
      if (Array.isArray(raw)) state.saved = new Set(raw);
    } catch (e) { /* storage unavailable: saving lasts for this visit only */ }
  }
  function storeSaved() {
    try { localStorage.setItem(SAVED_KEY, JSON.stringify(Array.from(state.saved))); } catch (e) { /* see above */ }
  }

  function roundUpNice(v) {
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    const f = v / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 3 ? 3 : f <= 5 ? 5 : f <= 7 ? 7 : 10) * p;
  }
  function roundDownStep(v) {
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    const f = v / p;
    return (f >= 5 ? 5 : f >= 2 ? 2 : 1) * p;
  }

  function derive() {
    const revenue = M.farmIncome(state.scenario, state.farm);
    const side = M.sideOf(market(), state.side);
    const steadiest = M.steadiestContracts(revenue, side);
    const base = M.summary(revenue);
    const max = roundUpNice(Math.max(10000, steadiest * 2));
    const step = Math.max(1, roundDownStep(max / 200));
    const span = Math.max(base.sd * 3.3, base.mean * 0.02);
    derived = {
      revenue: revenue,
      side: side,
      steadiest: Math.round(steadiest / step) * step,
      max: max,
      step: step,
      base: base,
      lo: base.mean - span,
      hi: base.mean + span,
      hedged: null,
      hedgedSummary: null
    };
    applyHedge();
  }

  function applyHedge() {
    derived.hedged = M.hedgedIncome(derived.revenue, derived.side, state.contracts);
    derived.hedgedSummary = M.summary(derived.hedged);
  }

  function bestSide(m) {
    const revenue = M.farmIncome(state.scenario, state.farm);
    const yes = M.steadiestContracts(revenue, M.sideOf(m, 'yes'));
    const no = M.steadiestContracts(revenue, M.sideOf(m, 'no'));
    return no > yes ? 'no' : 'yes';
  }

  function choose(marketId, side) {
    state.marketId = marketId;
    state.side = side || bestSide(market());
    state.contracts = 0;
    derive();
    state.contracts = derived.steadiest;
    applyHedge();
    renderAll();
  }

  /* ---------- markets column ---------- */

  function renderMarkets() {
    const list = $('market-list');
    list.textContent = '';
    const all = state.scenario.markets;
    const shown = all.filter(function (m) { return !state.savedOnly || state.saved.has(m.id); });

    shown.forEach(function (m) {
      const selected = m.id === state.marketId;
      const saved = state.saved.has(m.id);
      const li = make('li', 'market' + (selected ? ' is-selected' : ''));

      const card = make('div', 'market-card');
      const pick = make('button', 'market-pick');
      pick.type = 'button';
      if (selected) pick.setAttribute('aria-current', 'true');
      pick.appendChild(make('span', 'market-name', m.name));
      pick.appendChild(make('span', 'market-question', m.question));
      pick.appendChild(make('span', 'market-meta', m.settles + ' · ' + m.source));
      pick.addEventListener('click', function () { choose(m.id); });
      card.appendChild(pick);

      const sides = make('div', 'sides');
      sides.setAttribute('role', 'group');
      sides.setAttribute('aria-label', m.name + ' prices');
      [['yes', 'Yes', m.yesCents], ['no', 'No', m.noCents]].forEach(function (s) {
        const held = selected && state.side === s[0];
        const b = make('button', 'side side-' + s[0]);
        b.type = 'button';
        b.setAttribute('aria-pressed', held ? 'true' : 'false');
        b.appendChild(make('span', 'side-word', s[1]));
        b.appendChild(make('span', 'side-price', s[2] + '¢'));
        b.addEventListener('click', function () { choose(m.id, s[0]); });
        sides.appendChild(b);
      });
      card.appendChild(sides);
      li.appendChild(card);

      const ribbon = make('button', 'ribbon');
      ribbon.type = 'button';
      ribbon.setAttribute('aria-pressed', saved ? 'true' : 'false');
      ribbon.setAttribute('aria-label', (saved ? 'Remove ' : 'Save ') + m.name + (saved ? ' from saved' : ''));
      ribbon.title = saved ? 'Saved' : 'Save';
      const flag = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      flag.setAttribute('viewBox', '0 0 40 28');
      flag.setAttribute('aria-hidden', 'true');
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', 'M1 2.5h36.5L29 14l8.5 11.5H1z');
      flag.appendChild(path);
      ribbon.appendChild(flag);
      ribbon.addEventListener('click', function () {
        if (state.saved.has(m.id)) state.saved.delete(m.id); else state.saved.add(m.id);
        storeSaved();
        renderMarkets();
        renderDock();
      });
      li.appendChild(ribbon);
      list.appendChild(li);
    });

    $('markets-empty').hidden = shown.length > 0;
    $('markets-note').textContent = state.savedOnly
      ? 'Showing ' + shown.length + ' saved of ' + all.length
      : plural(all.length, 'sample market');
  }

  /* ---------- main panel ---------- */

  function sideWord() { return state.side === 'yes' ? 'YES' : 'NO'; }
  function sideCents() { return state.side === 'yes' ? market().yesCents : market().noCents; }

  function legend(items) {
    const ul = $('legend');
    ul.textContent = '';
    items.forEach(function (it) {
      const li = make('li');
      li.appendChild(make('span', 'swatch swatch-' + it.series));
      li.appendChild(make('span', null, it.text));
      ul.appendChild(li);
    });
  }

  function row(cells, head) {
    const tr = make('tr');
    cells.forEach(function (c, i) {
      const cell = make(i === 0 || head ? 'th' : 'td');
      if (i === 0) cell.scope = head ? 'col' : 'row'; else if (head) cell.scope = 'col';
      if (c instanceof Node) cell.appendChild(c); else cell.textContent = c;
      tr.appendChild(cell);
    });
    return tr;
  }

  function fill(id, rows, head) {
    const target = $(id);
    target.textContent = '';
    rows.forEach(function (r) { target.appendChild(row(r, head)); });
  }

  function incomeTicks(lo, hi) {
    const raw = (hi - lo) / 6;
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / p;
    const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
    const ticks = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push({ value: v, label: moneyShort(v) });
    return ticks;
  }

  function peakBin(values, from, to) {
    let best = from;
    for (let k = from; k <= to; k++) if (values[k] > values[best]) best = k;
    return best;
  }

  function incomeSpec() {
    const d = derived;
    return {
      ariaLabel: 'Season income across ' + whole.format(d.revenue.length) + ' simulated seasons, without the hedge and with it. Use the left and right arrow keys to read values.',
      headroom: 1.5,
      yCaption: 'Share of seasons',
      strike: null,
      domain: function () { return { lo: d.lo, hi: d.hi }; },
      ribs: function (bins, lo, hi) { return { share: M.histogram(d.revenue, lo, hi, bins), gold: null }; },
      line: function (bins, lo, hi) { return state.contracts > 0 ? M.histogram(d.hedged, lo, hi, bins) : null; },
      xTicks: incomeTicks,
      labels: function (data, bins) {
        const peak = peakBin(data.share, 0, bins - 1);
        let shoulder = peak;
        while (shoulder > 0 && data.share[shoulder] > data.share[peak] * 0.5) shoulder--;
        const out = [{ series: 'rib', bin: shoulder, text: 'Without hedge', place: 'left' }];
        if (data.line) {
          const top = peakBin(data.line, 0, bins - 1);
          let edge = top;
          while (edge < bins - 1 && data.line[edge] > data.line[top] * 0.55) edge++;
          out.push({ series: 'line', bin: edge, text: 'With hedge', place: 'right' });
        }
        return out;
      },
      tip: function (k, data, lo, hi) {
        const w = (hi - lo) / data.share.length;
        const rows = [{ series: 'rib', value: percent(data.share[k], 1), label: 'of seasons without hedge' }];
        if (data.line) rows.push({ series: 'line', value: percent(data.line[k], 1), label: 'of seasons with hedge' });
        return { title: moneyShort(lo + k * w) + ' to ' + moneyShort(lo + (k + 1) * w), rows: rows };
      }
    };
  }

  function forecastSpec() {
    const m = market();
    const yesPaysAbove = m.yesWhen === 'at-or-above';
    const heldPaysAbove = state.side === 'yes' ? yesPaysAbove : !yesPaysAbove;
    const lo0 = M.quantile(m.underlying, 0.004);
    const hi0 = M.quantile(m.underlying, 0.996);
    const word = sideWord();
    return {
      ariaLabel: m.measure + ' across ' + whole.format(m.underlying.length) + ' simulated seasons, split at ' + unitPhrase(m.strike, m.unit) + ' where the contract pays. Use the left and right arrow keys to read values.',
      headroom: 1.3,
      yCaption: 'Share of seasons',
      strike: { value: m.strike, label: unitValue(m.strike, m.unit) },
      // Shift the range so a bin edge lands exactly on the strike.
      domain: function (bins) {
        const w = (hi0 - lo0) / bins;
        const below = Math.max(1, Math.min(bins - 1, Math.round((m.strike - lo0) / w)));
        const lo = m.strike - below * w;
        return { lo: lo, hi: lo + bins * w };
      },
      ribs: function (bins, lo, hi) {
        const w = (hi - lo) / bins;
        const gold = new Uint8Array(bins);
        for (let k = 0; k < bins; k++) {
          const above = lo + (k + 0.5) * w >= m.strike;
          gold[k] = above === heldPaysAbove ? 1 : 0;
        }
        return { share: M.histogram(m.underlying, lo, hi, bins), gold: gold };
      },
      line: function () { return null; },
      xTicks: function (lo, hi) {
        const raw = (hi - lo) / 7;
        const p = Math.pow(10, Math.floor(Math.log10(raw)));
        const f = raw / p;
        const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p;
        const ticks = [];
        for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push({ value: v, label: unitTick(v, m.unit) });
        return ticks;
      },
      labels: function (data, bins) {
        let split = 0;
        while (split < bins && data.gold[split] === data.gold[0]) split++;
        const left = peakBin(data.share, 0, Math.max(0, split - 1));
        const right = peakBin(data.share, Math.min(bins - 1, split), bins - 1);
        const pays = word + ' pays $1';
        const not = word + ' pays $0';
        return [
          { series: data.gold[0] ? 'gold' : 'rib', bin: Math.min(left, Math.max(0, split - 3)), text: data.gold[0] ? pays : not, place: 'left' },
          { series: data.gold[bins - 1] ? 'gold' : 'rib', bin: Math.max(right, Math.min(bins - 1, split + 2)), text: data.gold[bins - 1] ? pays : not, place: 'right' }
        ];
      },
      tip: function (k, data, lo, hi) {
        const w = (hi - lo) / data.share.length;
        return {
          title: unitValue(lo + k * w, m.unit, true) + ' to ' + unitValue(lo + (k + 1) * w, m.unit, true),
          rows: [{ series: data.gold[k] ? 'gold' : 'rib', value: percent(data.share[k], 1), label: 'of seasons, ' + word + ' pays ' + (data.gold[k] ? '$1' : '$0') }]
        };
      }
    };
  }

  function renderBins() {
    const GROUPS = 12;
    const m = market();
    if (state.tab === 'income') {
      const d = derived;
      const w = (d.hi - d.lo) / GROUPS;
      const a = M.histogram(d.revenue, d.lo, d.hi, GROUPS);
      const b = M.histogram(d.hedged, d.lo, d.hi, GROUPS);
      fill('bins-head', [['Season income', 'Without hedge', 'With hedge']], true);
      const rows = [];
      for (let k = 0; k < GROUPS; k++) {
        rows.push([moneyShort(d.lo + k * w) + ' to ' + moneyShort(d.lo + (k + 1) * w), percent(a[k], 1), percent(b[k], 1)]);
      }
      fill('bins-body', rows);
    } else {
      const lo = M.quantile(m.underlying, 0.004);
      const hi = M.quantile(m.underlying, 0.996);
      const w = (hi - lo) / GROUPS;
      const a = M.histogram(m.underlying, lo, hi, GROUPS);
      fill('bins-head', [[m.measure + ', ' + unitCaption(m.unit), 'Share of seasons']], true);
      const rows = [];
      for (let k = 0; k < GROUPS; k++) {
        rows.push([unitValue(lo + k * w, m.unit, true) + ' to ' + unitValue(lo + (k + 1) * w, m.unit, true), percent(a[k], 1)]);
      }
      fill('bins-body', rows);
    }
  }

  function verdict(points) {
    const chip = make('span', 'verdict');
    let name = 'equal';
    let text = 'About fair';
    if (points >= 2) { name = 'check'; text = 'Cheap by ' + points + (points === 1 ? ' point' : ' points'); }
    else if (points <= -2) { name = 'alert'; text = 'Expensive by ' + Math.abs(points) + ' points'; }
    chip.appendChild(icon(name));
    chip.appendChild(make('span', null, text));
    return chip;
  }

  function renderIncomeNumbers() {
    const d = derived;
    const a = d.base;
    const b = d.hedgedSummary;
    const m = market();
    const cost = state.contracts * d.side.price;
    const hedging = state.contracts > 0;

    $('panel-lede').textContent = hedging
      ? plural(state.contracts, 'contract') + ' of ' + sideWord() + ' on ' + m.name + ', costing ' + dollars(cost) + ' up front.'
      : 'No hedge yet. Drag the hedge size to add ' + sideWord() + ' contracts on ' + m.name + '.';

    fill('compare-head', [['', 'Without hedge', 'With hedge', 'Change']], true);
    fill('compare-body', [
      ['Average season', money(a.mean), money(b.mean), hedging ? signedMoney(b.mean - a.mean) : '—'],
      ['Typical swing', '±' + money(a.sd), '±' + money(b.sd), hedging ? signedPercent(b.sd / a.sd - 1) : '—'],
      ['1-in-20 bad season', money(a.bad), money(b.bad), hedging ? signedMoney(b.bad - a.bad) : '—']
    ]);

    $('hedge-out').textContent = whole.format(state.contracts) + ' ' + sideWord();
    $('hedge-cost').textContent = hedging
      ? 'Costs ' + dollars(cost) + ' at ' + sideCents() + '¢ each'
      : 'No cost';
    const range = $('hedge-range');
    range.style.setProperty('--fill', (state.contracts / d.max) * 100 + '%');
    range.setAttribute('aria-valuetext', plural(state.contracts, 'contract'));
  }

  function renderPanel() {
    const d = derived;
    const m = market();
    const income = state.tab === 'income';

    document.querySelectorAll('.tabs [role="tab"]').forEach(function (t) {
      const on = t.dataset.tab === state.tab;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
    });
    $('view').setAttribute('aria-labelledby', 'tab-' + state.tab);

    $('hedge').hidden = !income;
    $('explain').hidden = income;

    if (income) {
      $('panel-title').textContent = 'Season income with and without the hedge';
      legend([{ series: 'rib', text: 'Without hedge' }, { series: 'line', text: 'With hedge' }]);

      const range = $('hedge-range');
      range.max = d.max;
      range.step = d.step;
      range.value = state.contracts;
      $('range-mark').style.setProperty('--at', d.steadiest / d.max);
      $('range-mark').hidden = d.steadiest === 0;
      $('hedge-steady').disabled = d.steadiest === 0;
      const note = $('hedge-note');
      note.hidden = d.steadiest > 0;
      note.textContent = sideWord() + ' on ' + m.name + ' pays out in seasons when this farm already earns more, so it adds swing instead of removing it. Try ' + (state.side === 'yes' ? 'NO' : 'YES') + '.';
      renderIncomeNumbers();
    } else {
      const p = M.chance(d.side);
      const cents = sideCents();
      const points = Math.round(p * 100) - cents;
      const word = sideWord();
      $('panel-title').textContent = m.measure;
      $('panel-lede').textContent = word + ' pays $1 in ' + percent(p) + ' of simulated seasons. The market charges ' + cents + '¢.';
      legend([{ series: 'gold', text: word + ' pays $1' }, { series: 'rib', text: word + ' pays $0' }]);
      fill('compare-head', [['', word + ' on ' + m.name]], true);
      fill('compare-body', [
        ['Chance by the model', percent(p)],
        ['Price of ' + word, cents + '¢'],
        ['Difference', verdict(points)]
      ]);
      const yesAbove = m.yesWhen === 'at-or-above';
      const when = (state.side === 'yes') === yesAbove ? 'is ' + unitPhrase(m.strike, m.unit) + ' or above' : 'is below ' + unitPhrase(m.strike, m.unit);
      $('explain').textContent = 'One ' + word + ' contract costs ' + cents + '¢ now and pays $1 if the ' + m.measure.charAt(0).toLowerCase() + m.measure.slice(1) + ' ' + when + '. Otherwise it pays nothing. ' + m.settles + ', from ' + m.sourceLong + '.';
    }

    const toggle = $('table-toggle');
    toggle.setAttribute('aria-pressed', state.tableView ? 'true' : 'false');
    toggle.textContent = state.tableView ? 'Chart view' : 'Table view';
    $('plot').hidden = state.tableView;
    $('bins').hidden = !state.tableView;
    $('legend').hidden = state.tableView;
    if (state.tableView) renderBins(); else plot.render(income ? incomeSpec() : forecastSpec());
  }

  /* ---------- header and dock ---------- */

  function renderHeader() {
    const f = state.farm;
    $('farm-line').textContent = (f.own ? 'Your seasons' : f.name) + ' · ' + whole.format(f.acres) + ' acres of ' + f.crop + ' · $' + f.pricePerBu.toFixed(2) + ' per bushel';
    $('sample-text').textContent = f.own
      ? 'Sample data. Prices and forecasts are made up; the yields are yours.'
      : 'Sample data. Prices, forecasts and farm figures are made up.';
  }

  function renderDock() {
    const f = state.farm;
    const y = M.farmYield(f.seasons, state.scenario.fallbackYieldSd);
    const years = f.seasons.map(function (s) { return s.year; });
    const span = years.length > 1 ? Math.min.apply(null, years) + ' to ' + Math.max.apply(null, years) : String(years[0]);
    const status = $('farm-status');
    status.textContent = '';
    status.classList.toggle('is-own', !!f.own);
    status.appendChild(make('span', null, (f.own ? 'Using your data: ' : 'Using the sample farm: ') + plural(f.seasons.length, 'season') + ', ' + span + ', averaging ' + Math.round(y.mean) + ' bu/acre.'));
    if (f.own) {
      if (!y.ownSpread) status.appendChild(make('span', null, ' Add ' + plural(3 - f.seasons.length, 'more season') + ' and the swing will come from your yields too.'));
      const reset = make('button', 'link', 'Use the sample farm');
      reset.type = 'button';
      reset.addEventListener('click', function () {
        state.farm = Object.assign({}, state.scenario.farm, { own: false });
        say('Back to the sample farm.', '');
        choose(state.marketId, state.side);
      });
      status.appendChild(document.createTextNode(' '));
      status.appendChild(reset);
    }

    const toggle = $('saved-toggle');
    toggle.setAttribute('aria-pressed', state.savedOnly ? 'true' : 'false');
    $('saved-count').textContent = state.saved.size;

    const staged = state.staged;
    $('staged-chip').hidden = !staged;
    $('season-input').hidden = !!staged;
    if (staged) $('staged-name').textContent = staged.name + ' · ' + plural(staged.seasons.length, 'season');
    syncSend();
  }

  function syncSend() {
    $('upload-form').classList.toggle('has-data', !!state.staged || $('season-input').value.trim() !== '');
  }

  function say(text, kind) {
    const node = $('upload-status');
    node.textContent = '';
    if (text && kind === 'error') node.appendChild(icon('alert'));
    if (text) node.appendChild(make('span', null, text));
    node.classList.toggle('is-error', kind === 'error');
    node.classList.toggle('is-own', kind === 'done');
    $('season-input').setAttribute('aria-invalid', kind === 'error' ? 'true' : 'false');
  }

  function renderAll() {
    renderHeader();
    renderMarkets();
    renderPanel();
    renderDock();
  }

  /* ---------- farm data: import and upload ---------- */

  function validSeason(year, value) {
    return Number.isInteger(year) && year >= 1950 && year <= 2100 && isFinite(value) && value > 0 && value < 500;
  }

  /* Accepts a CSV with a year column and a yield column (bushels per acre).
   * Optional acres and price columns replace the sample farm's figures. */
  function parseSeasonsCsv(text) {
    const lines = text.split(/\r?\n/).map(function (l) { return l.trim(); }).filter(Boolean);
    if (!lines.length) return { seasons: [] };
    const delimiter = lines[0].indexOf('\t') >= 0 ? '\t' : lines[0].indexOf(';') >= 0 ? ';' : ',';
    const cells = function (l) { return l.split(delimiter).map(function (c) { return c.trim().replace(/^"|"$/g, ''); }); };
    let col = { year: 0, yield: 1, acres: -1, price: -1 };
    let start = 0;
    if (/[a-z]/i.test(lines[0])) {
      const head = cells(lines[0]).map(function (h) { return h.toLowerCase(); });
      col = {
        year: head.findIndex(function (h) { return /year|season/.test(h); }),
        yield: head.findIndex(function (h) { return /yield|bu/.test(h); }),
        acres: head.findIndex(function (h) { return /^acres?$|planted|area/.test(h); }),
        price: head.findIndex(function (h) { return /price/.test(h); })
      };
      start = 1;
    }
    if (col.year < 0 || col.yield < 0) return { seasons: [] };
    const byYear = new Map();
    let acres = null;
    let price = null;
    for (let i = start; i < lines.length; i++) {
      const c = cells(lines[i]);
      const year = Number(c[col.year]);
      const value = Number(c[col.yield]);
      if (!validSeason(year, value)) continue;
      byYear.set(year, { year: year, yield: value });
      if (col.acres >= 0 && Number(c[col.acres]) > 0) acres = Number(c[col.acres]);
      if (col.price >= 0 && Number(c[col.price]) > 0) price = Number(c[col.price]);
    }
    const seasons = Array.from(byYear.values()).sort(function (a, b) { return a.year - b.year; });
    return { seasons: seasons, acres: acres, pricePerBu: price };
  }

  function parseTypedSeason(text) {
    const match = /^\s*(\d{4})\s*[,;:\s]\s*(\d+(?:\.\d+)?)/.exec(text);
    if (!match) return null;
    const season = { year: Number(match[1]), yield: Number(match[2]) };
    return validSeason(season.year, season.yield) ? season : null;
  }

  function stageFile(file) {
    const reader = new FileReader();
    reader.onerror = function () {
      say('Could not read ' + file.name + '. Try importing it again.', 'error');
    };
    reader.onload = function () {
      const parsed = parseSeasonsCsv(String(reader.result));
      if (!parsed.seasons.length) {
        state.staged = null;
        renderDock();
        say('No seasons found in ' + file.name + '. It needs a year column and a yield column in bushels per acre.', 'error');
        return;
      }
      state.staged = { name: file.name, seasons: parsed.seasons, acres: parsed.acres, pricePerBu: parsed.pricePerBu };
      renderDock();
      say(file.name + ' is ready. Press the arrow to upload it.', '');
      document.querySelector('.send').focus();
    };
    reader.readAsText(file);
  }

  function useSeasons(seasons, extra, message) {
    B.source.uploadSeasons(seasons).then(function (result) {
      const sample = state.scenario.farm;
      state.farm = {
        name: 'Your farm',
        crop: sample.crop,
        place: '',
        acres: (extra && extra.acres) || state.farm.acres,
        pricePerBu: (extra && extra.pricePerBu) || state.farm.pricePerBu,
        seasons: seasons,
        own: true
      };
      state.staged = null;
      $('season-input').value = '';
      say(message + (result.stored ? '' : ' Kept in this browser only.'), 'done');
      choose(state.marketId, state.side);
    }).catch(function () {
      say('The upload did not go through. Check your connection and press the arrow again.', 'error');
    });
  }

  function onUpload(e) {
    e.preventDefault();
    if (state.staged) {
      const s = state.staged;
      useSeasons(s.seasons, s, 'Uploaded ' + plural(s.seasons.length, 'season') + ' from ' + s.name + '.');
      return;
    }
    const input = $('season-input');
    if (!input.value.trim()) {
      say('Nothing to upload yet. Import a file, or type a season such as 2026, 192.', 'error');
      input.focus();
      return;
    }
    const season = parseTypedSeason(input.value);
    if (!season) {
      say('Type a season as year, bushels per acre. For example: 2026, 192.', 'error');
      input.focus();
      return;
    }
    const current = state.farm.own ? state.farm.seasons.filter(function (s) { return s.year !== season.year; }) : [];
    const seasons = current.concat([season]).sort(function (a, b) { return a.year - b.year; });
    useSeasons(seasons, null, 'Added ' + season.year + ' at ' + season.yield + ' bu/acre.');
  }

  /* ---------- wiring ---------- */

  function bind() {
    document.querySelectorAll('.tabs [role="tab"]').forEach(function (tab) {
      tab.addEventListener('click', function () {
        state.tab = tab.dataset.tab;
        renderPanel();
      });
      tab.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        state.tab = state.tab === 'income' ? 'forecast' : 'income';
        renderPanel();
        $('tab-' + state.tab).focus();
      });
    });

    $('table-toggle').addEventListener('click', function () {
      state.tableView = !state.tableView;
      renderPanel();
    });

    const range = $('hedge-range');
    range.addEventListener('input', function () {
      state.contracts = Number(range.value);
      applyHedge();
      renderIncomeNumbers();
      if (state.tableView) renderBins(); else plot.refreshLine();
    });
    $('hedge-none').addEventListener('click', function () { setContracts(0); });
    $('hedge-steady').addEventListener('click', function () { setContracts(derived.steadiest); });

    $('import-btn').addEventListener('click', function () { $('file-input').click(); });
    $('file-input').addEventListener('change', function (e) {
      if (e.target.files && e.target.files[0]) stageFile(e.target.files[0]);
      e.target.value = '';
    });
    $('staged-remove').addEventListener('click', function () {
      state.staged = null;
      renderDock();
      say('', '');
      $('season-input').focus();
    });
    $('upload-form').addEventListener('submit', onUpload);
    $('season-input').addEventListener('input', function () {
      if ($('upload-status').classList.contains('is-error')) say('', '');
      syncSend();
    });
    $('show-all').addEventListener('click', function () {
      state.savedOnly = false;
      renderMarkets();
      renderDock();
      $('saved-toggle').focus();
    });

    $('saved-toggle').addEventListener('click', function () {
      state.savedOnly = !state.savedOnly;
      renderMarkets();
      renderDock();
    });
  }

  function setContracts(n) {
    state.contracts = n;
    applyHedge();
    renderPanel();
  }

  function start() {
    plot = B.createPlot($('plot'));
    loadSaved();
    bind();
    B.source.scenario().then(function (scenario) {
      state.scenario = scenario;
      state.farm = Object.assign({}, scenario.farm, { own: false });
      choose(scenario.markets[0].id);
    }).catch(function () {
      $('panel-title').textContent = 'The market data did not load';
      $('panel-lede').textContent = 'Reload the page to try again.';
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})(window.Bizfax = window.Bizfax || {});
