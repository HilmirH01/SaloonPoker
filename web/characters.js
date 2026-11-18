// Original cartoon characters, drawn as inline SVG from a "look":
//
//   { base: 'cowboy' | 'cowgirl', hat, facial, shirt, neck, eyewear,   <- wardrobe ids (see story.py)
//     skin?, hair?, sly? }                                            <- optional, used for opponents
//
// frontChar(look) - bust facing the viewer.
// backChar(look)  - the same character seen from behind (seats on the near side of the table).
//
// Faces carry three expressions (neutral / happy / sad). The wrapping element
// picks one with data-mood="..."; see the .mood rules in style.css.

const INK = '#2b1a10';
const BASES = {
  cowboy: { skin: '#f6c79a', hair: '#6b3f1d' },
  cowgirl: { skin: '#f8cfa6', hair: '#c9512a' },
};

const HATS = {
  trail: { shape: 'western', hat: '#c98f4d', band: '#7a2d1c' },
  prairie: { shape: 'western', hat: '#f1dfb8', band: '#2fa39a' },
  outlaw: { shape: 'flat', hat: '#34313f', band: '#c92f2f' },
  derby: { shape: 'bowler', hat: '#7a5230', band: '#3a2414' },
  rancher: { shape: 'western', hat: '#fbf6ea', band: '#2b1a10' },
  sombrero: { shape: 'sombrero', hat: '#ecc864', band: '#d8262c' },
  tophat: { shape: 'top', hat: '#2c2a36', band: '#8e44c9' },
  sheriff: { shape: 'western', hat: '#5f3d22', band: '#2b1a10', star: true },
  goldhat: { shape: 'western', hat: '#ffd23f', band: '#b8860b', shine: true },
};

const SHIRTS = {
  denim: { kind: 'plain', main: '#3f7fc4' },
  rose: { kind: 'plain', main: '#d9486e' },
  plaid: { kind: 'plaid', main: '#cf3f33', line: '#5c1410' },
  forest: { kind: 'plain', main: '#2f8a4e' },
  vest: { kind: 'vest', main: '#f1e7d0', over: '#8a5528' },
  poncho: { kind: 'poncho', main: '#dd8f2e', line: '#1f7a6b' },
  gambler: { kind: 'suit', main: '#3b3747', over: '#c92f2f', front: '#f6efe0' },
  lawman: { kind: 'vest', main: '#e8dcc0', over: '#3d2c1e', star: true },
  goldsuit: { kind: 'suit', main: '#f2c230', over: '#fff3d6', front: '#fffdf4' },
};

let uid = 0;  // for clip-path ids, which must be unique on the page

function shade(hex, factor) {
  const n = parseInt(hex.slice(1), 16);
  const part = (shift) => Math.max(0, Math.min(255, Math.round(((n >> shift) & 255) * factor)));
  return `rgb(${part(16)},${part(8)},${part(0)})`;
}

const svg = (viewBox, body) =>
  `<svg class="char-svg" viewBox="${viewBox}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">` +
  `<g stroke="${INK}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">${body}</g></svg>`;

const mood = (name, body) => `<g class="mood mood-${name}">${body}</g>`;

function star(cx, cy, r) {
  const points = [];
  for (let i = 0; i < 10; i++) {
    const radius = i % 2 ? r * 0.45 : r, angle = -Math.PI / 2 + (i * Math.PI) / 5;
    points.push(`${(cx + radius * Math.cos(angle)).toFixed(1)},${(cy + radius * Math.sin(angle)).toFixed(1)}`);
  }
  return `<polygon points="${points.join(' ')}" fill="#ffd23f" stroke-width="3"/>`;
}

// ------------------------------------------------------------------- hats
function hat(id, front) {
  const h = HATS[id] || HATS.trail;
  const shine = h.shine
    ? `<path d="M150 30 l3 8 l8 3 l-8 3 l-3 8 l-3 -8 l-8 -3 l8 -3 Z" fill="#fff" stroke="none"/>` : '';
  const badge = h.star && front ? star(100, 51, 10) : '';
  const gleam = (d) => `<path d="${d}" fill="none" stroke="#fff" stroke-opacity=".4" stroke-width="4"/>`;
  switch (h.shape) {
    case 'flat':
      return `
        <ellipse cx="100" cy="80" rx="94" ry="14" fill="${h.hat}"/>
        <path d="M57 80 C54 60 55 40 60 32 C80 24 120 24 140 32 C145 40 146 60 143 80 C128 88 72 88 57 80 Z" fill="${h.hat}"/>
        <path d="M56 66 C80 76 120 76 144 66 L143 80 C128 88 72 88 57 80 Z" fill="${h.band}"/>
        ${gleam('M68 42 C74 36 82 34 90 34')}`;
    case 'bowler':
      return `
        <path d="M38 78 C38 68 52 73 62 78 C82 87 118 87 138 78 C148 73 162 68 162 78 C162 91 136 97 100 97 C64 97 38 91 38 78 Z" fill="${h.hat}"/>
        <path d="M56 80 C50 44 72 24 100 24 C128 24 150 44 144 80 C128 88 72 88 56 80 Z" fill="${h.hat}"/>
        <path d="M55 68 C80 78 120 78 145 68 L144 80 C128 88 72 88 56 80 Z" fill="${h.band}"/>
        ${gleam('M70 46 C76 38 84 34 92 33')}`;
    case 'top':
      return `
        <ellipse cx="100" cy="80" rx="76" ry="12" fill="${h.hat}"/>
        <path d="M60 80 L56 8 C80 0 120 0 144 8 L140 80 C124 88 76 88 60 80 Z" fill="${h.hat}"/>
        <path d="M59 62 C80 71 120 71 141 62 L140 80 C124 88 76 88 60 80 Z" fill="${h.band}"/>
        ${gleam('M70 18 L72 50')}`;
    case 'sombrero':
      return `
        <ellipse cx="100" cy="78" rx="112" ry="18" fill="${h.hat}"/>
        <ellipse cx="100" cy="77" rx="96" ry="11" fill="none" stroke="${h.band}" stroke-width="3.5" stroke-dasharray="7 6"/>
        <path d="M64 78 C66 52 82 18 100 18 C118 18 134 52 136 78 C122 86 78 86 64 78 Z" fill="${h.hat}"/>
        <path d="M67 68 L75 60 L83 68 L91 60 L100 68 L109 60 L117 68 L125 60 L133 68" fill="none" stroke="${h.band}" stroke-width="4"/>`;
    default:
      return `
        <path d="M6 70 C6 60 22 64 36 71 C62 83 138 83 164 71 C178 64 194 60 194 70 C194 85 160 95 100 95 C40 95 6 85 6 70 Z" fill="${h.hat}"/>
        <path d="M54 76 C49 44 57 21 78 23 C88 24 92 30 100 30 C108 30 112 24 122 23 C143 21 151 44 146 76 C130 85 70 85 54 76 Z" fill="${h.hat}"/>
        <path d="M53 64 C80 75 120 75 147 64 L146 76 C130 85 70 85 54 76 Z" fill="${h.band}"/>
        ${gleam('M70 40 C74 34 80 32 86 33')}${badge}${shine}`;
  }
}

// ---------------------------------------------------------------- clothes
const TORSO = 'M12 240 C12 198 40 180 76 172 L124 172 C160 180 188 198 188 240 Z';
const TORSO_BACK = 'M8 210 C8 160 40 138 78 130 L122 130 C160 138 192 160 192 210 Z';

function shirtFront(id) {
  const s = SHIRTS[id] || SHIRTS.denim;
  const collar = (fill) => `
    <path d="M76 172 L100 197 L89 207 L66 180 Z" fill="${fill}" stroke-width="4"/>
    <path d="M124 172 L100 197 L111 207 L134 180 Z" fill="${fill}" stroke-width="4"/>`;
  const clip = `torso${++uid}`;
  const clipDef = (d) => `<clipPath id="${clip}"><path d="${d}"/></clipPath>`;
  switch (s.kind) {
    case 'plaid':
      return {
        torso: `${clipDef(TORSO)}<path d="${TORSO}" fill="${s.main}"/>
          <g clip-path="url(#${clip})" stroke="${s.line}" stroke-width="6" stroke-opacity=".55" fill="none">
            <path d="M38 170 V240 M68 170 V240 M132 170 V240 M162 170 V240 M0 196 H200 M0 220 H200"/>
          </g>
          <path d="${TORSO}" fill="none"/>`,
        detail: collar(shade(s.main, 0.8)),
      };
    case 'vest':
      return {
        torso: `<path d="${TORSO}" fill="${s.main}"/>`,
        detail: `
          <path d="M70 174 L97 222 L93 240 L26 240 C26 208 44 186 70 174 Z" fill="${s.over}"/>
          <path d="M130 174 L103 222 L107 240 L174 240 C174 208 156 186 130 174 Z" fill="${s.over}"/>
          ${s.star ? star(58, 216, 11) : ''}`,
      };
    case 'suit':
      return {
        torso: `<path d="${TORSO}" fill="${s.main}"/>`,
        detail: `
          <path d="M82 172 L118 172 L114 240 L86 240 Z" fill="${s.front}"/>
          <path d="M74 174 L100 214 L94 240 L58 240 Z" fill="${s.over}"/>
          <path d="M126 174 L100 214 L106 240 L142 240 Z" fill="${s.over}"/>`,
      };
    case 'poncho': {
      const drape = 'M2 240 C6 200 38 178 78 170 L122 170 C162 178 194 200 198 240 Z';
      return {
        torso: `${clipDef(drape)}<path d="${drape}" fill="${s.main}"/>
          <g clip-path="url(#${clip})" fill="none" stroke-width="6">
            <path d="M0 206 L20 196 L40 206 L60 196 L80 206 L100 196 L120 206 L140 196 L160 206 L180 196 L200 206" stroke="${s.line}"/>
            <path d="M0 226 L20 216 L40 226 L60 216 L80 226 L100 216 L120 226 L140 216 L160 226 L180 216 L200 226" stroke="#fff3d6"/>
          </g>
          <path d="${drape}" fill="none"/>`,
        detail: `<path d="M78 172 Q100 192 122 172" fill="none" stroke-width="4"/>`,
      };
    }
    default:
      return { torso: `<path d="${TORSO}" fill="${s.main}"/>`, detail: collar(shade(s.main, 1.25)) };
  }
}

function neckFront(id) {
  const bandana = (fill) => `
    <path d="M66 170 Q100 186 134 170 Q128 190 100 218 Q72 190 66 170 Z" fill="${fill}"/>
    <g fill="#fff" stroke="none"><circle cx="88" cy="186" r="2.6"/><circle cx="100" cy="196" r="2.6"/>
      <circle cx="112" cy="186" r="2.6"/><circle cx="100" cy="180" r="2.6"/></g>`;
  switch (id) {
    case 'bandana_red': return bandana('#e0392b');
    case 'bandana_blue': return bandana('#2f6fd0');
    case 'bolo': return `
      <path d="M86 174 L100 196 L114 174 M98 204 L93 226 M102 204 L107 226" fill="none" stroke-width="3.5"/>
      <ellipse cx="100" cy="198" rx="7" ry="9" fill="#35c2c0" stroke-width="3.5"/>`;
    case 'bowtie': return `
      <path d="M100 187 L83 177 L83 197 Z M100 187 L117 177 L117 197 Z" fill="#23212d" stroke-width="3.5"/>
      <circle cx="100" cy="187" r="4.5" fill="#23212d" stroke-width="3"/>`;
    case 'goldchain': return `
      <g fill="#ffd23f" stroke-width="2.5">${[[80, 178], [86, 187], [93, 194], [100, 197], [107, 194], [114, 187], [120, 178]]
        .map(([x, y]) => `<circle cx="${x}" cy="${y}" r="4.2"/>`).join('')}
        <path d="M100 201 l7 9 l-7 9 l-7 -9 Z"/></g>`;
    default: return '';
  }
}

// ------------------------------------------------------------------ faces
function facialHair(id, hair) {
  const walrus = `<path d="M76 141 Q100 128 124 141 Q130 154 118 153 Q100 144 82 153 Q70 154 76 141 Z" fill="${hair}" stroke-width="4"/>`;
  const small = `<path d="M82 142 Q100 133 118 142 Q118 149 110 148 Q100 143 90 148 Q82 149 82 142 Z" fill="${hair}" stroke-width="3.5"/>`;
  const mouthPatch = (skin) => `<ellipse cx="100" cy="153" rx="15" ry="8" fill="${skin}" stroke="none"/>`;
  switch (id) {
    case 'pencil':
      return { over: `<path d="M83 144 Q100 136 117 144" fill="none" stroke="${hair}" stroke-width="5"/>` };
    case 'handlebar':
      return { over: `<path d="M100 141 C92 132 72 134 64 146 C60 153 52 153 47 146 C50 163 72 165 86 156 C93 152 98 148 100 146
          C102 148 107 152 114 156 C128 165 150 163 153 146 C148 153 140 153 136 146 C128 134 108 132 100 141 Z" fill="${hair}" stroke-width="4"/>` };
    case 'walrus':
      return { over: walrus };
    case 'goatee':
      return {
        under: `<path d="M87 158 Q100 152 113 158 Q114 176 100 181 Q86 176 87 158 Z" fill="${hair}" stroke-width="4"/>`,
        over: small,
      };
    case 'chops':
      return {
        under: `
          <path d="M54 100 C50 128 56 152 76 160 C82 150 72 142 68 130 C64 118 64 108 62 98 Z" fill="${hair}" stroke-width="4"/>
          <path d="M146 100 C150 128 144 152 124 160 C118 150 128 142 132 130 C136 118 136 108 138 98 Z" fill="${hair}" stroke-width="4"/>`,
        over: walrus,
      };
    case 'beard':
      return {
        under: (skin) => `
          <path d="M53 108 C50 146 66 178 100 180 C134 178 150 146 147 108 C142 128 132 138 100 138 C68 138 58 128 53 108 Z" fill="${hair}" stroke-width="4"/>
          ${mouthPatch(skin)}`,
        over: small,
      };
    case 'prospector':
      return {
        under: (skin) => `
          <path d="M53 108 C46 150 60 196 78 208 C86 222 94 214 100 228 C106 214 114 222 122 208 C140 196 154 150 147 108 C142 128 132 138 100 138 C68 138 58 128 53 108 Z" fill="${hair}" stroke-width="4"/>
          <path d="M84 176 Q88 192 84 204 M116 176 Q112 192 116 204 M100 180 V206" fill="none" stroke-width="3" stroke-opacity=".35"/>
          ${mouthPatch(skin)}`,
        over: walrus,
      };
    default:
      return {};
  }
}

function eyewear(id) {
  switch (id) {
    case 'specs': return `
      <g fill="#cfeaff" fill-opacity=".3" stroke-width="3.5"><circle cx="82" cy="119" r="14"/><circle cx="118" cy="119" r="14"/></g>
      <path d="M96 117 Q100 113 104 117 M68 117 L55 112 M132 117 L145 112" fill="none" stroke-width="3.5"/>`;
    case 'shades': return `
      <g fill="#1d1b26" stroke-width="3.5"><circle cx="82" cy="119" r="14"/><circle cx="118" cy="119" r="14"/></g>
      <path d="M96 117 Q100 113 104 117 M68 117 L55 112 M132 117 L145 112" fill="none" stroke-width="3.5"/>
      <path d="M74 113 l6 -4 M110 113 l6 -4" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="3"/>`;
    case 'monocle': return `
      <circle cx="118" cy="119" r="15" fill="#cfeaff" fill-opacity=".3" stroke="#b8860b" stroke-width="4"/>
      <path d="M130 128 Q142 150 134 172" fill="none" stroke="#b8860b" stroke-width="2.5" stroke-dasharray="4 3"/>`;
    case 'patch': return `
      <path d="M56 96 L144 110" fill="none" stroke-width="3.5"/>
      <path d="M68 108 Q82 102 96 110 Q98 128 82 134 Q66 128 68 108 Z" fill="#23212d" stroke-width="3.5"/>`;
    default: return '';
  }
}

function face(skin, hair, { girl, sly }) {
  const w = sly ? 7 : girl ? 3.5 : 5;
  const eyes = sly ? `
      <path d="M72 116 L93 118 Q92 129 82 129 Q73 128 72 116 Z" fill="#fff" stroke-width="3.5"/>
      <path d="M128 116 L107 118 Q108 129 118 129 Q127 128 128 116 Z" fill="#fff" stroke-width="3.5"/>
      <circle cx="85" cy="123" r="3.8" fill="${INK}" stroke="none"/>
      <circle cx="115" cy="123" r="3.8" fill="${INK}" stroke="none"/>` : `
      <ellipse cx="82" cy="119" rx="9" ry="11" fill="#fff" stroke-width="3.5"/>
      <ellipse cx="118" cy="119" rx="9" ry="11" fill="#fff" stroke-width="3.5"/>
      <circle cx="84" cy="121" r="4.5" fill="${INK}" stroke="none"/>
      <circle cx="116" cy="121" r="4.5" fill="${INK}" stroke="none"/>
      <circle cx="85.5" cy="119" r="1.6" fill="#fff" stroke="none"/>
      <circle cx="117.5" cy="119" r="1.6" fill="#fff" stroke="none"/>
      ${girl ? '<path d="M72 112 L67 107 M128 112 L133 107" fill="none" stroke-width="3.5"/>' : ''}`;
  const brows = sly
    ? { neutral: 'M68 104 L94 111 M132 104 L106 111', happy: 'M68 100 Q82 96 94 104 M132 100 Q118 96 106 104', sad: 'M68 110 L94 102 M132 110 L106 102' }
    : { neutral: 'M72 103 Q82 98 92 103 M108 103 Q118 98 128 103', happy: 'M72 100 Q82 93 92 100 M108 100 Q118 93 128 100', sad: 'M72 106 Q84 101 92 98 M128 106 Q116 101 108 98' };
  const brow = (d) => `<path d="${d}" fill="none" stroke-width="${w}"/>`;
  return `
    <circle cx="68" cy="138" r="8" fill="#ff8f7a" fill-opacity=".4" stroke="none"/>
    <circle cx="132" cy="138" r="8" fill="#ff8f7a" fill-opacity=".4" stroke="none"/>
    ${girl ? `<g fill="${shade(skin, 0.78)}" stroke="none"><circle cx="74" cy="132" r="1.6"/><circle cx="80" cy="135" r="1.6"/>
      <circle cx="126" cy="132" r="1.6"/><circle cx="120" cy="135" r="1.6"/></g>` : ''}
    <g class="eyes">${eyes}</g>
    <path d="M100 126 Q108 136 98 138" fill="none" stroke-width="4"/>
    ${mood('neutral', `${brow(brows.neutral)}
      <path d="${sly ? 'M89 152 Q100 156 111 152' : 'M86 148 Q100 158 114 148'}" fill="none" stroke-width="4.5"/>`)}
    ${mood('happy', `${brow(brows.happy)}
      <path d="M82 144 Q100 170 118 144 Z" fill="#7a1f1f" stroke-width="4"/>
      <path d="M86 146 Q100 152 114 146 L111 151 Q100 156 89 151 Z" fill="#fff" stroke="none"/>`)}
    ${mood('sad', `${brow(brows.sad)}
      <path d="M88 157 Q100 147 112 157" fill="none" stroke-width="4.5"/>
      <path d="M142 104 q6 9 0 13 q-6 -4 0 -13 Z" fill="#8fd3ff" stroke-width="2.5"/>`)}`;
}

// ------------------------------------------------------------------ busts
function resolve(look = {}) {
  const base = BASES[look.base] ? look.base : 'cowboy';
  return {
    girl: base === 'cowgirl',
    skin: look.skin || BASES[base].skin,
    hair: look.hair || BASES[base].hair,
    sly: !!look.sly,
    hat: look.hat, facial: look.facial, shirt: look.shirt, neck: look.neck, eyewear: look.eyewear,
  };
}

const braid = (x, dx) => `
  <circle cx="${x}" cy="150" r="9.5"/><circle cx="${x + dx}" cy="165" r="9.5"/>
  <circle cx="${x + 2 * dx}" cy="180" r="9"/><circle cx="${x + 3 * dx}" cy="194" r="8"/>`;

export function frontChar(look) {
  const c = resolve(look);
  const skinShade = shade(c.skin, 0.86);
  const shirt = shirtFront(c.shirt);
  const whiskers = facialHair(c.facial, c.hair);
  const under = typeof whiskers.under === 'function' ? whiskers.under(skinShade) : whiskers.under || '';
  const head = c.sly
    ? 'M54 100 C54 62 146 62 146 100 L146 130 C146 152 128 168 100 168 C72 168 54 152 54 130 Z'
    : 'M54 104 C54 62 146 62 146 104 L146 124 C146 150 124 168 100 168 C76 168 54 150 54 124 Z';
  const hairBack = c.girl ? `<g fill="${c.hair}" stroke-width="4">${braid(45, -1.5)}${braid(155, 1.5)}</g>` : '';
  const hairFront = c.girl ? `
      <path d="M57 86 C46 104 47 130 50 148 L62 140 C58 122 60 104 68 92 Z" fill="${c.hair}" stroke-width="4"/>
      <path d="M143 86 C154 104 153 130 150 148 L138 140 C142 122 140 104 132 92 Z" fill="${c.hair}" stroke-width="4"/>
      <path d="M62 84 C76 104 100 104 114 90 C122 100 132 100 138 90 L138 80 L62 80 Z" fill="${c.hair}" stroke-width="4"/>` : `
      <path d="M54 92 L54 120 Q63 112 62 96 Z" fill="${c.hair}" stroke-width="4"/>
      <path d="M146 92 L146 120 Q137 112 138 96 Z" fill="${c.hair}" stroke-width="4"/>`;

  return svg('0 0 200 230', `
    ${hairBack}
    ${shirt.torso}
    <path d="M84 150 L84 174 Q100 188 116 174 L116 150 Z" fill="${skinShade}"/>
    ${shirt.detail}
    ${neckFront(c.neck)}
    <ellipse cx="51" cy="122" rx="9" ry="12" fill="${skinShade}"/>
    <ellipse cx="149" cy="122" rx="9" ry="12" fill="${skinShade}"/>
    <path d="${head}" fill="${c.skin}"/>
    ${under}
    ${face(c.skin, c.hair, c)}
    ${whiskers.over || ''}
    ${eyewear(c.eyewear)}
    ${hairFront}
    ${hat(c.hat, true)}`);
}

export function backChar(look) {
  const c = resolve(look);
  const s = SHIRTS[c.shirt] || SHIRTS.denim;
  const coat = s.kind === 'vest' ? s.over : s.main;
  const bandana = { bandana_red: '#e0392b', bandana_blue: '#2f6fd0' }[c.neck];
  const extras = c.girl
    ? `<g fill="${c.hair}" stroke-width="4">
         <circle cx="72" cy="126" r="10"/><circle cx="69" cy="142" r="10"/><circle cx="66" cy="158" r="9.5"/><circle cx="64" cy="173" r="9"/>
         <circle cx="128" cy="126" r="10"/><circle cx="131" cy="142" r="10"/><circle cx="134" cy="158" r="9.5"/><circle cx="136" cy="173" r="9"/>
       </g>`
    : bandana ? `<path d="M96 126 L82 150 L100 140 Z M104 126 L118 150 L100 140 Z" fill="${bandana}" stroke-width="4"/>
       <circle cx="100" cy="128" r="7" fill="${bandana}" stroke-width="4"/>` : '';
  return svg('0 0 200 200', `
    <path d="${TORSO_BACK}" fill="${coat}"/>
    ${s.kind === 'vest' ? `<path d="M8 210 C8 176 22 156 44 144 L52 210 Z M192 210 C192 176 178 156 156 144 L148 210 Z" fill="${s.main}" stroke-width="4"/>` : ''}
    <path d="M86 108 L86 132 Q100 140 114 132 L114 108 Z" fill="${shade(c.skin, 0.86)}"/>
    <ellipse cx="53" cy="100" rx="8" ry="11" fill="${shade(c.skin, 0.86)}"/>
    <ellipse cx="147" cy="100" rx="8" ry="11" fill="${shade(c.skin, 0.86)}"/>
    <path d="M56 80 C56 50 144 50 144 80 L144 98 C144 116 124 126 100 126 C76 126 56 116 56 98 Z" fill="${c.hair}"/>
    ${extras}
    ${hat(c.hat, false)}`);
}
