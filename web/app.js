// Saloon Poker - story mode shell: main menu, the town, the clothing shop,
// and handing over to the poker table (table.js) when you enter a saloon.

import { frontChar } from '/characters.js';
import { townBackdrop, saloonFront, shopFront, padlock, medal } from '/scenes.js';
import { createTable } from '/table.js';

const STAGE_W = 1400, STAGE_H = 800;
const $ = (sel) => document.querySelector(sel);
const money = (n) => '$' + Number(n).toLocaleString('en-US');
const ordinal = (n) => n + (['th', 'st', 'nd', 'rd'][n % 100 > 10 && n % 100 < 14 ? 0 : n % 10] || 'th');

let state = null;  // what the server knows: { profile, saloons, items, session }

// --------------------------------------------------------------- plumbing
function fit() {
  const s = Math.min(innerWidth / STAGE_W, innerHeight / STAGE_H);
  const x = (innerWidth - STAGE_W * s) / 2, y = (innerHeight - STAGE_H * s) / 2;
  $('#stage').style.transform = `translate(${x}px, ${y}px) scale(${s})`;
}
addEventListener('resize', fit);
fit();

async function api(path, body) {
  try {
    const options = body === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    };
    const res = await fetch(path, options);
    const data = await res.json();
    if (data && data.saloons) state = data;
    return data;
  } catch {
    return null;
  }
}

function show(name) {
  for (const id of ['menu', 'town', 'shop', 'table']) $(`#screen-${id}`).hidden = id !== name;
}

// -------------------------------------------------------------- main menu
let chosen = 'cowboy';

function choose(kind) {
  chosen = kind;
  document.querySelectorAll('.avatar').forEach((a) => a.classList.toggle('selected', a.dataset.avatar === kind));
}

function showMenu() {
  const saved = !!state.profile;
  $('#btn-continue').hidden = !saved;
  $('#btn-begin').classList.toggle('btn-plain', saved);
  $('#btn-begin').classList.toggle('btn-next', !saved);
  $('#btn-begin .lbl').textContent = saved ? 'New journey' : 'Begin journey';
  $('#create').hidden = true;
  show('menu');
}

function setupMenu() {
  $('#menu-scene').innerHTML = townBackdrop();
  const heroes = [
    ['left:70px', { base: 'cowboy', hat: 'trail', shirt: 'denim', neck: 'bandana_red' }],
    ['right:70px', { base: 'cowgirl', hat: 'prairie', shirt: 'rose' }],
  ];
  for (const [side, look] of heroes) {
    const hero = document.createElement('div');
    hero.className = 'menu-char';
    hero.style.cssText = side;
    hero.dataset.mood = 'happy';
    hero.innerHTML = frontChar(look);
    $('#screen-menu').insertBefore(hero, $('.menu-title'));
  }
  document.querySelectorAll('.avatar').forEach((a) => {
    a.querySelector('.avatar-art').innerHTML = frontChar({
      base: a.dataset.avatar, ...(a.dataset.avatar === 'cowgirl'
        ? { hat: 'prairie', shirt: 'rose' } : { hat: 'trail', shirt: 'denim', neck: 'bandana_red' }),
    });
    a.addEventListener('click', () => choose(a.dataset.avatar));
  });

  $('#btn-continue').addEventListener('click', showTown);
  $('#btn-begin').addEventListener('click', () => {
    $('#create-warn').hidden = !state.profile;
    $('#name-input').value = state.profile ? state.profile.name : '';
    choose(state.profile ? state.profile.base : 'cowboy');
    $('#create').hidden = false;
    $('#name-input').focus();
  });
  $('#btn-create-cancel').addEventListener('click', () => { $('#create').hidden = true; });
  const create = async () => {
    await api('/api/journey', { name: $('#name-input').value.trim(), base: chosen });
    if (state.profile) showTown();
  };
  $('#btn-create').addEventListener('click', create);
  $('#name-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') create(); });
}

// ------------------------------------------------------------------- town
// Far row: the clothing shop, then saloons 1-5 left to right. The trail turns
// at the end of the street, so the near row runs right to left: 6 up to 10.
const FAR = { w: 200, h: 208, top: 150, left: (i) => 40 + i * 222 };
const NEAR = { w: 240, h: 250, top: 440, left: (i) => 50 + i * 265 };
let hintTimer = 0;

function hint(text) {
  const box = $('#town-hint');
  box.textContent = text;
  box.classList.add('show');
  clearTimeout(hintTimer);
  hintTimer = setTimeout(() => box.classList.remove('show'), 2600);
}

function building(className, row, index, art, label) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = `building ${className}`;
  b.setAttribute('aria-label', label);
  b.style.cssText = `left:${row.left(index)}px;top:${row.top}px;width:${row.w}px;height:${row.h}px`;
  b.innerHTML = `<span class="b-art">${art}</span>`;
  $('#buildings').append(b);
  return b;
}

function showTown() {
  const prof = state.profile;
  if (!prof) return showMenu();
  $('#town-portrait').innerHTML = frontChar(prof.look);
  $('#town-name').textContent = prof.name;
  $('#town-money').textContent = money(prof.money);
  $('#saloon-panel').hidden = true;
  $('#buildings').replaceChildren();

  building('open shop', FAR, 0, shopFront(), 'Clothing shop').addEventListener('click', showShop);

  const next = state.saloons.find((s) => s.unlocked && s.best !== 1);
  for (const s of state.saloons) {
    const far = s.id <= 5;
    const b = building(s.unlocked ? 'open' : 'locked', far ? FAR : NEAR, far ? s.id : 10 - s.id,
      saloonFront(s.id, s.name, s.unlocked), `${s.name}, saloon ${s.id}${s.unlocked ? '' : ' (locked)'}`);
    if (!s.unlocked) {
      b.insertAdjacentHTML('beforeend', `<span class="b-lock">${padlock}</span>`);
      b.addEventListener('click', () => {
        b.classList.remove('nudge');
        void b.offsetWidth;
        b.classList.add('nudge');
        hint(`Locked. Win at the ${state.saloons[s.id - 2].name} first.`);
      });
      continue;
    }
    if (s.best && s.best <= s.prizes.length) b.insertAdjacentHTML('beforeend', `<span class="b-medal">${medal(s.best)}</span>`);
    if (next && next.id === s.id) b.insertAdjacentHTML('beforeend', '<span class="b-next">Play here</span>');
    b.addEventListener('click', () => openSaloon(s));
  }
  show('town');
}

function openSaloon(s) {
  $('#sp-name').textContent = s.name;
  $('#sp-info').textContent = `Saloon ${s.id} of ${state.saloons.length} · ${s.players} players · last one standing wins`;
  $('#sp-cast').innerHTML = s.cast.map((c) => `<div class="portrait" data-mood="neutral">${frontChar(c.look)}</div>`).join('');
  $('#sp-cast').querySelectorAll('.portrait').forEach((p, i) => { p.title = s.cast[i].name; });
  $('#sp-prizes').innerHTML = s.prizes.map((amount, i) => {
    const earned = s.best && s.best <= i + 1;
    return `<div class="prize${earned ? ' earned' : ''}">${medal(i + 1)}<b>${money(amount)}</b>
      <small>${earned ? 'collected' : `${ordinal(i + 1)} place`}</small></div>`;
  }).join('');
  $('#sp-best').textContent = !s.best ? "You haven't played here yet."
    : s.best === 1 ? "You've won here. Playing again is just for fun."
      : `Your best finish here: ${ordinal(s.best)}. Win to open the next saloon.`;
  $('#btn-enter').onclick = () => enterSaloon(s.id);
  $('#saloon-panel').hidden = false;
}

async function enterSaloon(id) {
  const res = await api('/api/enter', { saloon: id });
  if (!res || !res.ok) return;
  $('#saloon-panel').hidden = true;
  show('table');
  table.open(res.sid, true);
}

// ------------------------------------------------------------------- shop
const SLOTS = [['hat', 'Hats'], ['facial', 'Whiskers'], ['shirt', 'Shirts'], ['neck', 'Neckwear'], ['eyewear', 'Eyewear']];
let slot = 'hat';

function showShop() {
  const prof = state.profile;
  $('#shop-money').textContent = money(prof.money);
  $('#shop-char').innerHTML = frontChar(prof.look);

  $('#shop-tabs').innerHTML = SLOTS.map(([id, label]) =>
    `<button type="button" data-slot="${id}" class="${id === slot ? 'on' : ''}">${label}</button>`).join('');
  $('#shop-tabs').querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
    slot = b.dataset.slot;
    showShop();
  }));

  const box = $('#shop-items');
  box.replaceChildren();
  box.classList.toggle('low', slot === 'shirt' || slot === 'neck');
  for (const item of state.items.filter((i) => i.slot === slot)) {
    const wearing = prof.look[slot] === item.id;
    const owned = item.price === 0 || prof.owned.includes(`${slot}:${item.id}`);
    const look = { ...prof.look, [slot]: item.id };
    const tile = document.createElement('div');
    tile.className = `item${wearing ? ' wearing' : ''}`;
    tile.innerHTML = `<div class="item-art" data-mood="neutral">${frontChar(look)}</div><div class="item-name"></div>
      <button type="button" class="act"></button>`;
    tile.querySelector('.item-name').textContent = item.name;
    const act = tile.querySelector('.act');
    if (wearing) {
      act.textContent = 'Wearing';
      act.disabled = true;
    } else if (owned) {
      act.textContent = 'Wear';
      act.addEventListener('click', async () => { await api('/api/equip', { slot, item: item.id }); showShop(); });
    } else {
      act.textContent = money(item.price);
      act.classList.add('buy');
      act.disabled = prof.money < item.price;
      act.title = act.disabled ? 'Not enough money yet' : 'Buy';
      act.addEventListener('click', async () => { await api('/api/buy', { slot, item: item.id }); showShop(); });
    }
    // Try it on in the mirror while pointing at it.
    tile.addEventListener('mouseenter', () => { $('#shop-char').innerHTML = frontChar(look); });
    tile.addEventListener('mouseleave', () => { $('#shop-char').innerHTML = frontChar(state.profile.look); });
    box.append(tile);
  }
  show('shop');
}

// ------------------------------------------------------------------ table
const table = createTable(async (where) => {
  await api('/api/state');
  if (where === 'menu') showMenu();
  else if (where && where.again) enterSaloon(where.again);
  else showTown();
});

// ------------------------------------------------------------------- boot
$('#town-scene').innerHTML = townBackdrop();
$('#screen-town').insertAdjacentHTML('beforeend', '<div class="town-hint" id="town-hint"></div>');
$('#btn-town-menu').addEventListener('click', showMenu);
$('#btn-shop-back').addEventListener('click', showTown);
$('#btn-sp-close').addEventListener('click', () => { $('#saloon-panel').hidden = true; });
setupMenu();

(async () => {
  while (!(await api('/api/state'))) await new Promise((r) => setTimeout(r, 1000));
  if (state.session && state.profile) {   // a game was in progress: sit back down
    show('table');
    table.open(state.session.sid, false);
  } else {
    showMenu();
  }
})();
