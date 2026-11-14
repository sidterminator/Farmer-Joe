/* Screen logic: the three screens, the farm form, the plan and the order.
 * Data comes only through FarmerJoe.source (sample-data.js); sums go through
 * FarmerJoe.model. */
(function (B) {
  'use strict';

  const M = B.model;
  const STORE_KEY = 'farmerjoe.farm';
  const MINUS = '−';
  const EASE_OUT = 'cubic-bezier(0.23, 1, 0.32, 1)';
  const LOT = 100;
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

  function reducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
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
  function plural(n, word) { return whole.format(n) + ' ' + word + (n === 1 ? '' : 's'); }
  /* "Near Champaign, IL" -> "near Champaign, IL"; a bare town -> "at Champaign, IL". */
  function placePhrase(label) {
    if (/^Near /.test(label)) return 'near ' + label.slice(5);
    if (/^\d/.test(label)) return label;
    if (/^Farm at /.test(label)) return label.slice(5);
    return 'at ' + label;
  }
  function aboutMiles(miles) {
    if (miles < 10) return 'under 10 miles away';
    return 'about ' + whole.format(Math.round(miles / 5) * 5) + ' miles away';
  }

  /* ---------- state ---------- */

  const state = {
    farm: {
      lat: null, lon: null, label: '', stationId: null, miles: 0,
      crop: 'corn', acres: 300, yield: 200, price: 4.5, yieldSd: null,
      worries: ['heat', 'drought'], budget: 15000, lean: 4
    },
    touched: { yield: false, price: false },
    scenario: null,
    revenue: null,
    base: null,
    planArr: null,
    plan: null,
    lo: 0,
    hi: 1,
    tickets: [],
    inGraph: [],
    custom: false,
    trimmed: false,
    tableView: false,
    live: { status: 'idle', event: null, stationId: null }
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
      setError('where', 'Put your farm on the map first. Click the map, or type a town.');
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
    document.querySelectorAll('input[name="worry"]').forEach(function (c) { c.checked = f.worries.indexOf(c.value) >= 0; });
    $('budget').value = f.budget;
    $('budget-range').value = f.budget;
    $('stability').value = f.lean;
    $('stability-out').textContent = LEAN[f.lean - 1].label;
    ['acres-range', 'budget-range', 'stability'].forEach(function (id) { paintRange($(id)); });
    renderWhere(false);
    renderCropValue();
  }

  function renderCropValue() {
    const v = cropValue();
    $('crop-value').textContent = isFinite(v) && v > 0 ? dollars(v) : '—';
  }

  function renderWhere(animate) {
    const f = state.farm;
    const out = $('where-out');
    out.hidden = !hasLocation();
    if (!hasLocation()) return;
    const station = stationOf(f);
    $('where-stamp').textContent = f.label;
    $('where-station').textContent = 'Nearest station: ' + station.city + ', ' + aboutMiles(f.miles) + '.';
    if (animate && $('where-stamp').animate) {
      // The place is stamped onto the tag just after the pin lands.
      $('where-stamp').animate(reducedMotion()
        ? [{ opacity: 0 }, { opacity: 1 }]
        : [{ transform: 'rotate(-2deg) scale(1.16)', opacity: 0 }, { transform: 'rotate(-2deg) scale(1)', opacity: 1 }],
      { duration: 180, delay: reducedMotion() ? 0 : 230, easing: EASE_OUT, fill: 'backwards' });
    }
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
    renderWhere(animate);
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
      setError('where', 'No town by that name in the list. Try a larger town nearby, or click the map.');
      return;
    }
    setLocation(place.lat, place.lon, place.name + ', ' + place.state, true);
  }

  function enterFarm() {
    if (!map) {
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

  /* Accepts a CSV with a year column and a yield column (bushels per acre).
   * Optional acres and price columns fill those answers too. */
  function parseSeasonsCsv(text) {
    const lines = text.split(/\r?\n/).map(function (l) { return l.trim(); }).filter(Boolean);
    if (!lines.length) return { yields: [] };
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
    if (col.year < 0 || col.yield < 0) return { yields: [] };
    const byYear = new Map();
    let acres = null;
    let price = null;
    for (let i = start; i < lines.length; i++) {
      const c = cells(lines[i]);
      const year = Number(c[col.year]);
      const value = Number(c[col.yield]);
      if (!Number.isInteger(year) || year < 1950 || year > 2100 || !(value > 0 && value < 500)) continue;
      byYear.set(year, value);
      if (col.acres >= 0 && Number(c[col.acres]) > 0) acres = Number(c[col.acres]);
      if (col.price >= 0 && Number(c[col.price]) > 0) price = Number(c[col.price]);
    }
    return { yields: Array.from(byYear.values()), acres: acres, price: price };
  }

  function importHistory(file) {
    const note = $('yield-note');
    const reader = new FileReader();
    reader.onerror = function () { setError('yield', 'Could not read ' + file.name + '. Try importing it again.'); };
    reader.onload = function () {
      const parsed = parseSeasonsCsv(String(reader.result));
      if (!parsed.yields.length) {
        setError('yield', 'No seasons found in ' + file.name + '. It needs a year column and a yield column in bushels per acre.');
        return;
      }
      const f = state.farm;
      f.yield = Math.round(M.mean(parsed.yields));
      f.yieldSd = parsed.yields.length >= 3 ? M.sd(parsed.yields) : null;
      if (parsed.acres) f.acres = parsed.acres;
      if (parsed.price) f.price = parsed.price;
      state.touched.yield = true;
      if (parsed.price) state.touched.price = true;
      setError('yield', '');
      syncForm();
      note.hidden = false;
      note.textContent = 'From ' + plural(parsed.yields.length, 'season') + ' in ' + file.name +
        (f.yieldSd !== null ? ': normal ' + f.yield + ', swing ±' + Math.round(f.yieldSd) + ' bushels.' : ': normal ' + f.yield + '. Three or more seasons would also set the swing.');
      save();
    };
    reader.readAsText(file);
  }

  function validateFarm() {
    const f = state.farm;
    let first = null;
    function check(key, ok, text) {
      setError(key, ok ? '' : text);
      if (!ok && !first) first = key;
    }
    check('where', hasLocation(), 'Put your farm on the map first. Click the map, or type a town.');
    check('acres', f.acres > 0, 'Enter the acres you farm, such as 300.');
    check('yield', f.yield > 0, 'Enter a normal yield in bushels per acre, such as 200.');
    check('price', f.price > 0, 'Enter the price you expect per bushel, such as 4.50.');
    check('budget', f.budget >= 0, 'Enter the most you would spend, or 0.');
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
        if (!state.touched.yield) { f.yield = crop.yield; f.yieldSd = null; }
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
      state.farm.yieldSd = null;
      state.touched.yield = true;
      $('yield-note').hidden = true;
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

    document.querySelectorAll('input[name="worry"]').forEach(function (c) {
      c.addEventListener('change', function () {
        state.farm.worries = Array.from(document.querySelectorAll('input[name="worry"]:checked')).map(function (x) { return x.value; });
        save();
      });
    });

    $('stability').addEventListener('input', function () {
      state.farm.lean = Number($('stability').value);
      $('stability-out').textContent = LEAN[state.farm.lean - 1].label;
      paintRange($('stability'));
      save();
    });

    $('import-btn').addEventListener('click', function () { $('file-input').click(); });
    $('file-input').addEventListener('change', function (e) {
      if (e.target.files && e.target.files[0]) importHistory(e.target.files[0]);
      e.target.value = '';
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

  function roundUpNice(v) {
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    const f = v / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 3 ? 3 : f <= 5 ? 5 : f <= 7 ? 7 : 10) * p;
  }

  /* The steadiest amount of one contract on its own, used to scale its slider. */
  function measure(ticket) {
    const side = M.sideOf(ticket.market, ticket.side);
    ticket.steady = M.recommend(state.revenue, [side], { budget: -1, stability: 1, lot: LOT }).steadiest[0];
    ticket.adds = ticket.steady === 0;
    ticket.max = roundUpNice(Math.max(5000, ticket.steady * 2, ticket.contracts * 1.2));
  }

  function costOf(tickets) {
    let cost = 0;
    tickets.forEach(function (t) { if (t.on) cost += t.contracts * M.sideOf(t.market, t.side).price; });
    return cost;
  }

  function recommendPlan() {
    const on = state.tickets.filter(function (t) { return t.on; });
    on.forEach(function (t) { if (!t.sideChosen) t.side = M.hedgeSide(state.revenue, t.market); });
    const rec = M.recommend(state.revenue, on.map(function (t) { return M.sideOf(t.market, t.side); }),
      { budget: state.farm.budget, stability: LEAN[state.farm.lean - 1].value, lot: LOT });
    on.forEach(function (t, i) { t.contracts = rec.contracts[i]; });
    state.tickets.forEach(function (t) { if (!t.on) t.contracts = 0; measure(t); });
    state.custom = false;
    state.trimmed = rec.trimmed;
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
        yieldSd: f.yieldSd !== null ? f.yieldSd : crop.spread * f.yield
      });
      state.base = M.summary(state.revenue);
      const span = Math.max(state.base.sd * 3.3, state.base.mean * 0.02);
      state.lo = state.base.mean - span;
      state.hi = state.base.mean + span;
      state.tickets = scenario.markets.map(function (m) {
        return {
          market: m,
          on: f.worries.length ? f.worries.indexOf(m.worry) >= 0 : true,
          side: M.hedgeSide(state.revenue, m),
          sideChosen: false, contracts: 0, steady: 0, max: 5000, adds: false, refs: null
        };
      });
      recommendPlan();
      renderTickets();
      updatePlan(true);
      loadLive(false);
    });
  }

  function verdict(points) {
    const chip = make('span', 'verdict');
    let name = 'equal';
    let text = 'About fair';
    if (points >= 2) { name = 'check'; text = 'Cheap by ' + points + ' points'; }
    else if (points <= -2) { name = 'alert'; text = 'Expensive by ' + Math.abs(points) + ' points'; }
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
      box.setAttribute('aria-label', 'Include ' + m.name + ' in the plan');
      const boxMark = make('span', 'box');
      boxMark.appendChild(icon('check'));
      pick.appendChild(box);
      pick.appendChild(boxMark);
      li.appendChild(pick);

      const body = make('div', 'ticket-body');
      const top = make('div', 'ticket-top');
      top.appendChild(make('span', 'ticket-name', m.name));
      const cost = make('span', 'ticket-cost');
      top.appendChild(cost);
      body.appendChild(top);
      body.appendChild(make('p', 'ticket-q', m.question + '. ' + m.settles + '.'));
      if (m.caveat) {
        const caveat = make('p', 'ticket-flag');
        caveat.appendChild(icon('info'));
        caveat.appendChild(make('span', null, m.caveat));
        body.appendChild(caveat);
      }

      box.addEventListener('change', function () { togglePick(t, box.checked); });
      if (!t.on) {
        const prices = make('div', 'ticket-prices');
        prices.appendChild(make('span', 'price-yes', 'Yes ' + m.yesCents + '\u00a2'));
        prices.appendChild(make('span', 'price-no', 'No ' + m.noCents + '\u00a2'));
        const add = make('button', 'btn btn-quiet', 'Add to plan');
        add.type = 'button';
        add.setAttribute('aria-label', 'Add ' + m.name + ' to the plan');
        add.addEventListener('click', function () { togglePick(t, true); });
        prices.appendChild(add);
        body.appendChild(prices);
        li.appendChild(body);
        list.appendChild(li);
        t.refs = { cost: cost };
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

      const qty = make('div', 'qty');
      const field = make('span', 'field');
      const number = document.createElement('input');
      number.type = 'number';
      number.min = 0;
      number.step = LOT;
      number.inputMode = 'numeric';
      number.value = t.contracts;
      number.setAttribute('aria-label', m.name + ' contracts');
      field.appendChild(number);
      qty.appendChild(field);
      const range = document.createElement('input');
      range.type = 'range';
      range.min = 0;
      range.max = t.max;
      range.step = LOT;
      range.value = t.contracts;
      range.setAttribute('aria-label', m.name + ' contracts, slider');
      qty.appendChild(range);
      controls.appendChild(qty);
      body.appendChild(controls);

      const why = make('p', 'ticket-why');
      why.appendChild(make('strong', null, sideWord + ' pays $1'));
      why.appendChild(document.createTextNode(' when ' + (t.side === 'yes' ? m.yesPaysWhen : m.noPaysWhen) + '. Model chance ' + percent(M.chance(side)) + '. '));
      why.appendChild(verdict(Math.round(M.chance(side) * 100) - Math.round(side.price * 100)));
      body.appendChild(why);

      if (t.adds) {
        const flag = make('p', 'ticket-flag');
        flag.appendChild(icon('alert'));
        flag.appendChild(make('span', null, sideWord + ' pays in the seasons this farm already earns more, so it adds swing. ' + (t.side === 'yes' ? 'No' : 'Yes') + ' is the side that steadies it.'));
        body.appendChild(flag);
      }
      li.appendChild(body);
      list.appendChild(li);

      t.refs = { cost: cost };
      paintRange(range);

      number.addEventListener('input', function () {
        const v = numberFrom(number);
        t.contracts = isFinite(v) && v > 0 ? Math.round(v) : 0;
        if (t.contracts > Number(range.max)) { t.max = roundUpNice(t.contracts * 1.2); range.max = t.max; }
        range.value = t.contracts;
        paintRange(range);
        state.custom = true;
        updatePlan(false);
      });
      range.addEventListener('input', function () {
        t.contracts = Number(range.value);
        number.value = t.contracts;
        paintRange(range);
        state.custom = true;
        updatePlan(false);
      });
    });
  }

  /* Choosing which markets are in the plan, or which side of one to buy,
   * re-sizes the whole combination inside the budget. Amounts typed or
   * dragged afterwards stand until the next such choice. */
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
    state.tickets.forEach(function (t) { if (t.on) t.contracts = Math.floor((t.contracts * f) / LOT) * LOT; });
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

  function incomeTicks(lo, hi) {
    const raw = (hi - lo) / 6;
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / p;
    const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
    const ticks = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push({ value: v, label: moneyShort(v) });
    return ticks;
  }

  function chartSpec() {
    return {
      ariaLabel: 'Season income across ' + whole.format(state.revenue.length) + ' simulated seasons: without protection above, with your plan below. Use the left and right arrow keys to read values.',
      lo: state.lo,
      hi: state.hi,
      headroom: 1.45,
      bands: [
        {
          key: 'base',
          label: 'Without protection',
          values: function (bins, lo, hi) { return M.histogram(state.revenue, lo, hi, bins); },
          get mark() { return { value: state.base.bad, label: '1 in 20: ' + money(state.base.bad) }; }
        },
        {
          key: 'plan',
          get label() { return 'With your plan: ' + (state.inGraph.length ? state.inGraph.join(' + ') : 'nothing selected'); },
          values: function (bins, lo, hi) { return M.histogram(state.planArr, lo, hi, bins); },
          get mark() { return { value: state.plan.bad, label: '1 in 20: ' + money(state.plan.bad) }; }
        }
      ],
      xTicks: incomeTicks,
      tip: function (k, shares, lo, hi) {
        const w = (hi - lo) / shares[0].length;
        return {
          title: moneyShort(lo + k * w) + ' to ' + moneyShort(lo + (k + 1) * w),
          rows: [
            { key: 'base', value: percent(shares[0][k], 1), label: 'of seasons without protection' },
            { key: 'plan', value: percent(shares[1][k], 1), label: 'of seasons with your plan' }
          ]
        };
      }
    };
  }

  function renderBins() {
    const GROUPS = 12;
    const w = (state.hi - state.lo) / GROUPS;
    const a = M.histogram(state.revenue, state.lo, state.hi, GROUPS);
    const b = M.histogram(state.planArr, state.lo, state.hi, GROUPS);
    fill('bins-head', [['Season income', 'Without protection', 'With your plan']], true);
    const rows = [];
    for (let k = 0; k < GROUPS; k++) {
      rows.push([moneyShort(state.lo + k * w) + ' to ' + moneyShort(state.lo + (k + 1) * w), percent(a[k], 1), percent(b[k], 1)]);
    }
    fill('bins-body', rows);
  }

  /* Everything that follows from the quantities. `full` redraws the chart
   * frame; otherwise only its columns move. */
  function updatePlan(full) {
    const f = state.farm;
    const active = state.tickets.filter(function (t) { return t.on && t.contracts > 0; });
    const chosen = state.tickets.filter(function (t) { return t.on; }).map(function (t) { return t.market.name; });
    state.inGraph = active.map(function (t) { return t.market.name; });
    state.planArr = M.planIncome(state.revenue, active.map(legOf));
    state.plan = M.summary(state.planArr);
    const a = state.base;
    const b = state.plan;
    const cost = costOf(state.tickets);
    const station = stationOf(f);
    const crop = B.crops[f.crop];

    state.tickets.forEach(function (t) {
      const price = M.sideOf(t.market, t.side).price;
      t.refs.cost.textContent = t.on ? dollars(t.contracts * price) : 'Not in plan';
    });

    $('plan-title').textContent = active.length
      ? 'Your plan: ' + dollars(cost) + ' across ' + plural(active.length, 'market')
      : 'No protection in the plan';
    let lede;
    if (!active.length) {
      lede = chosen.length
        ? 'The markets you picked have no contracts in them yet. Raise an amount on the right to see what it does to your season.'
        : 'Tick the markets you want on the right. The graph shows the combination you pick.';
    } else if (b.sd < a.sd) {
      lede = 'It cuts the typical swing in your season income from ±' + money(a.sd) + ' to ±' + money(b.sd) +
        (b.bad >= a.bad ? ' and lifts a 1-in-20 bad season by ' + money(b.bad - a.bad) + '.' : ', but a 1-in-20 bad season comes in ' + money(a.bad - b.bad) + ' lower.');
    } else {
      lede = 'This mix adds swing to your season income instead of removing it. Check the side on each contract.';
    }
    $('plan-lede').textContent = lede;
    $('plan-result').textContent = !active.length ? 'Nothing in the plan yet.'
      : 'Swing ±' + money(state.base.sd) + ' to ±' + money(state.plan.sd) + '. Bad season ' + signedMoney(state.plan.bad - state.base.bad) + '. Cost ' + dollars(cost) + '.';
    $('farm-line').textContent = whole.format(f.acres) + ' acres of ' + crop.label.toLowerCase() + ' ' + placePhrase(f.label) +
      '. Worth ' + dollars(cropValue()) + ' in a normal year. Nearest station: ' + station.city + ', ' + aboutMiles(f.miles) + '.';

    const hedging = active.length > 0;
    fill('analysis-head', [['', 'Without protection', 'With your plan', 'Change']], true);
    fill('analysis-body', [
      ['Average season', money(a.mean), money(b.mean), hedging ? signedMoney(b.mean - a.mean) : '—'],
      ['Typical swing', '±' + money(a.sd), '±' + money(b.sd), hedging ? signedPercent(b.sd / a.sd - 1) : '—'],
      ['1-in-20 bad season', money(a.bad), money(b.bad), hedging ? signedMoney(b.bad - a.bad) : '—'],
      ['Cost of protection', '$0', dollars(cost), hedging ? percent(cost / cropValue(), 1) + ' of the crop' : '—']
    ]);

    // The order
    const over = cost > f.budget + 0.5;
    $('meter').classList.toggle('is-over', over);
    $('meter-fill').style.transform = 'scaleX(' + (f.budget > 0 ? Math.min(1, cost / f.budget) : cost > 0 ? 1 : 0) + ')';
    const line = $('budget-line');
    line.textContent = '';
    if (over) {
      line.appendChild(icon('alert'));
      line.appendChild(make('strong', null, 'Over your ' + dollars(f.budget) + ' limit by ' + dollars(cost - f.budget) + '.'));
      const trim = make('button', 'link', 'Trim to fit');
      trim.type = 'button';
      trim.addEventListener('click', trimToBudget);
      line.appendChild(trim);
    } else {
      line.appendChild(make('span', null, dollars(cost) + ' of your ' + dollars(f.budget) + ' limit.'));
    }
    const lines = $('order-lines');
    lines.textContent = '';
    if (!active.length) lines.appendChild(make('li', 'order-empty', 'Nothing in the order yet.'));
    active.forEach(function (t) {
      const price = M.sideOf(t.market, t.side).price;
      const li = make('li');
      li.appendChild(make('span', null, whole.format(t.contracts) + ' ' + (t.side === 'yes' ? 'Yes' : 'No') + ' on ' + t.market.name + ' at ' + Math.round(price * 100) + '¢'));
      li.appendChild(make('span', null, dollars(t.contracts * price)));
      lines.appendChild(li);
    });
    $('order-total').textContent = dollars(cost);
    $('send-order').disabled = !(B.source.ordersConnected && active.length);

    const stateLine = $('plan-state');
    stateLine.textContent = '';
    if (state.custom) {
      stateLine.appendChild(make('span', null, 'You changed the amounts. '));
      const back = make('button', 'link', 'Back to the recommended amounts');
      back.type = 'button';
      back.addEventListener('click', function () {
        recommendPlan();
        renderTickets();
        updatePlan(false);
      });
      stateLine.appendChild(back);
    } else {
      stateLine.textContent = !chosen.length ? 'No markets picked'
        : 'Sized for ' + chosen.join(' + ') + (state.trimmed ? ', trimmed to your limit' : '');
    }

    const toggle = $('table-toggle');
    toggle.setAttribute('aria-pressed', state.tableView ? 'true' : 'false');
    toggle.textContent = state.tableView ? 'Chart view' : 'Table view';
    $('plot').hidden = state.tableView;
    $('bins').hidden = !state.tableView;
    if (state.tableView) renderBins();
    else if (full) plot.render(chartSpec());
    else plot.refresh();
  }

  /* ---------- live Kalshi markets ---------- */

  function loadLive(force) {
    const station = stationOf(state.farm);
    if (!force && state.live.stationId === station.id && state.live.status === 'ok') { renderLive(); return; }
    state.live = { status: 'loading', event: null, stationId: station.id };
    renderLive();
    B.source.liveMarkets(station).then(function (event) {
      if (state.live.stationId !== station.id) return;
      state.live.event = event;
      state.live.status = event && event.markets.length ? 'ok' : 'empty';
      renderLive();
    }).catch(function () {
      if (state.live.stationId !== station.id) return;
      state.live.status = 'error';
      renderLive();
    });
  }

  function priceCell(cents, kind) {
    return cents === null ? make('span', 'price-none', 'No offer') : make('span', 'price-' + kind, cents + '¢');
  }

  function renderLive() {
    const station = stationOf(state.farm);
    const status = $('live-status');
    const body = $('live-body');
    status.textContent = '';
    body.textContent = '';
    const live = state.live;

    if (live.status === 'loading') {
      status.textContent = 'Asking Kalshi…';
      const sk = make('div', 'skeleton');
      sk.setAttribute('aria-hidden', 'true');
      sk.appendChild(make('span'));
      sk.appendChild(make('span'));
      sk.appendChild(make('span'));
      body.appendChild(sk);
      return;
    }

    if (live.status === 'ok') {
      const e = live.event;
      const time = e.fetchedAt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
      const quoted = e.markets.some(function (m) { return m.yesCents !== null || m.noCents !== null; });
      const tail = 'Kalshi lists each month’s market shortly before the month, so the July plan above runs on sample prices.';
      status.appendChild(make('span', 'live-dot'));
      body.appendChild(make('p', 'live-title', e.title));

      if (!quoted) {
        // Listed but nobody is quoting it: one row says so instead of a table of blanks.
        status.appendChild(make('span', null, 'Listed, not quoted, ' + time));
        const line = make('p', 'live-row');
        line.appendChild(make('span', null, plural(e.markets.length, 'strike') + ' listed, ' +
          e.markets[0].label.toLowerCase() + ' to ' + e.markets[e.markets.length - 1].label.toLowerCase()));
        line.appendChild(make('strong', null, 'No offers right now'));
        body.appendChild(line);
        body.appendChild(make('p', 'live-note', 'This market is really listed for ' + station.city + ', the station nearest your farm (' + e.ticker + '), on Kalshi’s demo exchange. ' + tail));
        const again = make('button', 'btn btn-quiet', 'Check again');
        again.type = 'button';
        again.addEventListener('click', function () { loadLive(true); });
        body.appendChild(again);
        return;
      }

      status.appendChild(make('span', null, 'Live from Kalshi’s demo exchange, ' + time));
      const table = make('table', 'live-table');
      const thead = make('thead');
      thead.appendChild(row(['Pays if rainfall is', 'Yes', 'No'], true));
      const tbody = make('tbody');
      e.markets.forEach(function (m) {
        const tr = make('tr');
        tr.appendChild(make('td', null, m.label));
        const yes = make('td');
        yes.appendChild(priceCell(m.yesCents, 'yes'));
        const no = make('td');
        no.appendChild(priceCell(m.noCents, 'no'));
        tr.appendChild(yes);
        tr.appendChild(no);
        tbody.appendChild(tr);
      });
      table.appendChild(thead);
      table.appendChild(tbody);
      body.appendChild(table);
      body.appendChild(make('p', 'live-note', 'These are the real open prices for ' + station.city + ', the station nearest your farm (' + e.ticker + '). ' + tail));
      return;
    }

    const fail = make('div', 'live-fail');
    if (live.status === 'empty') {
      status.textContent = 'Nothing open';
      fail.appendChild(make('p', null, 'Kalshi has no open monthly rain market for ' + station.city + ' right now. The plan above does not depend on it.'));
    } else {
      status.textContent = 'Not connected';
      fail.appendChild(make('p', null, 'Kalshi could not be reached. The plan above does not depend on it.'));
    }
    const retry = make('button', 'btn btn-quiet');
    retry.type = 'button';
    retry.appendChild(icon('retry'));
    retry.appendChild(document.createTextNode('Try again'));
    retry.addEventListener('click', function () { loadLive(true); });
    fail.appendChild(retry);
    body.appendChild(fail);
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
