/* Screen logic: the three screens, the farm form, the plan and the order.
 * Data comes only through FarmerJoe.source (sample-data.js); sums go through
 * FarmerJoe.model. */
(function (B) {
  'use strict';

  const M = B.model;
  const STORE_KEY = 'farmerjoe.farm';
  const MINUS = '−';
  const HARVESTS = 20;   // sample harvests on the chart
  const LEAN = [
    { label: 'Lowest cost', value: 0.2 },
    { label: 'Mostly cost', value: 0.4 },
    { label: 'Balanced', value: 0.6 },
    { label: 'Mostly stability', value: 0.8 },
    { label: 'Most stability', value: 1 }
  ];

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

  function rounded(v) {
    const unit = Math.abs(v) >= 1e6 ? 1000 : 100;
    return Math.round(v / unit) * unit;
  }
  function money(v) {
    const r = rounded(v);
    return (r < 0 ? MINUS : '') + '$' + whole.format(Math.abs(r));
  }
  function signedMoney(v) {
    const r = rounded(v);
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
  function aboutMiles(miles) {
    if (miles < 10) return 'under 10 mi';
    return whole.format(Math.round(miles / 5) * 5) + ' mi';
  }

  /* ---------- state ---------- */

  const state = {
    farm: {
      lat: null, lon: null, label: '', stationId: null, miles: 0,
      crop: 'corn', acres: 300, yield: 200, price: 4.5, budget: 15000, lean: 4
    },
    touched: { yield: false, price: false },
    scenario: null,
    revenue: null,
    base: null,
    planArr: null,
    harvests: [],
    plan: null,
    tickets: [],
    inGraph: [],
    custom: false,
    trimmed: false,
    tableView: false
  };

  let map = null;
  let plot = null;
  let firstShow = true;

  function hasLocation() { return state.farm.lat !== null && !!state.farm.stationId; }
  function stationOf(farm) { return B.stations.find(function (s) { return s.id === farm.stationId; }); }

  function save() {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify({ farm: state.farm, touched: state.touched })); } catch (e) { /* this visit only */ }
  }
  function restore() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || 'null');
      if (saved && saved.farm && B.crops[saved.farm.crop]) {
        Object.assign(state.farm, saved.farm);
        Object.assign(state.touched, saved.touched || {});
      }
    } catch (e) { /* start fresh */ }
  }

  /* ---------- towns ---------- */

  let places = null;
  function getPlaces() {
    if (!places) {
      places = B.placesRaw.split(';').map(function (s) {
        const p = s.split('|');
        return { name: p[0], state: p[1], lat: +p[2], lon: +p[3], key: (p[0] + ', ' + p[1]).toLowerCase() };
      });
    }
    return places;
  }

  function suggest(text) {
    const t = text.trim().toLowerCase();
    if (t.length < 2) return [];
    const out = [];
    const list = getPlaces();
    for (let i = 0; i < list.length && out.length < 8; i++) if (list[i].key.indexOf(t) === 0) out.push(list[i]);
    return out;
  }

  /* The list is largest first, so the first match is the best-known town. */
  function findPlace(text) {
    const t = text.trim().toLowerCase().replace(/\s+/g, ' ').replace(/\s*,\s*/, ', ');
    if (!t) return null;
    const list = getPlaces();
    return list.find(function (p) { return p.key === t; }) ||
      list.find(function (p) { return p.name.toLowerCase() === t; }) ||
      list.find(function (p) { return p.key.indexOf(t) === 0; }) || null;
  }

  function labelFor(lat, lon) {
    let best = null;
    let bestMiles = Infinity;
    getPlaces().forEach(function (p) {
      if (Math.abs(p.lat - lat) > 2.5 || Math.abs(p.lon - lon) > 3.5) return;
      const d = B.milesBetween(lat, lon, p.lat, p.lon);
      if (d < bestMiles) { bestMiles = d; best = p; }
    });
    if (!best) return 'Farm at ' + lat.toFixed(1) + '°N, ' + Math.abs(lon).toFixed(1) + '°W';
    const town = best.name + ', ' + best.state;
    if (bestMiles < 4) return town;
    if (bestMiles < 60) return 'Near ' + town;
    return whole.format(Math.round(bestMiles / 5) * 5) + ' miles from ' + town;
  }

  /* ---------- routing ---------- */

  function routeName() {
    const hash = location.hash.replace(/^#\/?/, '');
    return hash === 'farm' || hash === 'plan' ? hash : 'intro';
  }

  function route() {
    const name = routeName();
    if (name === 'plan' && !hasLocation()) {
      location.replace('#/farm');
      setError('where', 'Pin your farm first.');
      return;
    }
    show(name);
  }

  function show(name) {
    ['intro', 'farm', 'plan'].forEach(function (n) {
      const screen = $('screen-' + n);
      const on = n === name;
      if (on && screen.hidden && !firstShow) {
        screen.classList.add('is-entering');
        screen.addEventListener('animationend', function () { screen.classList.remove('is-entering'); }, { once: true });
      }
      screen.hidden = !on;
    });
    document.querySelectorAll('.steps a[href="#/plan"]').forEach(function (a) {
      if (hasLocation()) a.removeAttribute('aria-disabled'); else a.setAttribute('aria-disabled', 'true');
    });
    if (name === 'farm') enterFarm();
    if (name === 'plan') enterPlan();
    if (!firstShow) {
      window.scrollTo(0, 0);
      const title = $('screen-' + name).querySelector('h1');
      if (title) title.focus({ preventScroll: true });
    }
    firstShow = false;
  }

  /* ---------- screen 2: the farm form ---------- */

  function paintRange(input) {
    const min = Number(input.min);
    const max = Number(input.max);
    const v = Math.min(max, Math.max(min, Number(input.value)));
    input.style.setProperty('--fill', ((v - min) / (max - min)) * 100 + '%');
  }

  function setError(key, text) {
    const node = $(key + '-error');
    const input = $(key);
    node.textContent = '';
    node.hidden = !text;
    if (text) {
      node.appendChild(icon('alert'));
      node.appendChild(make('span', null, text));
      input.setAttribute('aria-invalid', 'true');
    } else {
      input.removeAttribute('aria-invalid');
    }
  }

  function cropValue() {
    const f = state.farm;
    return f.acres * f.yield * f.price;
  }

  function syncForm() {
    const f = state.farm;
    $('where').value = f.label;
    document.querySelectorAll('input[name="crop"]').forEach(function (r) { r.checked = r.value === f.crop; });
    $('acres').value = f.acres;
    $('acres-range').value = f.acres;
    $('yield').value = f.yield;
    $('price').value = f.price.toFixed(2);
    $('budget').value = f.budget;
    $('budget-range').value = f.budget;
    $('stability').value = f.lean;
    $('stability-out').textContent = LEAN[f.lean - 1].label;
    ['acres-range', 'budget-range', 'stability'].forEach(function (id) { paintRange($(id)); });
    renderWhere();
    renderCropValue();
  }

  function renderCropValue() {
    const v = cropValue();
    $('crop-value').textContent = isFinite(v) && v > 0 ? dollars(v) : '—';
  }

  function renderWhere() {
    const f = state.farm;
    const out = $('where-out');
    out.hidden = !hasLocation();
    if (hasLocation()) out.textContent = 'Station: ' + stationOf(f).city + ', ' + aboutMiles(f.miles);
  }

  function mapFarm() {
    const f = state.farm;
    return hasLocation() ? { lat: f.lat, lon: f.lon, label: f.label, station: stationOf(f) } : null;
  }

  function setLocation(lat, lon, label, animate) {
    const near = B.nearestStation(lat, lon);
    Object.assign(state.farm, { lat: lat, lon: lon, label: label, stationId: near.station.id, miles: near.miles });
    $('where').value = label;
    setError('where', '');
    renderWhere();
    if (map) map.setFarm(mapFarm(), animate);
    document.querySelectorAll('.steps a[href="#/plan"]').forEach(function (a) { a.removeAttribute('aria-disabled'); });
    save();
  }

  function resolveWhere() {
    const text = $('where').value;
    if (!text.trim()) return;
    if (hasLocation() && text === state.farm.label) return;
    const place = findPlace(text);
    if (!place) {
      setError('where', 'Town not found. Try a bigger one, or click the map.');
      return;
    }
    setLocation(place.lat, place.lon, place.name + ', ' + place.state, true);
  }

  function enterFarm() {
    if (!map) {
      const names = B.stations.map(function (s) { return s.city; }).sort();
      $('station-count').textContent = names.length + ' station cities';
      $('station-names').textContent = names.join(' \u00b7 ');
      map = B.createMap($('map'), {
        onPick: function (p) { setLocation(p.lat, p.lon, labelFor(p.lat, p.lon), true); }
      });
      if (hasLocation()) map.setFarm(mapFarm(), false);
    }
  }

  function numberFrom(input) {
    const v = input.valueAsNumber;
    return isFinite(v) ? v : NaN;
  }

  function validateFarm() {
    const f = state.farm;
    let first = null;
    function check(key, ok, text) {
      setError(key, ok ? '' : text);
      if (!ok && !first) first = key;
    }
    check('where', hasLocation(), 'Pin your farm first.');
    check('acres', f.acres > 0, 'Enter acres.');
    check('yield', f.yield > 0, 'Enter a yield.');
    check('price', f.price > 0, 'Enter a price.');
    check('budget', f.budget >= 0, 'Enter a budget, or 0.');
    if (first) $(first).focus();
    return !first;
  }

  function bindFarm() {
    const where = $('where');
    where.addEventListener('input', function () {
      setError('where', '');
      const list = $('places');
      list.textContent = '';
      suggest(where.value).forEach(function (p) {
        const option = document.createElement('option');
        option.value = p.name + ', ' + p.state;
        list.appendChild(option);
      });
      // Picking a suggestion fills the field with an exact town.
      const exact = getPlaces().find(function (p) { return p.key === where.value.trim().toLowerCase(); });
      if (exact && where.value.indexOf(',') > 0) resolveWhere();
    });
    where.addEventListener('change', resolveWhere);
    where.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); resolveWhere(); }
    });

    document.querySelectorAll('input[name="crop"]').forEach(function (r) {
      r.addEventListener('change', function () {
        const f = state.farm;
        f.crop = r.value;
        const crop = B.crops[f.crop];
        if (!state.touched.yield) f.yield = crop.yield;
        if (!state.touched.price) f.price = crop.price;
        syncForm();
        save();
      });
    });

    function pair(numberId, rangeId, key) {
      const number = $(numberId);
      const range = $(rangeId);
      number.addEventListener('input', function () {
        const v = numberFrom(number);
        state.farm[key] = v;
        if (isFinite(v)) { range.value = v; paintRange(range); setError(numberId, ''); }
        renderCropValue();
        save();
      });
      range.addEventListener('input', function () {
        state.farm[key] = Number(range.value);
        number.value = range.value;
        paintRange(range);
        setError(numberId, '');
        renderCropValue();
        save();
      });
    }
    pair('acres', 'acres-range', 'acres');
    pair('budget', 'budget-range', 'budget');

    $('yield').addEventListener('input', function () {
      state.farm.yield = numberFrom($('yield'));
      state.touched.yield = true;
      setError('yield', '');
      renderCropValue();
      save();
    });
    $('price').addEventListener('input', function () {
      state.farm.price = numberFrom($('price'));
      state.touched.price = true;
      setError('price', '');
      renderCropValue();
      save();
    });

    $('stability').addEventListener('input', function () {
      state.farm.lean = Number($('stability').value);
      $('stability-out').textContent = LEAN[state.farm.lean - 1].label;
      paintRange($('stability'));
      save();
    });

    $('farm-form').addEventListener('submit', function (e) {
      e.preventDefault();
      if (validateFarm()) location.hash = '#/plan';
    });
  }

  /* ---------- screen 3: the plan ---------- */

  function legOf(ticket) {
    const side = M.sideOf(ticket.market, ticket.side);
    return { payout: side.payout, price: side.price, contracts: ticket.contracts };
  }

  function priceOf(ticket) { return M.sideOf(ticket.market, ticket.side).price; }

  function roundUpNice(v) {
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    const f = v / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 3 ? 3 : f <= 5 ? 5 : f <= 7 ? 7 : 10) * p;
  }

  /* How far one hedge's slider runs, from what the adviser says it could take. */
  function measure(ticket) {
    const top = B.advisor.ceiling(state.revenue, ticket.market, ticket.side);
    ticket.adds = top.contracts === 0;
    ticket.max = roundUpNice(Math.max(5000, top.contracts * 2, ticket.contracts * 1.2));
  }

  function costOf(tickets) {
    let cost = 0;
    tickets.forEach(function (t) { if (t.on) cost += t.contracts * priceOf(t); });
    return cost;
  }

  /* Ask the adviser (advisor.js, a placeholder model) what to hedge and how
   * much to put into each of the ticked markets. */
  function recommendPlan() {
    const on = state.tickets.filter(function (t) { return t.on; });
    const advice = B.advisor.suggest(state.revenue, on.map(function (t) {
      return Object.assign({}, t.market, { side: t.sideChosen ? t.side : null });
    }), { budget: state.farm.budget, stability: LEAN[state.farm.lean - 1].value });
    on.forEach(function (t, i) {
      t.side = advice.picks[i].side;
      t.contracts = advice.picks[i].contracts;
    });
    state.tickets.forEach(function (t) { if (!t.on) t.contracts = 0; measure(t); });
    state.custom = false;
    state.trimmed = advice.trimmed;
  }

  /* A fixed shuffle, so the sample harvests read as a run of years and the
   * same farm always shows the same run. */
  function shuffled(list, seed) {
    const a = list.slice();
    let s = seed >>> 0;
    for (let i = a.length - 1; i > 0; i--) {
      s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
      const j = s % (i + 1);
      const tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function enterPlan() {
    const f = state.farm;
    const station = stationOf(f);
    if (!plot) plot = B.createPlot($('plot'));
    B.source.scenario({ crop: f.crop, station: station, miles: f.miles }).then(function (scenario) {
      const crop = B.crops[f.crop];
      state.scenario = scenario;
      state.revenue = M.farmIncome(scenario.farmShock, {
        acres: f.acres, price: f.price, yield: f.yield,
        yieldSd: crop.spread * f.yield
      });
      state.base = M.summary(state.revenue);
      state.harvests = shuffled(M.representativeSeasons(state.revenue, scenario.markets.map(function (m) { return m.payoutYes; }), HARVESTS), 2027);
      state.tickets = scenario.markets.map(function (m) {
        return {
          market: m,
          on: !!m.preselect,
          side: M.hedgeSide(state.revenue, m),
          sideChosen: false, contracts: 0, max: 5000, adds: false, refs: null
        };
      });
      recommendPlan();
      renderTickets();
      updatePlan(true);
    });
  }

  function verdict(points) {
    const chip = make('span', 'verdict');
    let name = 'equal';
    let text = 'Fair price';
    if (points >= 2) { name = 'check'; text = 'Cheap by ' + points; }
    else if (points <= -2) { name = 'alert'; text = 'Pricey by ' + Math.abs(points); }
    chip.appendChild(icon(name));
    chip.appendChild(make('span', null, text));
    return chip;
  }

  function renderTickets() {
    const list = $('tickets');
    list.textContent = '';
    state.tickets.forEach(function (t) {
      const m = t.market;
      const side = M.sideOf(m, t.side);
      const sideWord = t.side === 'yes' ? 'Yes' : 'No';
      const li = make('li', 'ticket' + (t.on ? ' is-on' : ''));

      const pick = make('label', 'pick');
      const box = document.createElement('input');
      box.type = 'checkbox';
      box.checked = t.on;
      box.setAttribute('aria-label', 'Hedge with ' + m.name);
      const boxMark = make('span', 'box');
      boxMark.appendChild(icon('check'));
      pick.appendChild(box);
      pick.appendChild(boxMark);
      li.appendChild(pick);
      box.addEventListener('change', function () { togglePick(t, box.checked); });

      const body = make('div', 'ticket-body');
      const top = make('div', 'ticket-top');
      top.appendChild(make('span', 'ticket-name', m.name));
      const meta = make('span', 'ticket-meta');
      top.appendChild(meta);
      body.appendChild(top);
      body.appendChild(make('p', 'ticket-q', m.question));
      if (m.caveat) {
        const caveat = make('p', 'ticket-flag');
        caveat.appendChild(icon('info'));
        caveat.appendChild(make('span', null, m.caveat));
        body.appendChild(caveat);
      }
      t.refs = { meta: meta };

      if (!t.on) {
        const prices = make('div', 'ticket-prices');
        prices.appendChild(make('span', 'price-yes', 'Yes ' + m.yesCents + '¢'));
        prices.appendChild(make('span', 'price-no', 'No ' + m.noCents + '¢'));
        const add = make('button', 'btn btn-quiet', 'Add');
        add.type = 'button';
        add.setAttribute('aria-label', 'Hedge with ' + m.name);
        add.addEventListener('click', function () { togglePick(t, true); });
        prices.appendChild(add);
        body.appendChild(prices);
        li.appendChild(body);
        list.appendChild(li);
        return;
      }

      const controls = make('div', 'ticket-controls');
      const sides = make('div', 'sides');
      sides.setAttribute('role', 'group');
      sides.setAttribute('aria-label', m.name + ' side to buy');
      [['yes', 'Yes', m.yesCents], ['no', 'No', m.noCents]].forEach(function (s) {
        const b = make('button', 'side side-' + s[0]);
        b.type = 'button';
        b.setAttribute('aria-pressed', t.side === s[0] ? 'true' : 'false');
        b.appendChild(make('span', 'side-word', s[1]));
        b.appendChild(make('span', 'side-price', s[2] + '¢'));
        b.addEventListener('click', function () { chooseSide(t, s[0]); });
        sides.appendChild(b);
      });
      controls.appendChild(sides);

      // How much money goes into this hedge: typed in dollars, or dragged.
      const qty = make('div', 'qty');
      const field = make('span', 'field');
      field.appendChild(make('span', 'unit unit-lead', '$'));
      const amount = document.createElement('input');
      amount.type = 'number';
      amount.min = 0;
      amount.step = 100;
      amount.inputMode = 'numeric';
      amount.value = Math.round(t.contracts * side.price);
      amount.setAttribute('aria-label', 'Dollars into ' + m.name);
      field.appendChild(amount);
      qty.appendChild(field);
      const range = document.createElement('input');
      range.type = 'range';
      range.min = 0;
      range.max = t.max;
      range.step = B.advisor.lot;
      range.value = t.contracts;
      range.setAttribute('aria-label', 'Dollars into ' + m.name + ', slider');
      qty.appendChild(range);
      controls.appendChild(qty);
      body.appendChild(controls);

      const why = make('p', 'ticket-why');
      why.appendChild(document.createTextNode('Model ' + percent(M.chance(side)) + ' '));
      why.appendChild(verdict(Math.round(M.chance(side) * 100) - Math.round(side.price * 100)));
      body.appendChild(why);

      if (t.adds) {
        const flag = make('p', 'ticket-flag');
        flag.appendChild(icon('alert'));
        flag.appendChild(make('span', null, sideWord + ' adds swing. Try ' + (t.side === 'yes' ? 'No' : 'Yes') + '.'));
        body.appendChild(flag);
      }
      li.appendChild(body);
      list.appendChild(li);
      paintRange(range);

      amount.addEventListener('input', function () {
        const v = numberFrom(amount);
        t.contracts = isFinite(v) && v > 0 ? Math.round(v / side.price / B.advisor.lot) * B.advisor.lot : 0;
        if (t.contracts > Number(range.max)) { t.max = roundUpNice(t.contracts * 1.2); range.max = t.max; }
        range.value = t.contracts;
        paintRange(range);
        state.custom = true;
        updatePlan(false);
      });
      // Contracts come in hundreds, so settle the field on what the money buys.
      amount.addEventListener('change', function () { amount.value = Math.round(t.contracts * side.price); });
      range.addEventListener('input', function () {
        t.contracts = Number(range.value);
        amount.value = Math.round(t.contracts * side.price);
        paintRange(range);
        state.custom = true;
        updatePlan(false);
      });
    });
  }

  /* Choosing which hedges are in the plan, or which side of one to buy, asks
   * the adviser to size the whole mix again inside the budget. Amounts typed
   * or dragged afterwards stand until the next such choice. */
  function togglePick(ticket, on) {
    ticket.on = on;
    if (!on) ticket.sideChosen = false;
    recommendPlan();
    renderTickets();
    updatePlan(false);
  }

  function chooseSide(ticket, side) {
    if (ticket.side === side) return;
    ticket.side = side;
    ticket.sideChosen = true;
    recommendPlan();
    renderTickets();
    updatePlan(false);
  }

  function trimToBudget() {
    const cost = costOf(state.tickets);
    if (cost <= 0) return;
    const f = state.farm.budget / cost;
    state.tickets.forEach(function (t) { if (t.on) t.contracts = Math.floor((t.contracts * f) / B.advisor.lot) * B.advisor.lot; });
    state.custom = true;
    renderTickets();
    updatePlan(false);
  }

  function row(cells, head) {
    const tr = make('tr');
    cells.forEach(function (c, i) {
      const cell = make(i === 0 || head ? 'th' : 'td');
      if (head) cell.scope = 'col'; else if (i === 0) cell.scope = 'row';
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

  /* Revenue by harvest: the sample harvests along the bottom, dollars up the
   * side, one line without a hedge and one with the plan. */
  function chartSpec() {
    const picks = state.harvests;
    return {
      ariaLabel: 'Revenue over ' + picks.length + ' sample harvests, without a hedge and with your plan. Arrow keys read values.',
      base: { label: 'Without', values: picks.map(function (i) { return state.revenue[i]; }) },
      plan: {
        label: 'With plan',
        values: function () { return state.inGraph.length ? picks.map(function (i) { return state.planArr[i]; }) : null; }
      },
      money: moneyShort,
      worst: function (v) { return 'Worst ' + moneyShort(v); },
      tip: function (i, base, plan) {
        const rows = [{ key: 'base', value: money(base[i]), label: 'without' }];
        if (plan) rows.push({ key: 'plan', value: money(plan[i]), label: 'with plan' });
        return { title: 'Harvest ' + (i + 1), rows: rows };
      }
    };
  }

  function renderBins() {
    const picks = state.harvests;
    fill('bins-head', [['Harvest', 'Without', 'With plan']], true);
    fill('bins-body', picks.map(function (s, i) {
      return [String(i + 1), money(state.revenue[s]), money(state.planArr[s])];
    }));
  }

  /* Everything that follows from the amounts. `full` redraws the chart frame;
   * otherwise only the plan's line moves. */
  function updatePlan(full) {
    const f = state.farm;
    const active = state.tickets.filter(function (t) { return t.on && t.contracts > 0; });
    const chosen = state.tickets.filter(function (t) { return t.on; });
    state.inGraph = active.map(function (t) { return t.market.name; });
    state.planArr = M.planIncome(state.revenue, active.map(legOf));
    state.plan = M.summary(state.planArr);
    const a = state.base;
    const b = state.plan;
    const cost = costOf(state.tickets);
    const station = stationOf(f);
    const crop = B.crops[f.crop];
    const hedging = active.length > 0;

    state.tickets.forEach(function (t) {
      t.refs.meta.textContent = t.on ? whole.format(t.contracts) + ' contracts' : 'Not in plan';
    });

    // The advice, in dollars per hedge.
    $('plan-title').textContent = hedging ? 'Hedge ' + dollars(cost) : 'No hedge yet';
    $('plan-lede').textContent = !hedging
      ? (chosen.length ? 'Raise an amount to see the effect.' : 'Tick a hedge to start.')
      : (state.custom ? 'Your mix: ' : 'Suggested: ') + active.map(function (t) {
        return dollars(t.contracts * priceOf(t)) + ' in ' + t.market.name;
      }).join(' · ');
    let effect = '';
    if (hedging) {
      effect = b.sd < a.sd
        ? Math.round((1 - b.sd / a.sd) * 100) + '% steadier. Bad harvest ' + signedMoney(b.bad - a.bad) + '. Average ' + signedMoney(b.mean - a.mean) + '.'
        : 'This mix adds swing. Check the sides.';
    }
    $('plan-effect').textContent = effect;
    $('plan-effect').hidden = !effect;
    $('plan-result').textContent = hedging ? effect : 'Nothing in the plan yet.';
    $('farm-line').textContent = whole.format(f.acres) + ' ac ' + crop.label.toLowerCase() + ' · ' + f.label + ' · ' + station.city + ' station';

    fill('analysis-head', [['', 'Without', 'With plan', 'Change']], true);
    fill('analysis-body', [
      ['Average harvest', money(a.mean), money(b.mean), hedging ? signedMoney(b.mean - a.mean) : '—'],
      ['Swing', '±' + money(a.sd), '±' + money(b.sd), hedging ? signedPercent(b.sd / a.sd - 1) : '—'],
      ['Bad harvest (1 in 20)', money(a.bad), money(b.bad), hedging ? signedMoney(b.bad - a.bad) : '—'],
      ['Cost', '$0', dollars(cost), hedging ? percent(cost / cropValue(), 1) + ' of crop' : '—']
    ]);

    // The order
    const over = cost > f.budget + 0.5;
    $('meter').classList.toggle('is-over', over);
    $('meter-fill').style.transform = 'scaleX(' + (f.budget > 0 ? Math.min(1, cost / f.budget) : cost > 0 ? 1 : 0) + ')';
    const line = $('budget-line');
    line.textContent = '';
    if (over) {
      line.appendChild(icon('alert'));
      line.appendChild(make('strong', null, 'Over budget by ' + dollars(cost - f.budget) + '.'));
      const trim = make('button', 'link', 'Trim');
      trim.type = 'button';
      trim.addEventListener('click', trimToBudget);
      line.appendChild(trim);
    } else {
      line.appendChild(make('span', null, dollars(cost) + ' of ' + dollars(f.budget)));
    }
    const lines = $('order-lines');
    lines.textContent = '';
    if (!hedging) lines.appendChild(make('li', 'order-empty', 'Nothing yet.'));
    active.forEach(function (t) {
      const price = priceOf(t);
      const li = make('li');
      li.appendChild(make('span', null, whole.format(t.contracts) + ' ' + (t.side === 'yes' ? 'Yes' : 'No') + ' · ' + t.market.name + ' · ' + Math.round(price * 100) + '¢'));
      li.appendChild(make('span', null, dollars(t.contracts * price)));
      lines.appendChild(li);
    });
    $('order-total').textContent = dollars(cost);
    $('send-order').disabled = !(B.source.ordersConnected && hedging);

    const stateLine = $('plan-state');
    stateLine.textContent = '';
    if (state.custom) {
      stateLine.appendChild(make('span', null, 'Edited. '));
      const back = make('button', 'link', 'Reset');
      back.type = 'button';
      back.addEventListener('click', function () {
        recommendPlan();
        renderTickets();
        updatePlan(false);
      });
      stateLine.appendChild(back);
    } else {
      stateLine.textContent = !chosen.length ? 'None picked' : state.trimmed ? 'Trimmed to budget' : 'Sized for you';
    }

    const toggle = $('table-toggle');
    toggle.setAttribute('aria-pressed', state.tableView ? 'true' : 'false');
    toggle.textContent = state.tableView ? 'Chart' : 'Table';
    $('plot').hidden = state.tableView;
    $('legend').hidden = state.tableView;
    $('legend-plan').hidden = !hedging;
    $('bins').hidden = !state.tableView;
    if (state.tableView) renderBins();
    else if (full) plot.render(chartSpec());
    else plot.refresh();
  }

  /* ---------- start ---------- */

  function start() {
    restore();
    bindFarm();
    syncForm();
    $('table-toggle').addEventListener('click', function () {
      state.tableView = !state.tableView;
      updatePlan(true);
    });
    window.addEventListener('hashchange', route);
    route();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})(window.FarmerJoe = window.FarmerJoe || {});
