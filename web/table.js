// The poker table: seats up to nine players in a saloon and plays back the
// tournament.
//
// web.py records everything the engine does as a list of events, each with a
// snapshot of the table. This file fetches those events (long-polling) and
// plays them back one at a time, animating whatever changed between snapshots.

import { frontChar, backChar } from '/characters.js';
import { saloonInterior, medal } from '/scenes.js';

const ME = 0;
const POS = { pot: { x: 700, y: 420 }, deal: { x: 700, y: 330 } };
const CHIP_COLORS = ['#e0392b', '#2f6fd0', '#2f9e52', '#8e44c9', '#3a3442'];
const ROOM_HUES = [8, 150, 38, 200, 215, 285, 95, 230, 18, 348];

const $ = (sel) => document.querySelector(sel);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const money = (n) => '$' + Number(n).toLocaleString('en-US');
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const ordinal = (n) => n + (['th', 'st', 'nd', 'rd'][n % 100 > 10 && n % 100 < 14 ? 0 : n % 10] || 'th');

// ------------------------------------------------------------ seat layout
// Seats run clockwise from the human at the bottom: near-left (seen from
// behind), far-left corner, the far side of the table, far-right corner,
// near-right. Positions are stage pixels; x values are centres.
const TOP_X = { 1: [700], 2: [520, 880], 3: [450, 700, 950], 4: [400, 600, 800, 1000] };
const TOP_W = { 1: 170, 2: 160, 3: 160, 4: 150 };
const PLANS = {  // opponents -> [near seats per side, corner seats per side, far-side seats]
  1: [0, 0, 1], 2: [0, 0, 2], 3: [0, 0, 3], 4: [0, 0, 4], 5: [0, 1, 3], 6: [0, 1, 4], 7: [1, 1, 3], 8: [1, 1, 4],
};
const ME_SLOT = {
  view: 'back', bust: { x: 700, top: 566, w: 200, z: 4 },
  cards: { x: 700, y: 446 }, bet: { x: 872, y: 480 }, dealer: { x: 551, y: 521 },
  bubble: { x: 596, y: 628 }, stack: { x: 925, y: 650 },
};

function topSlot(x, count) {
  const w = TOP_W[count];
  return {
    view: 'front', bust: { x, top: Math.round(124 - 168 * (w / 200)), w, z: 1 },
    plaque: { x, top: 124 }, cards: { x, y: 186 }, bet: { x, y: 250 }, dealer: { x: x + 64, y: 214 },
    bubble: { x, y: 182 }, stack: { x, y: 148 },
  };
}
function cornerSlot(right) {
  const m = (v) => (right ? 1400 - v : v);
  return {
    view: 'front', bust: { x: m(222), top: 84, w: 140, z: 1 },
    plaque: { x: m(150), top: 218 }, cards: { x: m(322), y: 262 }, bet: { x: m(412), y: 298 },
    dealer: { x: m(288), y: 342 }, bubble: { x: m(322), y: 258 }, stack: { x: m(150), y: 242 },
  };
}
function nearSlot(right) {
  const m = (v) => (right ? 1400 - v : v);
  return {
    view: 'back', bust: { x: m(290), top: 546, w: 150, z: 4 },
    plaque: { x: m(122), top: 612, portrait: true }, cards: { x: m(376), y: 468 }, bet: { x: m(460), y: 430 },
    dealer: { x: m(300), y: 500 }, bubble: { x: m(376), y: 464 }, stack: { x: m(122), y: 636 },
  };
}
function layout(opponents) {
  const [near, corner, top] = PLANS[opponents];
  const slots = [ME_SLOT];
  if (near) slots.push(nearSlot(false));
  if (corner) slots.push(cornerSlot(false));
  TOP_X[top].forEach((x) => slots.push(topSlot(x, top)));
  if (corner) slots.push(cornerSlot(true));
  if (near) slots.push(nearSlot(true));
  return slots;
}

// ------------------------------------------------------------------ cards
function setFace(card, code) {
  card.dataset.code = code || '';
  card.classList.toggle('facedown', !code);
  if (!code) return;
  const rank = code[0] === 'T' ? '10' : code[0], suit = code[1];
  card.classList.toggle('red', suit === 'h' || suit === 'd');
  card.querySelector('.front').innerHTML =
    `<span class="rank${rank === '10' ? ' ten' : ''}">${rank}</span>` +
    `<svg class="pip" viewBox="0 0 100 100"><use href="#suit-${suit}"/></svg>` +
    `<svg class="big" viewBox="0 0 100 100"><use href="#suit-${suit}"/></svg>`;
}

function makeCard(code) {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = '<div class="card-inner"><div class="face front"></div><div class="face back"></div></div>';
  setFace(card, code);
  return card;
}

// Make `box` show `codes` (null = face down). New cards fly in from the middle,
// a face-down card that now has a code flips over. Returns how many were dealt.
function syncCards(box, codes, instant, order = 0) {
  while (box.children.length > codes.length) box.lastChild.remove();
  let dealt = 0;
  codes.forEach((code, i) => {
    let card = box.children[i];
    if (!card) {
      card = makeCard(code);
      box.append(card);
      if (!instant) {
        card.style.setProperty('--fx', `${POS.deal.x - box.offsetLeft - card.offsetLeft - card.offsetWidth / 2}px`);
        card.style.setProperty('--fy', `${POS.deal.y - box.offsetTop - card.offsetTop - card.offsetHeight / 2}px`);
        card.style.setProperty('--d', `${(order + dealt) * 55}ms`);
        card.classList.add('deal');
      }
      dealt++;
    } else if (card.dataset.code !== (code || '')) {
      setFace(card, code);
    }
  });
  return dealt;
}

function stackHTML(amount, bigBlind) {
  const n = clamp(Math.round(Math.log2(amount / bigBlind + 1)), 1, 6);
  let chips = '';
  for (let i = 0; i < n; i++) {
    chips += `<div class="chip" style="--c:${CHIP_COLORS[i % CHIP_COLORS.length]};bottom:${6 + i * 7}px"></div>`;
  }
  return `<div class="stack" style="height:${46 + (n - 1) * 7}px">${chips}</div>`;
}

// ------------------------------------------------------------------ table
// `onExit(where)` is called when the player leaves: 'town', 'menu', or
// { again: saloonId } to sit straight back down.
export function createTable(onExit) {
  const screen = $('#screen-table');
  const el = {
    board: $('#board'), pot: $('#pot'), banner: $('#banner'), dealer: $('#dealer'),
    raisebox: $('#raisebox'), slider: $('#slider'),
    result: $('#result'), victory: $('#victory'), leave: $('#leave-panel'),
  };
  const btn = Object.fromEntries(
    [...screen.querySelectorAll('.btn[data-act]')].map((b) => [b.dataset.act, b]));

  let sid = null;        // id of the tournament we are following
  let cursor = -1;       // index of the next event we want (-1: just the latest)
  let gen = 0;           // bumped whenever we switch tournament; stale work bails out
  let pending = [];      // events waiting to be played
  let pumping = false;
  let meta = null;       // saloon and seats of the tournament on screen
  let builtFor = null;
  let seats = [];
  let view = null;       // the last snapshot that was drawn
  let legal = null;      // legal actions while it is my turn
  let raiseTo = 0;
  let mode = 'wait';     // 'act' | 'wait' | 'over'
  let tempo = 1;         // playback speed; hands I'm not in run faster
  let showdown = null;   // hands shown at the current showdown

  class Stale extends Error {}
  async function pause(ms, g) {
    await sleep(ms * tempo);
    if (g !== gen) throw new Stale();
  }

  // ---------------------------------------------------------------- seats
  function add(className, style = {}) {
    const node = document.createElement('div');
    node.className = `seat-el ${className}`;
    for (const [k, v] of Object.entries(style)) node.style[k] = typeof v === 'number' && k !== 'zIndex' ? `${v}px` : v;
    screen.insertBefore(node, $('#fx'));
    return node;
  }

  function buildSeats() {
    screen.querySelectorAll('.seat-el').forEach((node) => node.remove());
    $('#room-scene').innerHTML = saloonInterior(ROOM_HUES[(meta.saloon.id - 1) % ROOM_HUES.length]);
    $('#hud-saloon').textContent = meta.saloon.name;
    const slots = layout(meta.seats.length - 1);
    seats = meta.seats.map((info, i) => {
      const slot = slots[i], me = i === ME, front = slot.view === 'front';
      const bust = add(`bust view-${slot.view}`, {
        left: slot.bust.x - slot.bust.w / 2, top: slot.bust.top, width: slot.bust.w,
        height: slot.bust.w * (front ? 1.15 : 1), zIndex: slot.bust.z,
      });
      bust.dataset.mood = 'neutral';
      bust.innerHTML = front ? frontChar(info.look) : backChar(info.look);

      const portrait = me || slot.plaque.portrait;
      const plaque = me
        ? add('plaque plaque-me')
        : add(`plaque small${portrait ? ' with-portrait' : ''}`, { left: slot.plaque.x - (portrait ? 91 : 75), top: slot.plaque.top });
      plaque.innerHTML = `${portrait ? '<div class="portrait" data-mood="neutral"></div>' : ''}
        <div class="plaque-text"><div class="name"></div><div class="chips"></div></div><div class="tag"></div>`;
      plaque.querySelector('.name').textContent = info.name;
      const face = plaque.querySelector('.portrait');
      if (face) face.innerHTML = frontChar(info.look);

      return {
        slot, bust, plaque, face,
        chips: plaque.querySelector('.chips'), tag: plaque.querySelector('.tag'),
        cards: add(`cards hole ${me ? 'me' : 'opp'}`, { left: slot.cards.x - (me ? 93 : 42), top: slot.cards.y }),
        bet: add(`bet${me ? '' : ' small'}`, { left: slot.bet.x, top: slot.bet.y }),
        bubble: add(`bubble${me ? ' me' : ''}`, { left: slot.bubble.x, top: slot.bubble.y }),
        handname: add(`handname${me ? ' me' : ''}`, { left: slot.bet.x, top: slot.bet.y + (me ? 12 : 12) }),
        shown: null, rolling: 0, timer: 0,
      };
    });
  }

  function setMood(i, mood) {
    seats[i].bust.dataset.mood = mood;
    if (seats[i].face) seats[i].face.dataset.mood = mood;
  }

  function setActive(who) {
    seats.forEach((seat, i) => seat.plaque.classList.toggle('active', i === who));
  }

  // Chip counts roll up/down instead of jumping.
  function setChips(seat, value, instant) {
    cancelAnimationFrame(seat.rolling);
    const from = seat.shown;
    if (instant || from === null || from === value) {
      seat.shown = value;
      seat.chips.textContent = money(value);
      return;
    }
    const t0 = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - t0) / 500);
      seat.shown = Math.round(from + (value - from) * t);
      seat.chips.textContent = money(seat.shown);
      if (t < 1) seat.rolling = requestAnimationFrame(step);
    };
    seat.rolling = requestAnimationFrame(step);
  }

  function setBet(seat, amount, bigBlind) {
    const box = seat.bet;
    if (amount > 0) {
      if (box.dataset.amount !== String(amount)) {
        box.innerHTML = `${stackHTML(amount, bigBlind)}<span class="amount">${money(amount)}</span>`;
        box.dataset.amount = amount;
      }
      box.classList.add('show');
    } else {
      box.classList.remove('show');
      box.dataset.amount = '';
    }
  }

  function fly(from, to, delay = 0, color = CHIP_COLORS[0]) {
    const chip = document.createElement('div');
    chip.className = 'fly';
    chip.innerHTML = `<div class="chip" style="--c:${color}"></div>`;
    chip.style.left = `${from.x}px`;
    chip.style.top = `${from.y}px`;
    $('#fx').append(chip);
    setTimeout(() => {
      chip.getBoundingClientRect();  // commit the start position before moving
      chip.style.left = `${to.x}px`;
      chip.style.top = `${to.y}px`;
      chip.style.opacity = 0;
    }, delay);
    setTimeout(() => chip.remove(), delay + 700);
  }

  function say(i, html, { loud = false, sticky = false } = {}) {
    const seat = seats[i];
    clearTimeout(seat.timer);
    seat.bubble.innerHTML = html;
    seat.bubble.classList.toggle('loud', loud);
    seat.bubble.classList.add('show');
    if (!sticky) seat.timer = setTimeout(() => seat.bubble.classList.remove('show'), 1900);
  }
  function hush(i) {
    clearTimeout(seats[i].timer);
    seats[i].bubble.classList.remove('show');
  }

  function actionLine(ev) {
    const p = ev.state.players[ev.who];
    switch (ev.kind) {
      case 'fold': return { text: 'Fold.' };
      case 'check': return { text: 'Check.' };
      case 'call':
        return p.allIn ? { text: 'Call - all in!', loud: true } : { text: `Call ${money(ev.toCall)}` };
      case 'raise':
        if (p.allIn) return { text: `All in! ${money(p.bet)}`, loud: true };
        return { text: `${ev.isBet ? 'Bet' : 'Raise to'} ${money(p.bet)}` };
      default: return { text: '...' };
    }
  }

  // -------------------------------------------------------- drawing state
  function clearHand() {
    el.board.replaceChildren();
    el.banner.classList.remove('show');
    showdown = null;
    seats.forEach((seat, i) => {
      seat.cards.replaceChildren();
      seat.handname.classList.remove('show', 'winner');
      hush(i);
      setMood(i, 'neutral');
    });
    setActive(null);
  }

  // Draw a snapshot. Returns what was newly dealt so the caller can wait for it.
  function render(s, prev, instant) {
    $('#hud-hand').textContent = `Hand ${Math.max(1, s.hand)} · Blinds ${money(s.blinds[0])} / ${money(s.blinds[1])}`;
    $('#hud-left').textContent = `${s.left} of ${s.players.length} players left`;

    const collected = !!prev && s.pot > prev.pot;
    let hole = 0;
    s.players.forEach((p, i) => {
      const seat = seats[i];
      if (p.out) {
        cancelAnimationFrame(seat.rolling);
        seat.shown = 0;
        seat.chips.textContent = 'Out';
      } else {
        setChips(seat, p.chips, instant);
      }
      if (!instant && collected && prev.players[i].bet > 0 && p.bet === 0) fly(seat.slot.bet, POS.pot);
      setBet(seat, p.bet, s.blinds[1]);
      hole += syncCards(seat.cards, p.cards, instant, hole);
      const dealt = p.cards.length > 0;
      seat.cards.classList.toggle('folded', dealt && p.folded);
      seat.cards.classList.toggle('shown', i !== ME && p.cards.some(Boolean));
      const folded = dealt && p.folded && !p.out;
      if (folded || p.allIn) seat.tag.textContent = folded ? 'Fold' : 'All-in';
      seat.tag.classList.toggle('fold', folded);
      seat.tag.classList.toggle('show', folded || p.allIn);
      seat.bust.classList.toggle('out', p.out);
      seat.plaque.classList.toggle('out', p.out);
    });

    const middle = s.pot + s.players.reduce((sum, p) => sum + p.bet, 0);
    if (middle > 0) $('#pot-amount').textContent = money(middle);
    el.pot.classList.toggle('show', middle > 0);

    const d = seats[s.button].slot.dealer;
    el.dealer.style.left = `${d.x}px`;
    el.dealer.style.top = `${d.y}px`;
    el.dealer.classList.toggle('off', s.hand === 0);

    const board = syncCards(el.board, s.board, instant);
    return { hole, board };
  }

  function showHands(hands) {
    showdown = hands;
    hands.forEach(({ seat, name }) => {
      const h = seats[seat].handname;
      h.innerHTML = '<span></span>';
      h.firstChild.textContent = name;
      h.classList.add('show');
    });
  }

  function finishHand(ev, s, instant) {
    const winners = ev.winners.map((w) => w.seat);
    const total = ev.winners.reduce((sum, w) => sum + w.amount, 0);
    const iWon = winners.includes(ME);
    setActive(null);
    seats.forEach((_, i) => hush(i));

    s.players.forEach((p, i) => {
      if (winners.includes(i)) setMood(i, 'happy');
      else if (p.out || (ev.showdown && p.cards.length && !p.folded)) setMood(i, 'sad');
    });

    if (ev.showdown && showdown) {
      const best = new Set(showdown.filter((h) => winners.includes(h.seat)).flatMap((h) => h.cards));
      const mark = (card, eligible) => {
        const wins = eligible && best.has(card.dataset.code);
        card.classList.toggle('win', wins);
        card.classList.toggle('dim', !wins);
      };
      [...el.board.children].forEach((c) => mark(c, true));
      seats.forEach((seat, i) => {
        [...seat.cards.children].forEach((c) => mark(c, winners.includes(i)));
        seat.handname.classList.toggle('winner', winners.includes(i));
      });
    }

    const first = (i) => meta.seats[i].name.split(' ')[0];
    const main = $('#banner-main'), sub = $('#banner-sub');
    el.banner.classList.toggle('mine', iWon && winners.length === 1);
    el.banner.classList.toggle('split', winners.length > 1);
    if (winners.length > 1) main.textContent = iWon ? 'You split the pot!' : 'Split pot';
    else if (iWon) main.textContent = `You win ${money(total)}!`;
    else main.textContent = `${first(winners[0])} wins ${money(total)}`;
    const gone = ev.busted.map((b) => b.seat).filter((i) => i !== ME).map((i) => meta.seats[i].name);
    sub.textContent = gone.length ? `${gone.join(' and ')} ${gone.length > 1 ? 'are' : 'is'} out!` : '';
    el.banner.classList.add('show');

    if (!instant) {
      ev.winners.forEach((w, n) => {
        for (let k = 0; k < 3; k++) fly(POS.pot, seats[w.seat].slot.stack, n * 120 + k * 90, CHIP_COLORS[k]);
      });
    }
  }

  function showResult(ev) {
    setMode('over');
    setActive(null);
    const { place, players, prize, fullPrize, unlocked, champion } = ev;
    const saloon = meta.saloon;
    if (champion) {
      $('#victory-char').innerHTML = frontChar(meta.seats[ME].look);
      $('#victory-text').textContent =
        `You beat every saloon in Dusty Gulch, ${meta.seats[ME].name}. The whole town tips its hat to you.`;
      $('#victory-prize').textContent = prize ? `+${money(prize)}` : '';
      const colors = ['#ffd84a', '#e0392b', '#2f6fd0', '#2f9e52', '#fff3d6'];
      $('#confetti').innerHTML = Array.from({ length: 46 }, (_, i) =>
        `<i style="left:${(i * 53) % 1400}px;background:${colors[i % 5]};animation-duration:${2.6 + (i % 7) * 0.4}s;animation-delay:${-(i % 9) * 0.5}s"></i>`).join('');
      el.victory.hidden = false;
      return;
    }
    $('#result-medal').innerHTML = place <= 3 && place < players ? medal(place) : '';
    $('#result-title').textContent = place === 1 ? 'You won!' : `You finished ${ordinal(place)}`;
    $('#result-sub').textContent = `out of ${players} players at the ${saloon.name}`;
    $('#result-prize').textContent = prize ? `+${money(prize)}` : '';
    let note;
    if (unlocked) note = 'The next saloon in town is now open!';
    else if (prize) note = place === 1 ? '' : 'Win here to open the next saloon.';
    else if (fullPrize) note = "You've already collected this prize here.";
    else if (saloon.prizes.length === 1) note = 'Win the heads-up to earn the prize.';
    else note = `Finish in the top ${saloon.prizes.length} to earn a prize.`;
    $('#result-note').textContent = note;
    el.result.hidden = false;
  }

  // ------------------------------------------------------------- controls
  function setMode(next) {
    mode = next;
    if (next !== 'act') {
      legal = null;
      Object.values(btn).forEach((b) => { b.disabled = true; });
      el.raisebox.classList.add('off');
      for (const id of ['#call-amt', '#raise-amt', '#allin-amt']) $(id).textContent = '';
      btn.call.querySelector('.lbl').textContent = 'Call';
    }
  }

  function setRaise(value) {
    if (!legal) return;
    const lo = legal.minRaiseTo, hi = legal.maxRaiseTo;
    raiseTo = clamp(Math.round(value), lo, hi);
    const fraction = hi > lo ? (raiseTo - lo) / (hi - lo) : 1;
    el.slider.value = Math.round(fraction * 1000);
    el.slider.style.setProperty('--fill', `${fraction * 100}%`);
    $('#raise-amt').textContent = money(raiseTo);
  }

  function enableControls(l) {
    setMode('act');
    legal = l;
    const me = view.players[ME];
    const canSize = l.canRaise && l.minRaiseTo < l.maxRaiseTo;

    btn.fold.disabled = l.canCheck;
    btn.check.disabled = !l.canCheck;
    btn.call.disabled = l.toCall === 0;
    btn.raise.disabled = !canSize;
    btn.allin.disabled = !l.canRaise;
    el.raisebox.classList.toggle('off', !canSize);

    $('#call-amt').textContent = l.toCall ? money(l.toCall) : '';
    btn.call.querySelector('.lbl').textContent = l.toCall && l.toCall >= me.chips ? 'Call all-in' : 'Call';
    $('#raise-lbl').textContent = l.currentBet === 0 ? 'Bet' : 'Raise to';
    $('#allin-amt').textContent = l.canRaise ? money(l.maxRaiseTo) : '';
    if (canSize) setRaise(l.minRaiseTo); else $('#raise-amt').textContent = '';
  }

  async function post(path, body) {
    try {
      const res = await fetch(path, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      return res.ok ? await res.json() : { ok: false };
    } catch {
      return { ok: false };
    }
  }

  // Something got out of step with the server: start over from its latest state.
  function resync() {
    gen++;
    cursor = -1;
    pending = [];
    pollLoop(gen);
  }

  async function act(kind) {
    if (mode !== 'act' || !legal || btn[kind].disabled) return;
    let body = { kind };
    if (kind === 'allin') body = { kind: 'raise', amount: legal.maxRaiseTo };
    if (kind === 'raise') body = { kind: 'raise', amount: raiseTo };
    setMode('wait');
    const res = await post('/api/action', { sid, ...body });
    if (!res.ok) resync();
  }

  function stop() {
    gen++;
    pending = [];
  }

  async function leave(where) {
    stop();
    await post('/api/leave', {});
    onExit(where);
  }

  Object.entries(btn).forEach(([kind, b]) => b.addEventListener('click', () => act(kind)));
  el.slider.addEventListener('input', () => {
    if (!legal) return;
    const lo = legal.minRaiseTo, hi = legal.maxRaiseTo, step = view.blinds[0];
    const f = el.slider.value / 1000;
    // Snap to small-blind steps, but always let the ends reach min and max.
    setRaise(f >= 1 ? hi : f <= 0 ? lo : Math.round((lo + f * (hi - lo)) / step) * step);
  });
  $('#step-down').addEventListener('click', () => setRaise(raiseTo - view.blinds[1]));
  $('#step-up').addEventListener('click', () => setRaise(raiseTo + view.blinds[1]));
  screen.querySelectorAll('[data-preset]').forEach((b) => b.addEventListener('click', () => {
    if (!legal) return;
    const middle = view.pot + view.players.reduce((sum, p) => sum + p.bet, 0);
    const fraction = { min: 0, half: 0.5, pot: 1 }[b.dataset.preset];
    setRaise(fraction ? legal.currentBet + (middle + legal.toCall) * fraction : legal.minRaiseTo);
  }));

  $('#btn-leave').addEventListener('click', () => {
    if (mode === 'over') leave('town'); else el.leave.hidden = false;
  });
  $('#btn-leave-no').addEventListener('click', () => { el.leave.hidden = true; });
  $('#btn-leave-yes').addEventListener('click', () => leave('town'));
  $('#btn-result-town').addEventListener('click', () => leave('town'));
  $('#btn-result-again').addEventListener('click', () => leave({ again: meta.saloon.id }));
  $('#btn-victory').addEventListener('click', () => leave('menu'));

  addEventListener('keydown', (e) => {
    if (screen.hidden || e.metaKey || e.ctrlKey || e.altKey) return;
    if (!el.result.hidden || !el.victory.hidden || !el.leave.hidden || mode !== 'act') return;
    const key = e.key.toLowerCase();
    if (key === 'f') act('fold');
    else if (key === 'c') act(legal.canCheck ? 'check' : 'call');
    else if (key === 'r' || key === 'b') act('raise');
    else if (key === 'a') act('allin');
    else if (key === 'arrowleft') setRaise(raiseTo - view.blinds[1]);
    else if (key === 'arrowright') setRaise(raiseTo + view.blinds[1]);
  });

  // ------------------------------------------------------- event playback
  async function play(ev, instant, g) {
    const s = ev.state;
    const fresh = instant || !view || view.hand !== s.hand;
    if (fresh) clearHand();
    const prev = fresh ? null : view;
    const dealt = render(s, prev, instant);
    view = s;
    // Hands I'm not part of run faster.
    const mine = s.players[ME];
    tempo = mine.out || mine.folded || !mine.cards.length ? 0.45 : 1;
    if (ev.type !== 'turn' || ev.who !== ME) setMode(mode === 'over' ? 'over' : 'wait');

    if (!instant) {
      if (dealt.board) await pause(380 + dealt.board * 120, g);
      else if (dealt.hole) await pause(350 + dealt.hole * 55, g);
    }

    switch (ev.type) {
      case 'turn':
        setActive(ev.who);
        if (ev.who === ME) {
          enableControls(ev.legal);
        } else if (!instant) {
          say(ev.who, '<span class="dots"><span></span><span></span><span></span></span>', { sticky: true });
          await pause(380 + Math.random() * 520, g);
        }
        break;
      case 'action': {
        const line = actionLine(ev);
        say(ev.who, line.text, { loud: line.loud });
        setActive(null);
        if (!instant) await pause(ev.who === ME ? 350 : 700, g);
        break;
      }
      case 'blind':
        if (!instant) await pause(240, g);
        break;
      case 'reveal':
        setActive(null);
        if (!instant) await pause(1000, g);
        break;
      case 'showdown':
        setActive(null);
        showHands(ev.hands);
        if (!instant) await pause(1500, g);
        break;
      case 'hand_end':
        finishHand(ev, s, instant);
        if (!instant) {
          tempo = Math.max(tempo, 0.7);
          await pause(ev.showdown ? 3400 : 2100, g);
        }
        break;
      case 'match_end':
        if (!instant) await pause(900, g);
        showResult(ev);
        break;
      default: {
        // Bets being collected or returned.
        const moved = prev && s.players.some((p, i) => p.bet !== prev.players[i].bet);
        if (!instant && moved) await pause(360, g);
      }
    }
  }

  async function pump() {
    if (pumping) return;
    pumping = true;
    const g = gen;
    try {
      while (pending.length && g === gen) {
        const { ev, instant } = pending.shift();
        await play(ev, instant, g);
      }
    } catch (err) {
      if (!(err instanceof Stale)) console.error(err);
    } finally {
      pumping = false;
      if (pending.length) pump();
    }
  }

  async function pollLoop(g) {
    while (g === gen) {
      let data;
      try {
        const res = await fetch(`/api/events?sid=${sid ?? 0}&since=${cursor}`);
        data = await res.json();
      } catch {
        await sleep(1500);
        continue;
      }
      if (g !== gen) return;
      if (data.sid === null) {          // the tournament is gone (server restarted?)
        stop();
        onExit('town');
        return;
      }
      if (builtFor !== data.sid) {
        meta = data.meta;
        builtFor = data.sid;
        view = null;
        buildSeats();
      }
      if (data.catchup || data.sid !== sid) {
        sid = data.sid;
        const latest = data.events.at(-1);
        if (latest) {
          cursor = latest.i + 1;
          pending = [{ ev: latest, instant: true }];
        }
      } else {
        for (const ev of data.events) {
          pending.push({ ev, instant: false });
          cursor = ev.i + 1;
        }
      }
      pump();
    }
  }

  // Start following tournament `id`. `fromStart` plays it from its first event
  // (a fresh game); otherwise we jump to wherever it is now (a page reload).
  function open(id, fromStart) {
    gen++;
    pending = [];
    sid = id;
    cursor = fromStart ? 0 : -1;
    view = null;
    builtFor = null;
    el.result.hidden = el.victory.hidden = el.leave.hidden = true;
    el.banner.classList.remove('show');
    el.pot.classList.remove('show');
    el.dealer.classList.add('off');
    el.board.replaceChildren();
    screen.querySelectorAll('.seat-el').forEach((node) => node.remove());
    seats = [];
    mode = 'wait';
    setMode('wait');
    pollLoop(gen);
  }

  return { open, stop };
}
