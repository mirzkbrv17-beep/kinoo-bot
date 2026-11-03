(() => {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) { tg.ready(); tg.expand(); try { tg.setHeaderColor('#000000'); tg.setBackgroundColor('#0b0b0d'); } catch (e) {} }
  const lang = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code || 'uz').startsWith('ru') ? 'ru' : 'uz';
  const L = {
    uz: {all: 'Hammasi', movie: 'Kinolar', series: 'Seriallar', cartoon: 'Multfilmlar', vip: 'VIP', search: 'Qidirish…', empty: 'Hech narsa topilmadi', watch: '▶️ Botda ko\'rish', trailer: '🎞 Treyler', fav: '🤍 Sevimli', unfav: '❤️ Sevimlidan olib tashlash', vipOnly: '👑 VIP kontent', err: 'Xatolik. Qayta urinib ko\'ring.', start: 'Avval botda /start bosing.', sub: 'Botdan foydalanish uchun kanallarga obuna bo\'ling:', code: 'Kod', year: 'Yil', country: 'Davlat', genre: 'Janr', dur: 'Davomiyligi', age: 'Yosh', views: 'Ko\'rishlar', seasons: 'Fasllar', eps: 'Qismlar', min: 'daq', banned: 'Kirish yopilgan.'},
    ru: {all: 'Все', movie: 'Фильмы', series: 'Сериалы', cartoon: 'Мультфильмы', vip: 'VIP', search: 'Поиск…', empty: 'Ничего не найдено', watch: '▶️ Смотреть в боте', trailer: '🎞 Трейлер', fav: '🤍 В избранное', unfav: '❤️ Убрать из избранного', vipOnly: '👑 VIP контент', err: 'Ошибка. Повторите.', start: 'Сначала нажмите /start в боте.', sub: 'Подпишитесь на каналы, чтобы пользоваться ботом:', code: 'Код', year: 'Год', country: 'Страна', genre: 'Жанр', dur: 'Длительность', age: 'Возраст', views: 'Просмотры', seasons: 'Сезоны', eps: 'Серии', min: 'мин', banned: 'Доступ закрыт.'}
  }[lang];
  const $ = (id) => document.getElementById(id);
  const state = {kind: 'all', genre: null, q: '', page: 0, more: true, busy: false, bot: ''};
  $('q').placeholder = L.search;

  async function api(path, opt = {}) {
    const r = await fetch(path, Object.assign({}, opt, {headers: Object.assign({'X-Init-Data': (tg && tg.initData) || ''}, opt.headers || {})}));
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { const e = new Error(j.error || 'error'); e.data = j; throw e; }
    return j;
  }
  function showError(e) {
    const m = $('msg'); m.textContent = '';
    if (e.message === 'start_bot') m.textContent = L.start;
    else if (e.message === 'banned') m.textContent = L.banned;
    else if (e.message === 'subscribe') {
      m.textContent = L.sub + '\n';
      ((e.data && e.data.channels) || []).forEach(c => {
        const a = document.createElement('a'); a.textContent = '📢 ' + c.title; a.href = '#'; a.style.cssText = 'display:block;color:#e50914;margin:6px';
        a.onclick = (ev) => { ev.preventDefault(); tg && tg.openTelegramLink ? tg.openTelegramLink(c.url) : window.open(c.url); };
        m.appendChild(a);
      });
    } else m.textContent = L.err;
  }
  function chips(box, items, cur, onPick) {
    box.innerHTML = '';
    items.forEach(([key, label]) => {
      const b = document.createElement('button'); b.className = 'chip' + (String(cur) === String(key) ? ' on' : ''); b.textContent = label;
      b.onclick = () => onPick(key); box.appendChild(b);
    });
  }
  function drawKinds() { chips($('kinds'), ['all', 'movie', 'series', 'cartoon', 'vip'].map(k => [k, L[k]]), state.kind, k => { state.kind = k; reload(); drawKinds(); }); }
  function drawGenres(list) { chips($('genres'), [[null, L.all]].concat(list.map(g => [g.id, g.name])), state.genre, g => { state.genre = g || null; reload(); drawGenres(list); }); }

  function card(it) {
    const d = document.createElement('div'); d.className = 'card';
    if (it.poster) { const i = document.createElement('img'); i.loading = 'lazy'; i.src = it.poster; i.alt = ''; d.appendChild(i); }
    else { const p = document.createElement('div'); p.className = 'ph'; p.textContent = (it.title || '?')[0]; d.appendChild(p); }
    if (it.locked) { const l = document.createElement('div'); l.className = 'lock'; d.appendChild(l); }
    if (it.vip) { const v = document.createElement('span'); v.className = 'badge vip'; v.textContent = '👑'; d.appendChild(v); }
    if (it.imdb) { const r = document.createElement('span'); r.className = 'badge rate'; r.textContent = '⭐ ' + it.imdb; d.appendChild(r); }
    const c = document.createElement('div'); c.className = 'cap'; c.textContent = it.title + (it.year ? ' (' + it.year + ')' : ''); d.appendChild(c);
    d.onclick = () => openItem(it);
    return d;
  }
  async function load() {
    if (state.busy || !state.more) return;
    state.busy = true;
    try {
      const p = new URLSearchParams({kind: state.kind, page: state.page, q: state.q});
      if (state.genre) p.set('genre', state.genre);
      const r = await api('/api/catalog?' + p);
      r.items.forEach(it => $('grid').appendChild(card(it)));
      state.more = r.more; state.page++;
      $('msg').textContent = $('grid').children.length ? '' : L.empty;
    } catch (e) { showError(e); state.more = false; }
    state.busy = false;
  }
  function reload() { $('grid').innerHTML = ''; state.page = 0; state.more = true; $('msg').textContent = ''; load(); }

  async function openItem(it) {
    const box = $('detail'); box.innerHTML = '';
    $('sheet').classList.remove('hidden');
    try {
      const d = await api('/api/item/' + it.type + '/' + it.id);
      const hero = document.createElement('div'); hero.className = 'hero';
      if (d.poster) { const i = document.createElement('img'); i.src = d.poster; hero.appendChild(i); }
      else { const p = document.createElement('div'); p.className = 'ph'; p.textContent = d.title[0]; hero.appendChild(p); }
      const info = document.createElement('div');
      const h = document.createElement('h2'); h.textContent = d.title; info.appendChild(h);
      const meta = document.createElement('div'); meta.className = 'meta';
      const rows = [[L.code, d.code], [L.year, d.year], [L.country, d.country], [L.genre, d.genre], [L.dur, d.duration ? d.duration + ' ' + L.min : null], [L.age, d.age], ['IMDb', d.imdb ? '⭐ ' + d.imdb : null], [L.views, d.views], [L.seasons, d.seasons], [L.eps, d.episodes]];
      rows.forEach(([k, v]) => { if (v) { const r = document.createElement('div'); r.textContent = k + ': ' + v; meta.appendChild(r); } });
      if (d.vip) { const r = document.createElement('div'); r.textContent = L.vipOnly; meta.appendChild(r); }
      info.appendChild(meta); hero.appendChild(info); box.appendChild(hero);
      if (d.description) { const p = document.createElement('p'); p.className = 'desc'; p.textContent = d.description; box.appendChild(p); }
      const acts = document.createElement('div'); acts.className = 'actions';
      const w = document.createElement('button'); w.className = 'btn main'; w.textContent = L.watch;
      w.onclick = () => { const url = 'https://t.me/' + state.bot + '?start=m_' + d.code; tg && tg.openTelegramLink ? (tg.openTelegramLink(url), tg.close()) : window.open(url); };
      acts.appendChild(w);
      if (d.type === 'movie') {
        const f = document.createElement('button'); f.className = 'btn'; f.textContent = d.fav ? L.unfav : L.fav;
        f.onclick = async () => { try { const r = await api('/api/fav/' + d.id, {method: 'POST'}); f.textContent = r.fav ? L.unfav : L.fav; } catch (e) { showError(e); } };
        acts.appendChild(f);
      }
      if (d.trailer) { const t = document.createElement('button'); t.className = 'btn'; t.textContent = L.trailer; t.onclick = () => tg && tg.openLink ? tg.openLink(d.trailer) : window.open(d.trailer); acts.appendChild(t); }
      box.appendChild(acts);
    } catch (e) { box.textContent = L.err; }
  }
  $('close').onclick = () => $('sheet').classList.add('hidden');
  $('sheet').onclick = (e) => { if (e.target === $('sheet')) $('sheet').classList.add('hidden'); };
  let timer; $('q').oninput = (e) => { clearTimeout(timer); timer = setTimeout(() => { state.q = e.target.value.trim(); reload(); }, 350); };
  new IntersectionObserver(es => { if (es[0].isIntersecting) load(); }, {rootMargin: '300px'}).observe($('sentinel'));

  (async () => {
    drawKinds();
    try {
      const me = await api('/api/me'); state.bot = me.bot;
      drawGenres(await api('/api/genres'));
    } catch (e) { showError(e); return; }
    load();
  })();
})();
