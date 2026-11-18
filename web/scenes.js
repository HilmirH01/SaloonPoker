// Scenery, drawn as inline SVG: the town, its buildings and the saloon interior.

const INK = '#2b1a10';
let uid = 0;

const outlined = (body, width = 4) =>
  `<g stroke="${INK}" stroke-width="${width}" stroke-linejoin="round" stroke-linecap="round">${body}</g>`;

// ------------------------------------------------------------------- town
function cactus(x, y, s = 1) {
  return `<g transform="translate(${x} ${y}) scale(${s})" fill="#4f9a55">
    <path d="M-7 0 V-58 Q0 -70 7 -58 V0 Z"/>
    <path d="M-7 -22 H-20 Q-28 -22 -28 -32 V-44 Q-23 -50 -18 -44 V-34 H-7 Z"/>
    <path d="M7 -30 H18 Q26 -30 26 -40 V-54 Q21 -60 16 -54 V-42 H7 Z"/>
  </g>`;
}

export function townBackdrop() {
  const cloud = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s})" fill="#fff" fill-opacity=".9" stroke="none">
    <ellipse cx="0" cy="0" rx="46" ry="16"/><ellipse cx="-22" cy="-10" rx="22" ry="14"/><ellipse cx="14" cy="-14" rx="28" ry="18"/></g>`;
  const id = `town${++uid}`;  // gradient ids must be unique: the backdrop is used on two screens
  const tracks = (y) => `<path d="M0 ${y} H1400 M0 ${y + 22} H1400" stroke="#c99a58" stroke-width="5" stroke-dasharray="46 30" fill="none" opacity=".7"/>`;
  return `<svg viewBox="0 0 1400 800" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs>
      <linearGradient id="${id}-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#55b4e6"/><stop offset="1" stop-color="#ffe6b0"/></linearGradient>
      <linearGradient id="${id}-ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9bd78"/><stop offset="1" stop-color="#cf9650"/></linearGradient>
    </defs>
    <rect width="1400" height="260" fill="url(#${id}-sky)"/>
    <circle cx="1210" cy="78" r="78" fill="#fff6c8" opacity=".45"/>
    <circle cx="1210" cy="78" r="46" fill="#fff2a8"/>
    ${cloud(210, 70, 1.2)}${cloud(560, 44, 0.9)}${cloud(900, 96, 1.1)}
    ${outlined(`
      <path d="M-10 250 V190 H70 L96 150 H250 L270 190 H360 V250 Z" fill="#e6a071"/>
      <path d="M980 250 V200 L1010 160 H1150 L1170 120 H1300 L1320 170 H1410 V250 Z" fill="#e6a071"/>
      <path d="M380 250 L420 196 H600 L628 222 H760 L790 250 Z" fill="#d68857"/>
    `)}
    <rect y="240" width="1400" height="560" fill="url(#${id}-ground)"/>
    <path d="M0 240 H1400" stroke="${INK}" stroke-width="4"/>
    <rect y="352" width="1400" height="92" fill="#f0cb8e"/>
    <rect y="690" width="1400" height="110" fill="#f0cb8e"/>
    ${tracks(388)}${tracks(730)}
    ${outlined(`${cactus(18, 352, 0.8)}${cactus(1384, 690, 0.9)}${cactus(1372, 350, 0.6)}`)}
    <g fill="none" stroke="#a9773c" stroke-width="3" opacity=".8">
      <circle cx="655" cy="414" r="15"/><path d="M642 414 q13 -16 26 0 M645 406 q10 14 20 0 M655 400 v28"/>
    </g>
  </svg>`;
}

const SALOON_STYLE = [
  { wall: '#cf9458', trim: '#8a4b22', top: 0, tier: 0 },
  { wall: '#dcb872', trim: '#7a5a22', top: 1, tier: 0 },
  { wall: '#e6c84a', trim: '#8a6a10', top: 3, tier: 0 },
  { wall: '#bd8660', trim: '#6a3a1f', top: 2, tier: 1 },
  { wall: '#bcc8d2', trim: '#55687a', top: 1, tier: 1 },
  { wall: '#6a5862', trim: '#2e2530', top: 0, tier: 1 },
  { wall: '#93b660', trim: '#476a22', top: 3, tier: 1 },
  { wall: '#9298a4', trim: '#3f444f', top: 1, tier: 2 },
  { wall: '#ea9150', trim: '#9a3f1a', top: 2, tier: 2 },
  { wall: '#b63c4b', trim: '#e2a91f', top: 2, tier: 2 },
];

function facade(wall, trim, top) {
  const tops = [
    `<path d="M16 66 V34 H224 V66 Z" fill="${wall}"/><rect x="8" y="24" width="224" height="13" rx="3" fill="${trim}"/>`,
    `<path d="M16 66 V46 H58 V22 H182 V46 H224 V66 Z" fill="${wall}"/><rect x="50" y="14" width="140" height="11" rx="3" fill="${trim}"/>`,
    `<path d="M16 66 V46 Q120 -6 224 46 V66 Z" fill="${wall}"/><path d="M16 46 Q120 -6 224 46" fill="none" stroke="${trim}" stroke-width="9"/><path d="M16 46 Q120 -6 224 46" fill="none"/>`,
    `<path d="M16 66 V48 L120 8 L224 48 V66 Z" fill="${wall}"/><path d="M12 50 L120 8 L228 50" fill="none" stroke="${trim}" stroke-width="9"/><path d="M12 50 L120 8 L228 50" fill="none"/>`,
  ];
  let planks = '';
  for (let y = 80; y < 236; y += 14) planks += `M24 ${y} H216 `;
  return `
    ${tops[top]}
    <rect x="24" y="64" width="192" height="174" fill="${wall}"/>
    <path d="${planks}" stroke="#000" stroke-opacity=".14" stroke-width="2"/>`;
}

function signText(name, y, size) {
  const fit = name.length > 13 ? size - 4 : name.length > 10 ? size - 2 : size;
  return `<text x="120" y="${y}" text-anchor="middle" font-family="Rye, Rockwell, Georgia, serif" font-size="${fit}"
    fill="${INK}" stroke="none">${name}</text>`;
}

// A saloon front. `lit` shows warm light in the windows (the saloon is open to you).
export function saloonFront(number, name, lit) {
  const s = SALOON_STYLE[number - 1];
  const glow = lit ? '#ffd978' : '#4a4038';
  const win = (x, y, w, h) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${glow}"/>
    <path d="M${x + w / 2} ${y} V${y + h} M${x} ${y + h / 2} H${x + w}" stroke-width="3"/>`;
  const upper = s.tier >= 1 ? `${win(46, 108, 36, 32)}${win(158, 108, 36, 32)}${s.tier === 1 ? win(102, 108, 36, 32) : ''}` : '';
  const balcony = s.tier === 2 ? `
    <rect x="92" y="104" width="56" height="38" rx="3" fill="${glow}"/>
    <path d="M120 104 V142" stroke-width="3"/>
    <path d="M30 128 H210 M30 144 H210" fill="none" stroke="${s.trim}" stroke-width="5"/>
    <path d="M40 128 V144 M62 128 V144 M84 128 V144 M156 128 V144 M178 128 V144 M200 128 V144" stroke="${s.trim}" stroke-width="4"/>` : '';
  const louvers = (x) => `<path d="M${x} 196 Q${x + 10} 186 ${x + 20} 196 V230 H${x} Z" fill="${s.trim}"/>
    <path d="M${x + 4} 204 H${x + 16} M${x + 4} 212 H${x + 16} M${x + 4} 220 H${x + 16}" stroke-width="2.5"/>`;
  return `<svg viewBox="0 0 240 250" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${outlined(`
    ${facade(s.wall, s.trim, s.top)}
    <rect x="38" y="70" width="164" height="30" rx="5" fill="#fff3d6"/>
    ${signText(name, 91, 17)}
    ${upper}${balcony}
    <path d="M4 164 L22 148 H218 L236 164 Z" fill="${s.trim}"/>
    <rect x="12" y="164" width="8" height="74" fill="${s.trim}"/><rect x="220" y="164" width="8" height="74" fill="${s.trim}"/>
    ${win(36, 178, 44, 38)}${win(160, 178, 44, 38)}
    <rect x="96" y="174" width="48" height="64" fill="#2a1a12"/>
    ${louvers(98)}${louvers(122)}
    <rect x="0" y="236" width="240" height="12" rx="3" fill="#8a5a2e"/>
    <path d="M40 236 V248 M80 236 V248 M120 236 V248 M160 236 V248 M200 236 V248" stroke-width="2.5"/>
    <circle cx="120" cy="${[46, 36, 34, 40][s.top]}" r="15" fill="${s.trim}"/>
    <text x="120" y="${[46, 36, 34, 40][s.top] + 6}" text-anchor="middle" font-family="'Luckiest Guy', Impact, sans-serif" font-size="18" fill="#fff3d6" stroke="none">${number}</text>
  `)}</svg>`;
}

export function shopFront() {
  let stripes = '';
  for (let i = 0; i < 9; i++) {
    const x = 6 + i * 25.4;
    stripes += `<path d="M${x + 14} 146 H${x + 36} L${x + 25.4 + 4} 170 H${x + 4} Z" fill="${i % 2 ? '#fff3d6' : '#d8362f'}" stroke-width="2.5"/>`;
  }
  return `<svg viewBox="0 0 240 250" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${outlined(`
    ${facade('#6fc0b4', '#2b7d73', 1)}
    <rect x="38" y="70" width="164" height="30" rx="5" fill="#fff3d6"/>
    ${signText('Clothing', 92, 19)}
    <path d="M100 30 q20 -14 40 0 q8 2 14 8 h-68 q6 -6 14 -8 Z" fill="#c98f4d" stroke-width="3"/>
    <rect x="46" y="108" width="36" height="30" rx="3" fill="#ffe9a8"/><rect x="158" y="108" width="36" height="30" rx="3" fill="#ffe9a8"/>
    ${stripes}
    <rect x="30" y="178" width="66" height="50" rx="3" fill="#ffe9a8"/>
    <path d="M46 200 q17 -18 34 0 q8 2 10 8 h-54 q2 -6 10 -8 Z" fill="#7a5230" stroke-width="3"/>
    <rect x="144" y="178" width="66" height="50" rx="3" fill="#ffe9a8"/>
    <path d="M160 192 l10 -6 q7 6 14 0 l10 6 l-6 9 l-5 -3 v22 h-12 v-22 l-5 3 Z" fill="#d9486e" stroke-width="3"/>
    <rect x="104" y="176" width="32" height="62" rx="3" fill="#2b7d73"/>
    <circle cx="129" cy="208" r="3" fill="#ffd23f" stroke-width="2"/>
    <rect x="0" y="236" width="240" height="12" rx="3" fill="#8a5a2e"/>
    <path d="M40 236 V248 M80 236 V248 M120 236 V248 M160 236 V248 M200 236 V248" stroke-width="2.5"/>
  `)}</svg>`;
}

export const padlock = `<svg viewBox="0 0 60 70" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${outlined(`
  <path d="M16 32 V22 a14 14 0 0 1 28 0 V32" fill="none" stroke-width="8"/>
  <path d="M16 32 V22 a14 14 0 0 1 28 0 V32" fill="none" stroke="#c9ccd4" stroke-width="3.5"/>
  <rect x="7" y="30" width="46" height="36" rx="7" fill="#e2a91f"/>
  <circle cx="30" cy="45" r="5" fill="${INK}" stroke="none"/><path d="M30 46 V57" stroke-width="5"/>
`)}</svg>`;

export function medal(place) {
  const fill = ['#ffd23f', '#cfd6de', '#d98b4a'][place - 1] || '#b8a890';
  return `<svg viewBox="0 0 60 74" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${outlined(`
    <path d="M16 36 L8 70 L22 62 L30 72 L38 62 L52 70 L44 36 Z" fill="#d8362f"/>
    <circle cx="30" cy="28" r="23" fill="${fill}"/>
    <circle cx="30" cy="28" r="16" fill="none" stroke-opacity=".3" stroke-width="2.5"/>
    <text x="30" y="37" text-anchor="middle" font-family="'Luckiest Guy', Impact, sans-serif" font-size="25" fill="${INK}" stroke="none">${place}</text>
  `)}</svg>`;
}

// ---------------------------------------------------------- saloon interior
// `hue` tints the wallpaper so each saloon feels like a different room.
export function saloonInterior(hue) {
  const id = `room${++uid}`;
  const paper = `hsl(${hue} 34% 30%)`, paperLight = `hsl(${hue} 36% 36%)`;
  let stripes = '', grooves = '', floor = '', bottles = '';
  for (let x = 0; x < 1400; x += 56) stripes += `<rect x="${x}" y="12" width="26" height="126" fill="${paperLight}"/>`;
  for (let x = 44; x < 1400; x += 62) grooves += `M${x} 146 V208 `;
  for (let i = -9; i <= 9; i++) floor += `M${700 + i * 96} 216 L${700 + i * 236} 800 `;
  const colors = ['#3f9e5a', '#c9772e', '#9a2f2f', '#d9c05a', '#4a7fc4', '#7a4a8a'];
  for (let row = 0; row < 2; row++) {
    for (let i = 0; i < 10; i++) {
      const x = 58 + i * 25, y = row ? 118 : 72, h = 22 + ((i * 7 + row * 3) % 4) * 3;
      bottles += `<path d="M${x} ${y} V${y - h} H${x + 3.5} V${y - h - 9} H${x + 8.5} V${y - h} H${x + 12} V${y} Z" fill="${colors[(i + row * 2) % colors.length]}" stroke-width="2.5"/>`;
    }
  }
  const lamp = (x) => `
    <circle cx="${x}" cy="64" r="92" fill="url(#${id}-glow)" stroke="none"/>
    <path d="M${x - 12} 96 H${x + 12} L${x + 8} 104 H${x - 8} Z" fill="#8a6a10" stroke-width="3"/>
    <path d="M${x - 10} 96 Q${x - 16} 70 ${x} 54 Q${x + 16} 70 ${x + 10} 96 Z" fill="#fff0a8" stroke-width="3"/>`;
  const leaf = (x) => `<path d="M${x} 196 V120 Q${x + 33} 100 ${x + 66} 120 V196 Z" fill="#a5642a"/>
    <path d="M${x + 12} 136 H${x + 54} M${x + 12} 150 H${x + 54} M${x + 12} 164 H${x + 54} M${x + 12} 178 H${x + 54}" stroke-width="3"/>`;
  return `<svg viewBox="0 0 1400 800" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs>
      <radialGradient id="${id}-glow"><stop offset="0" stop-color="#ffe9a0" stop-opacity=".55"/><stop offset="1" stop-color="#ffe9a0" stop-opacity="0"/></radialGradient>
      <linearGradient id="${id}-floor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7d4f28"/><stop offset="1" stop-color="#99653a"/></linearGradient>
      <linearGradient id="${id}-dusk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7fc4ea"/><stop offset="1" stop-color="#ffd9a0"/></linearGradient>
    </defs>
    <rect width="1400" height="216" fill="${paper}"/>
    ${stripes}
    <rect y="216" width="1400" height="584" fill="url(#${id}-floor)"/>
    <path d="${floor}" stroke="${INK}" stroke-opacity=".38" stroke-width="3" fill="none"/>
    <path d="M250 330 H420 M900 300 H1120 M120 520 H330 M1060 560 H1290 M520 660 H700 M760 720 H1000" stroke="${INK}" stroke-opacity=".3" stroke-width="3"/>
    ${outlined(`
      <rect x="-6" y="-6" width="1412" height="20" fill="#5a3414"/>
      <rect x="-6" y="138" width="1412" height="78" fill="#8a5528"/>
      <path d="${grooves}" stroke-opacity=".45" stroke-width="3"/>
      <rect x="-6" y="132" width="1412" height="12" fill="#5a3414"/>
      <rect x="-6" y="206" width="1412" height="12" fill="#4a2a12"/>

      ${lamp(410)}${lamp(990)}

      <rect x="36" y="22" width="284" height="108" rx="6" fill="#5a3414"/>
      <rect x="48" y="32" width="260" height="90" fill="#2e1a0c"/>
      <path d="M48 74 H308 M48 120 H308" stroke="#8a5528" stroke-width="6"/>
      ${bottles}
      <rect x="14" y="152" width="330" height="60" fill="#6a3c18"/>
      <path d="M40 166 H130 V202 H40 Z M150 166 H240 V202 H150 Z M260 166 H326 V202 H260 Z" fill="#7d4a20" stroke-width="3"/>
      <rect x="6" y="142" width="346" height="14" rx="4" fill="#9a622e"/>

      <rect x="848" y="26" width="66" height="84" fill="#f3e2b8" stroke-width="3.5"/>
      <text x="881" y="44" text-anchor="middle" font-family="Rye, Rockwell, Georgia, serif" font-size="12" fill="${INK}" stroke="none">WANTED</text>
      <circle cx="881" cy="68" r="11" fill="#b59a72" stroke-width="2.5"/><path d="M864 98 Q881 76 898 98 Z" fill="#b59a72" stroke-width="2.5"/>

      <rect x="1096" y="24" width="172" height="190" fill="#5a3414"/>
      <rect x="1110" y="38" width="144" height="176" fill="url(#${id}-dusk)"/>
      <path d="M1110 176 L1140 150 H1190 L1206 168 H1254 V214 H1110 Z" fill="#e6a071" stroke-width="3"/>
      ${leaf(1112)}${leaf(1186)}
    `)}
  </svg>`;
}
