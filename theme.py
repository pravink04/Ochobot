"""Blue cyberpunk theme for the Streamlit UI: CSS, animated hero mascot, particles, stat cards."""
import html
import random
from urllib.parse import quote

import streamlit as st


def _uri(svg: str) -> str:
    return f'url("data:image/svg+xml,{quote(svg.strip())}")'


# ---------------- static tech doodles (inline SVG data URIs) ----------------
HERO_BG_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 460 260' fill='none' stroke='#2f7bff' stroke-width='1.3'>
<g opacity='.45'>
<path d='M460 58 H402 L382 78 H300 L282 96 H226'/><path d='M460 204 H412 L394 186 H330 L312 202 H244'/>
<path d='M460 130 H436'/><path d='M300 260 V236 L318 220 H370'/>
<rect x='296' y='68' width='26' height='10'/><rect x='334' y='196' width='22' height='10'/>
</g>
<g fill='#19e3ff' stroke='none' opacity='.75'>
<circle cx='382' cy='78' r='3'/><circle cx='282' cy='96' r='3'/><circle cx='394' cy='186' r='3'/><circle cx='312' cy='202' r='3'/>
</g></svg>"""

SIDE_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 300' fill='none' stroke='#2f7bff' stroke-width='1.4'>
<g opacity='.5'>
<path d='M0 236 H62 L82 216 H152 L172 236 H300'/><path d='M0 268 H112 L132 248 H204'/>
<path d='M42 300 V262 L62 242'/><path d='M222 300 V272 L242 252 H300'/>
<path d='M300 196 H252 L232 176 H182'/><path d='M0 196 H34 L54 176 V150'/>
<rect x='118' y='201' width='26' height='15'/><rect x='200' y='236' width='20' height='12'/>
</g>
<g fill='#19e3ff' stroke='none' opacity='.8'>
<circle cx='82' cy='216' r='3'/><circle cx='152' cy='216' r='3'/><circle cx='204' cy='248' r='3'/>
<circle cx='182' cy='176' r='3'/><circle cx='62' cy='242' r='3'/><circle cx='54' cy='150' r='3'/>
</g></svg>"""

PAGE_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 420' fill='none' stroke='#2f7bff' stroke-width='1.4'>
<g opacity='.45'>
<path d='M640 330 H520 L496 306 H380 L356 330 H250'/><path d='M640 380 H470 L446 356 H330'/>
<path d='M640 270 H560 L536 246 V190'/><path d='M420 420 V392 L396 368 H300'/>
<path d='M560 420 V396 L580 376 H640'/><path d='M640 220 H600 L580 200 H520'/>
<rect x='370' y='290' width='38' height='16'/><rect x='480' y='360' width='26' height='14'/>
<circle cx='536' cy='190' r='10'/>
</g>
<g fill='#19e3ff' stroke='none' opacity='.7'>
<circle cx='496' cy='306' r='3'/><circle cx='380' cy='306' r='3'/><circle cx='446' cy='356' r='3'/>
<circle cx='536' cy='246' r='3'/><circle cx='396' cy='368' r='3'/><circle cx='520' cy='200' r='3'/>
</g></svg>"""

DOTS_SVG = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 72 30' fill='#19e3ff'>" + "".join(
    f"<circle cx='{4 + c * 9}' cy='{4 + r * 9}' r='1.4' opacity='{0.25 + 0.08 * c:.2f}'/>"
    for c in range(8) for r in range(3)) + "</svg>"

# ---------------- animated mascot: friendly bot inside spinning radar rings ----------------
# (inline SVG so the page CSS can animate its parts; no blank lines allowed inside HTML blocks)
BOT_SVG = """<svg viewBox='0 0 200 200' fill='none' stroke='#19e3ff'>
<defs><filter id='botglow' x='-50%' y='-50%' width='200%' height='200%'><feGaussianBlur stdDeviation='2.2' result='b'/><feMerge><feMergeNode in='b'/><feMergeNode in='SourceGraphic'/></feMerge></filter></defs>
<circle cx='100' cy='100' r='70' stroke-opacity='.25'/>
<g class='ring-slow'><circle cx='100' cy='100' r='92' stroke-dasharray='3 9' stroke-opacity='.7'/></g>
<g class='ring-fast' filter='url(#botglow)'><path d='M100 14 A86 86 0 0 1 186 100' stroke-width='3' stroke-linecap='round'/><circle cx='186' cy='100' r='3.5' fill='#19e3ff' stroke='none'/></g>
<g class='bot' filter='url(#botglow)'>
<line x1='100' y1='76' x2='100' y2='64' stroke-width='2'/>
<circle class='led' cx='100' cy='60' r='4.5' fill='#19e3ff' stroke='none'/>
<rect x='62' y='92' width='7' height='20' rx='3' fill='#0a1d3d' stroke-width='1.5'/>
<rect x='131' y='92' width='7' height='20' rx='3' fill='#0a1d3d' stroke-width='1.5'/>
<rect x='68' y='76' width='64' height='50' rx='15' fill='#0a1d3d' stroke-width='2'/>
<rect x='76' y='84' width='48' height='30' rx='10' fill='#04101f' stroke='#2f7bff' stroke-width='1.2'/>
<ellipse class='eye' cx='90' cy='97' rx='4.2' ry='5.5' fill='#19e3ff' stroke='none'/>
<ellipse class='eye' cx='110' cy='97' rx='4.2' ry='5.5' fill='#19e3ff' stroke='none'/>
<circle cx='83' cy='106' r='3' fill='#2f7bff' stroke='none' opacity='.55'/>
<circle cx='117' cy='106' r='3' fill='#2f7bff' stroke='none' opacity='.55'/>
<path d='M95 106 Q100 111 105 106' stroke-width='1.8' stroke-linecap='round'/>
<rect x='82' y='130' width='36' height='20' rx='8' fill='#0a1d3d' stroke-width='1.6'/>
<circle class='led' cx='100' cy='140' r='3' fill='#19e3ff' stroke='none'/>
</g></svg>"""


def _fx_html() -> str:
    """Soft neon particles that drift upward behind/around the content."""
    rnd = random.Random(11)
    dots = "".join(
        f'<i style="--x:{rnd.uniform(2, 98):.1f}%;--s:{rnd.uniform(3, 7):.1f}px;'
        f'--t:{rnd.uniform(16, 30):.1f}s;--d:-{rnd.uniform(0, 28):.1f}s"></i>' for _ in range(16))
    return f'<div class="fx" aria-hidden="true">{dots}</div>'


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;500;600;700&family=Orbitron:wght@600;800&display=swap');

:root {
  --void:#030712; --panel:#07142b; --panel2:#0a1d3d; --edge:#12457f;
  --blue:#2f7bff; --cyan:#19e3ff; --ice:#d6f4ff; --mute:#7fa6c9;
  --warn:#ffb020; --alert:#ff3d81;
}

/* ---------- fonts: apply to text, never to Streamlit's icon glyphs ---------- */
.stApp *:not([data-testid="stIconMaterial"]):not([class*="material"]):not([class*="Material"]) {
  font-family: 'Chakra Petch', sans-serif; }
[data-testid="stIconMaterial"], [class*="material-symbols"], [class*="material-icons"] {
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
  font-feature-settings: 'liga'; letter-spacing: normal; text-transform: none; }
.hero-title, .stat .num, .side-title { font-family: 'Orbitron', sans-serif !important; }

/* ---------- base ---------- */
.stApp {
  color: var(--ice);
  background:
    @@PAGE@@ right bottom / min(640px, 48vw) no-repeat,
    linear-gradient(rgba(47,123,255,.06) 1px, transparent 1px) 0 0 / 44px 44px,
    linear-gradient(90deg, rgba(47,123,255,.06) 1px, transparent 1px) 0 0 / 44px 44px,
    radial-gradient(1100px 560px at 85% -10%, rgba(47,123,255,.24), transparent 60%),
    radial-gradient(800px 480px at -10% 35%, rgba(25,227,255,.10), transparent 60%),
    var(--void);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stAppDeployButton"], .stDeployButton { display: none; }
.block-container { padding-top: 2rem; max-width: 1180px; }
h2, h3, h4 { color: var(--cyan) !important; font-weight: 600 !important; letter-spacing:.2px; }
p, li, label, .stMarkdown { color: var(--ice); }
small, [data-testid="stCaptionContainer"] { color: var(--mute) !important; }
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background: var(--void); }
::-webkit-scrollbar-thumb { background: var(--edge); border-radius:2px; }
::-webkit-scrollbar-thumb:hover { background: var(--blue); }

/* ---------- doodles: divider with end node, chamfered heading marker ---------- */
hr { border: 0 !important; height: 1px; opacity: 1 !important; margin: 1.1rem 0 !important; position: relative;
  background: linear-gradient(90deg, var(--cyan), var(--edge) 35%, transparent); }
hr::before { content:""; position:absolute; left:0; top:-3px; width:7px; height:7px; background: var(--cyan);
  box-shadow: 0 0 10px var(--cyan); }
h3::before { content:""; display:inline-block; width:9px; height:9px; margin-right:10px; background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan); clip-path: polygon(0 0, 100% 0, 100% 60%, 60% 100%, 0 100%); }

/* ---------- HUD corner brackets (shared) ---------- */
.hud { position:relative; border:1px solid var(--edge);
  background: linear-gradient(135deg, rgba(10,29,61,.88), rgba(5,14,32,.88)); }
.hud::before, .hud::after { content:""; position:absolute; width:16px; height:16px; pointer-events:none; }
.hud::before { top:-1px; left:-1px; border-top:2px solid var(--cyan); border-left:2px solid var(--cyan); }
.hud::after  { bottom:-1px; right:-1px; border-bottom:2px solid var(--cyan); border-right:2px solid var(--cyan); }

/* ---------- hero ---------- */
.hero { padding: 30px 34px 28px; margin-bottom: 16px; overflow:hidden;
  background: @@HERO@@ right center / auto 125% no-repeat,
              linear-gradient(135deg, rgba(10,29,61,.88), rgba(5,14,32,.88));
  box-shadow: 0 0 40px rgba(47,123,255,.18), inset 0 0 60px rgba(25,227,255,.04); }
.hero .scan { position:absolute; top:0; bottom:0; left:-160px; width:140px; pointer-events:none;
  background: linear-gradient(90deg, transparent, rgba(25,227,255,.28), transparent);
  animation: sweep 1.9s ease-out 1 forwards; }
.hero .stream { position:absolute; left:0; right:0; bottom:0; height:2px; pointer-events:none;
  background: linear-gradient(90deg, transparent, var(--cyan), var(--blue), transparent) no-repeat;
  background-size: 40% 100%; filter: drop-shadow(0 0 6px var(--cyan)); animation: stream 3.4s ease-in-out infinite; }
.hero-title { font-weight:800; line-height:1.15; font-size: clamp(1.6rem, 3.3vw, 2.7rem); margin:0 0 8px;
  max-width: calc(100% - 230px);
  background: linear-gradient(90deg, #a8e6ff 0%, #19e3ff 25%, #2f7bff 50%, #19e3ff 75%, #a8e6ff 100%);
  background-size: 200% 100%; -webkit-background-clip:text; background-clip:text; color:transparent;
  filter: drop-shadow(0 0 16px rgba(25,227,255,.35)); animation: shine 7s linear infinite; }
.hero-sub { color: var(--mute); font-size: 1.05rem; margin: 0 0 18px; text-wrap: balance;
  max-width: min(58ch, calc(100% - 230px)); }
.hero-sub::after { content:"\\2588"; margin-left:4px; color: var(--cyan); font-size:.8em; animation: caret 1.1s steps(1) infinite; }
.chips { display:flex; flex-wrap:wrap; gap:10px; }
.chip { border:1px solid var(--edge); background: rgba(47,123,255,.10); color: var(--ice);
  padding: 3px 12px; font-size:.85rem; border-radius:2px; }
.chip.live { border-color: var(--cyan); color: var(--cyan); background: rgba(25,227,255,.08); }
.chip.live i { display:inline-block; width:8px; height:8px; margin-right:8px; border-radius:50%;
  background: var(--cyan); box-shadow: 0 0 10px var(--cyan); animation: pulse 2s ease-in-out infinite; }

/* mascot */
.bot-wrap { position:absolute; right:46px; top:50%; width:172px; height:172px; margin-top:-86px; pointer-events:none; }
.bot-wrap svg { width:100%; height:100%; overflow:visible; }
.ring-slow { transform-origin: 100px 100px; animation: spin 26s linear infinite; }
.ring-fast { transform-origin: 100px 100px; animation: spinrev 9s linear infinite; }
.bot { animation: bob 3.6s ease-in-out infinite; }
.bot .eye { transform-box: fill-box; transform-origin: center; animation: blink 5s infinite; }
.bot .led { animation: led 1.4s ease-in-out infinite; }
@media (max-width: 900px) {
  .bot-wrap { display:none; }
  .hero-title, .hero-sub { max-width: none; }
}

/* ---------- stat cards ---------- */
.stats { display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; margin: 4px 0 18px; }
.stat { padding: 14px 18px; transition: transform .2s ease, box-shadow .2s ease; animation: rise .6s ease-out backwards;
  background: @@DOTS@@ right 16px top 14px / 72px 30px no-repeat,
              linear-gradient(135deg, rgba(10,29,61,.88), rgba(5,14,32,.88)); }
.stat:nth-child(2) { animation-delay: .12s; } .stat:nth-child(3) { animation-delay: .24s; }
.stat:hover { transform: translateY(-3px); box-shadow: 0 0 26px rgba(25,227,255,.22); }
.stat .num { font-weight:600; font-size:1.7rem; color: var(--cyan); text-shadow: 0 0 14px rgba(25,227,255,.45);
  animation: flare 1.2s ease-out backwards; }
.stat .lbl { color: var(--mute); font-size:.9rem; }
@media (max-width: 700px) {
  .stats { grid-template-columns: 1fr; }
  .hero { padding: 22px 20px; background: linear-gradient(135deg, rgba(10,29,61,.88), rgba(5,14,32,.88)); }
}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: @@SIDE@@ bottom center / 100% auto no-repeat, linear-gradient(180deg, #061226 0%, #030a18 100%);
  border-right: 1px solid var(--edge); box-shadow: 0 0 34px rgba(47,123,255,.16); }
[data-testid="stSidebar"], [data-testid="stSidebarContent"] { overflow-x: hidden !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .9rem; }
.side-title { font-weight:600; font-size:1.15rem; color: var(--cyan); margin: 2px 0 6px;
  text-shadow: 0 0 12px rgba(25,227,255,.4); display:flex; align-items:center; gap:10px; }
.side-title::before { content:""; width:8px; height:8px; border-radius:50%; background: var(--cyan);
  box-shadow: 0 0 10px var(--cyan); animation: pulse 2s ease-in-out infinite; }
.side-title::after { content:""; flex:1; height:1px; background: linear-gradient(90deg, var(--cyan), transparent); }
.side-sub { color: var(--mute); font-size:.88rem; line-height:1.4; margin-bottom: 4px; }

/* ---------- tabs ---------- */
[data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--edge); }
button[data-baseweb="tab"] { background: transparent; color: var(--mute); font-weight:600; font-size:1rem;
  padding: 10px 20px; border-radius: 2px 2px 0 0; transition: color .15s, background .15s; }
button[data-baseweb="tab"]:hover { color: var(--ice); background: rgba(47,123,255,.10); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--cyan); background: rgba(25,227,255,.08); }
[data-baseweb="tab-highlight"] { background: var(--cyan) !important; height:2px !important;
  box-shadow: 0 0 12px var(--cyan); }
[data-baseweb="tab-border"] { background: transparent !important; }

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button {
  background: rgba(47,123,255,.12); color: var(--ice); border: 1px solid var(--blue);
  border-radius: 2px; font-weight:600; transition: box-shadow .15s, background .15s, border-color .15s, transform .1s; }
.stButton > button:hover, .stDownloadButton > button:hover {
  border-color: var(--cyan); background: rgba(25,227,255,.14); color:#fff; box-shadow: 0 0 16px rgba(25,227,255,.35); }
.stButton > button:active, .stDownloadButton > button:active { transform: scale(.97); }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible { outline: 2px solid var(--cyan); outline-offset:2px; }
button[data-testid="stBaseButton-primary"], .stButton > button[kind="primary"] {
  position: relative; overflow: hidden;
  background: linear-gradient(90deg, #1b63ff, #19e3ff); color:#021022; border:0; font-weight:700;
  box-shadow: 0 0 20px rgba(25,227,255,.40); }
button[data-testid="stBaseButton-primary"]::after, .stButton > button[kind="primary"]::after {
  content:""; position:absolute; top:0; left:-60%; width:40%; height:100%; pointer-events:none;
  background: linear-gradient(100deg, transparent, rgba(255,255,255,.55), transparent);
  transform: skewX(-20deg); transition: left .6s ease; }
button[data-testid="stBaseButton-primary"]:hover::after, .stButton > button[kind="primary"]:hover::after { left: 130%; }
button[data-testid="stBaseButton-primary"]:hover, .stButton > button[kind="primary"]:hover {
  color:#021022; box-shadow: 0 0 30px rgba(25,227,255,.70); filter: brightness(1.08); }

/* ---------- inputs ---------- */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
div[data-baseweb="select"] > div:first-child, [data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: #06122a !important; border: 1px solid var(--edge) !important; border-radius: 2px !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within {
  border-color: var(--cyan) !important; box-shadow: 0 0 0 1px var(--cyan), 0 0 16px rgba(25,227,255,.25) !important; }
[data-baseweb="tag"] { background: rgba(47,123,255,.28) !important; border: 1px solid var(--blue) !important;
  border-radius: 2px !important; }
[data-baseweb="tag"] span { color: var(--ice) !important; }
[data-testid="stFileUploaderDropzone"] { background: rgba(47,123,255,.06); border: 1px dashed var(--blue); border-radius: 2px;
  transition: border-color .2s, background .2s, box-shadow .2s; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--cyan); background: rgba(25,227,255,.07);
  box-shadow: 0 0 18px rgba(25,227,255,.18); }

/* ---------- chat ---------- */
[data-testid="stChatMessage"] { background: linear-gradient(135deg, rgba(10,29,61,.85), rgba(6,17,38,.85));
  border: 1px solid #123a6b; border-left: 3px solid var(--blue); border-radius: 2px; padding: 1rem 1.2rem;
  animation: msgIn .45s ease-out backwards; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) { border-left-color: var(--cyan); }
[data-testid="stChatInput"] { background:#06122a; border:1px solid var(--edge); border-radius: 2px; }
[data-testid="stChatInput"]:focus-within { border-color: var(--cyan); box-shadow: 0 0 20px rgba(25,227,255,.25); }
[data-testid="stBottom"] > div { background: transparent; }

/* ---------- misc widgets ---------- */
[data-testid="stExpander"] details { background: rgba(7,20,43,.75); border: 1px solid #123a6b; border-radius: 2px; }
[data-testid="stExpander"] summary { color: var(--cyan); font-weight:600; }
[data-testid="stAlert"] { border-radius: 2px; border: 1px solid var(--edge); background: rgba(10,29,61,.7); }
[data-testid="stDataFrame"] { border: 1px solid var(--edge); border-radius: 2px; }
[data-testid="stSpinner"] { color: var(--cyan); }
[data-testid="stSpinnerIcon"] { border-color: rgba(25,227,255,.2) !important; border-top-color: var(--cyan) !important;
  filter: drop-shadow(0 0 6px var(--cyan)); }

/* ---------- confidence badge ---------- */
.badge { display:inline-flex; align-items:center; gap:8px; padding:2px 12px; margin: 6px 0 2px;
  font-size:.85rem; font-weight:600; border-radius:2px; border:1px solid; }
.badge::before { content:""; width:7px; height:7px; border-radius:50%; background: currentColor; box-shadow: 0 0 8px currentColor; }
.badge.High::before { animation: led 1.6s ease-in-out infinite; }
.badge.High   { color: var(--cyan);  background: rgba(25,227,255,.10); }
.badge.Medium { color: var(--warn);  background: rgba(255,176,32,.10); }
.badge.Low    { color: var(--alert); background: rgba(255,61,129,.10); }

/* ---------- floating neon particles ---------- */
.fx { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.fx i { position:absolute; left: var(--x); bottom: -20px; width: var(--s); height: var(--s); border-radius: 50%;
  background: radial-gradient(circle, #19e3ff, transparent 70%); opacity: 0;
  animation: floatUp var(--t) linear var(--d) infinite; }
.fx i:nth-child(3n) { background: radial-gradient(circle, #2f7bff, transparent 70%); }

/* ---------- keyframes ---------- */
@keyframes sweep   { to { left: 105%; } }
@keyframes shine   { to { background-position: 200% 0; } }
@keyframes pulse   { 50% { opacity: .35; } }
@keyframes led     { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
@keyframes caret   { 50% { opacity: 0; } }
@keyframes stream  { 0% { background-position: -60% 0; } 100% { background-position: 160% 0; } }
@keyframes spin    { to { transform: rotate(360deg); } }
@keyframes spinrev { to { transform: rotate(-360deg); } }
@keyframes bob     { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@keyframes blink   { 0%, 90%, 100% { transform: scaleY(1); } 94% { transform: scaleY(.08); } }
@keyframes rise    { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes msgIn   { from { opacity: 0; transform: translateX(-12px); } to { opacity: 1; transform: none; } }
@keyframes flare   { 0% { opacity: 0; text-shadow: 0 0 0 transparent; } 40% { opacity: 1; text-shadow: 0 0 30px #19e3ff; } }
@keyframes floatUp {
  0%   { transform: translate(0, 0) scale(.6); opacity: 0; }
  10%  { opacity: .75; }
  50%  { transform: translate(18px, -55vh) scale(1); }
  90%  { opacity: .45; }
  100% { transform: translate(-14px, -110vh) scale(.9); opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .fx { display: none; }
}
</style>
"""

CSS = (_CSS.replace("@@PAGE@@", _uri(PAGE_SVG)).replace("@@HERO@@", _uri(HERO_BG_SVG))
       .replace("@@SIDE@@", _uri(SIDE_SVG)).replace("@@DOTS@@", _uri(DOTS_SVG)))


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(_fx_html(), unsafe_allow_html=True)


def hero(provider: str, model: str):
    st.markdown(f"""<div class="hud hero">
<div class="scan"></div>
<div class="bot-wrap">{BOT_SVG}</div>
<div class="hero-title">Enterprise Knowledge Copilot</div>
<p class="hero-sub">Ask questions across your company documents. Every answer shows where it came from.</p>
<div class="chips">
<span class="chip live"><i></i>Online</span>
<span class="chip">{html.escape(provider)}</span>
<span class="chip">{html.escape(model)}</span>
</div>
<div class="stream"></div>
</div>""", unsafe_allow_html=True)


def stat_cards(docs: int, chunks: int, active: int):
    st.markdown(f"""<div class="stats">
<div class="hud stat"><div class="num">{docs}</div><div class="lbl">Documents indexed</div></div>
<div class="hud stat"><div class="num">{chunks}</div><div class="lbl">Searchable passages</div></div>
<div class="hud stat"><div class="num">{active}/{docs}</div><div class="lbl">Included in searches</div></div>
</div>""", unsafe_allow_html=True)