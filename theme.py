"""Blue cyberpunk theme for the Streamlit UI (CSS + small HTML helpers)."""
import html
import math
from urllib.parse import quote

import streamlit as st


def _uri(svg: str) -> str:
    return f'url("data:image/svg+xml,{quote(svg.strip())}")'


# ---------------- tech doodles (inline SVG, no external files) ----------------
def _hero_svg() -> str:
    cx, cy = 340, 130
    ticks = ""
    for i, deg in enumerate(range(0, 360, 10)):
        a = math.radians(deg)
        r2 = 114 if i % 3 == 0 else 109
        ticks += (f"<line x1='{cx + 104 * math.cos(a):.1f}' y1='{cy + 104 * math.sin(a):.1f}' "
                  f"x2='{cx + r2 * math.cos(a):.1f}' y2='{cy + r2 * math.sin(a):.1f}'/>")
    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 460 260' fill='none' stroke='#19e3ff'>
<g stroke-width='1' opacity='.55'>
<circle cx='{cx}' cy='{cy}' r='30'/><circle cx='{cx}' cy='{cy}' r='62' stroke-dasharray='3 6'/>
<circle cx='{cx}' cy='{cy}' r='92' opacity='.7'/>{ticks}
<path d='M{cx} 8v48M{cx} 204v48M208 {cy}h44M428 {cy}h32'/>
</g>
<path d='M{cx} 62 A68 68 0 0 1 {cx + 68} {cy}' stroke-width='3' opacity='.9'/>
<path d='M{cx - 92} {cy} A92 92 0 0 1 {cx} {cy - 92}' stroke='#2f7bff' stroke-width='2' opacity='.8'/>
<path d='M{cx} {cy} L{cx + 40} {cy - 40} H460' stroke='#2f7bff' stroke-width='1.5' opacity='.8'/>
<path d='M{cx} {cy} L{cx - 36} {cy + 36} H250 L236 {cy + 50} H170' stroke='#2f7bff' stroke-width='1.2' opacity='.5'/>
<circle cx='{cx + 40}' cy='{cy - 40}' r='3.5' fill='#19e3ff'/><circle cx='{cx - 36}' cy='{cy + 36}' r='3' fill='#19e3ff'/>
<circle cx='{cx}' cy='{cy}' r='5' fill='#19e3ff' stroke='none'/>
<rect x='392' y='196' width='56' height='6' opacity='.5'/><rect x='392' y='208' width='34' height='6' opacity='.35'/>
</svg>"""


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
.hero { padding: 30px 34px 26px; margin-bottom: 16px; overflow:hidden;
  background: @@HERO@@ right center / auto 125% no-repeat,
              linear-gradient(135deg, rgba(10,29,61,.88), rgba(5,14,32,.88));
  box-shadow: 0 0 40px rgba(47,123,255,.18), inset 0 0 60px rgba(25,227,255,.04); }
.hero .scan { position:absolute; top:0; bottom:0; left:-160px; width:140px; pointer-events:none;
  background: linear-gradient(90deg, transparent, rgba(25,227,255,.28), transparent);
  animation: sweep 1.9s ease-out 1 forwards; }
@keyframes sweep { to { left: 105%; } }
.hero-title { font-weight:800; line-height:1.15; font-size: clamp(1.6rem, 3.3vw, 2.7rem); margin:0 0 8px;
  background: linear-gradient(90deg, #a8e6ff 0%, #19e3ff 45%, #2f7bff 100%);
  -webkit-background-clip:text; background-clip:text; color:transparent;
  filter: drop-shadow(0 0 16px rgba(25,227,255,.35)); }
.hero-sub { color: var(--mute); font-size: 1.05rem; margin: 0 0 18px; max-width: 58ch; text-wrap: balance; }
.chips { display:flex; flex-wrap:wrap; gap:10px; }
.chip { border:1px solid var(--edge); background: rgba(47,123,255,.10); color: var(--ice);
  padding: 3px 12px; font-size:.85rem; border-radius:2px; }
.chip.live { border-color: var(--cyan); color: var(--cyan); background: rgba(25,227,255,.08); }
.chip.live i { display:inline-block; width:8px; height:8px; margin-right:8px; border-radius:50%;
  background: var(--cyan); box-shadow: 0 0 10px var(--cyan); animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 50% { opacity:.35; } }

/* ---------- stat cards ---------- */
.stats { display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; margin: 4px 0 18px; }
.stat { padding: 14px 18px;
  background: @@DOTS@@ right 16px top 14px / 72px 30px no-repeat,
              linear-gradient(135deg, rgba(10,29,61,.88), rgba(5,14,32,.88)); }
.stat .num { font-weight:600; font-size:1.7rem; color: var(--cyan); text-shadow: 0 0 14px rgba(25,227,255,.45); }
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
  text-shadow: 0 0 12px rgba(25,227,255,.4); display:flex; align-items:center; gap:12px; }
.side-title::after { content:""; flex:1; height:1px; background: linear-gradient(90deg, var(--cyan), transparent); }
.side-sub { color: var(--mute); font-size:.88rem; line-height:1.4; margin-bottom: 4px; }

/* ---------- tabs ---------- */
[data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--edge); }
button[data-baseweb="tab"] { background: transparent; color: var(--mute); font-weight:600; font-size:1rem;
  padding: 10px 20px; border-radius: 2px 2px 0 0; }
button[data-baseweb="tab"]:hover { color: var(--ice); background: rgba(47,123,255,.10); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--cyan); background: rgba(25,227,255,.08); }
[data-baseweb="tab-highlight"] { background: var(--cyan) !important; height:2px !important;
  box-shadow: 0 0 12px var(--cyan); }
[data-baseweb="tab-border"] { background: transparent !important; }

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button {
  background: rgba(47,123,255,.12); color: var(--ice); border: 1px solid var(--blue);
  border-radius: 2px; font-weight:600; transition: box-shadow .15s, background .15s, border-color .15s; }
.stButton > button:hover, .stDownloadButton > button:hover {
  border-color: var(--cyan); background: rgba(25,227,255,.14); color:#fff; box-shadow: 0 0 16px rgba(25,227,255,.35); }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible { outline: 2px solid var(--cyan); outline-offset:2px; }
button[data-testid="stBaseButton-primary"], .stButton > button[kind="primary"] {
  background: linear-gradient(90deg, #1b63ff, #19e3ff); color:#021022; border:0; font-weight:700;
  box-shadow: 0 0 20px rgba(25,227,255,.40); }
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
[data-testid="stFileUploaderDropzone"] { background: rgba(47,123,255,.06); border: 1px dashed var(--blue); border-radius: 2px; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--cyan); background: rgba(25,227,255,.07); }

/* ---------- chat ---------- */
[data-testid="stChatMessage"] { background: linear-gradient(135deg, rgba(10,29,61,.85), rgba(6,17,38,.85));
  border: 1px solid #123a6b; border-left: 3px solid var(--blue); border-radius: 2px; padding: 1rem 1.2rem; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) { border-left-color: var(--cyan); }
[data-testid="stChatInput"] { background:#06122a; border:1px solid var(--edge); border-radius: 2px; }
[data-testid="stChatInput"]:focus-within { border-color: var(--cyan); box-shadow: 0 0 20px rgba(25,227,255,.25); }
[data-testid="stBottom"] > div { background: transparent; }

/* ---------- misc widgets ---------- */
[data-testid="stExpander"] details { background: rgba(7,20,43,.75); border: 1px solid #123a6b; border-radius: 2px; }
[data-testid="stExpander"] summary { color: var(--cyan); font-weight:600; }
[data-testid="stAlert"] { border-radius: 2px; border: 1px solid var(--edge); background: rgba(10,29,61,.7); }
[data-testid="stDataFrame"] { border: 1px solid var(--edge); border-radius: 2px; }

/* ---------- confidence badge ---------- */
.badge { display:inline-flex; align-items:center; gap:8px; padding:2px 12px; margin: 6px 0 2px;
  font-size:.85rem; font-weight:600; border-radius:2px; border:1px solid; }
.badge::before { content:""; width:7px; height:7px; border-radius:50%; background: currentColor; box-shadow: 0 0 8px currentColor; }
.badge.High   { color: var(--cyan);  background: rgba(25,227,255,.10); }
.badge.Medium { color: var(--warn);  background: rgba(255,176,32,.10); }
.badge.Low    { color: var(--alert); background: rgba(255,61,129,.10); }

@media (prefers-reduced-motion: reduce) {
  .hero .scan { display:none; } .chip.live i { animation: none; }
  .stButton > button, .stDownloadButton > button { transition: none; }
}
</style>
"""

CSS = (_CSS.replace("@@PAGE@@", _uri(PAGE_SVG)).replace("@@HERO@@", _uri(_hero_svg()))
       .replace("@@SIDE@@", _uri(SIDE_SVG)).replace("@@DOTS@@", _uri(DOTS_SVG)))


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(provider: str, model: str):
    st.markdown(f"""
<div class="hud hero">
  <div class="scan"></div>
  <div class="hero-title">Enterprise Knowledge Copilot</div>
  <p class="hero-sub">Ask questions across your company documents. Every answer shows where it came from.</p>
  <div class="chips">
    <span class="chip live"><i></i>Online</span>
    <span class="chip">{html.escape(provider)}</span>
    <span class="chip">{html.escape(model)}</span>
  </div>
</div>""", unsafe_allow_html=True)


def stat_cards(docs: int, chunks: int, active: int):
    st.markdown(f"""
<div class="stats">
  <div class="hud stat"><div class="num">{docs}</div><div class="lbl">Documents indexed</div></div>
  <div class="hud stat"><div class="num">{chunks}</div><div class="lbl">Searchable passages</div></div>
  <div class="hud stat"><div class="num">{active}/{docs}</div><div class="lbl">Included in searches</div></div>
</div>""", unsafe_allow_html=True)