import streamlit as st
import json
import os
import subprocess
import base64
from ai_model import generate_quiz, ask_tutor
import streamlit.components.v1 as components

# ---------- DATABASE FUNCTIONS ----------

def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r") as file:
            return json.load(file)
    return {}

def save_users(users_dict):
    with open("users.json", "w") as file:
        json.dump(users_dict, file, indent=4)

st.set_page_config(page_title="Acadence", page_icon="🎓", layout="wide")

def load_performance():
    if os.path.exists("performance.json"):
        with open("performance.json", "r") as file:
            return json.load(file)
    return {}

def save_performance(data):
    with open("performance.json", "w") as file:
        json.dump(data, file, indent=4)

def extract_score(s):
    """Handle both plain number and dict score formats."""
    return s["score"] if isinstance(s, dict) else s

# ---------- SESSION ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None

if "page" not in st.session_state:
    st.session_state.page = "Landing"

if "account_created" not in st.session_state:
    st.session_state.account_created = False

if "users" not in st.session_state:
    st.session_state.users = load_users()

if "performance" not in st.session_state:
    st.session_state.performance = load_performance()

# ══════════════════════════════════════════════════════════════
# PARTICLE SPHERE ANIMATION
# ══════════════════════════════════════════════════════════════
_PARTICLE_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden;background:#050a14}
canvas{position:fixed;top:0;left:0;width:100%;height:100%}
</style></head>
<body><canvas id="c"></canvas>
<script>
const canvas=document.getElementById('c');
const ctx=canvas.getContext('2d');
function resize(){canvas.width=window.innerWidth;canvas.height=window.innerHeight;}
resize();window.addEventListener('resize',resize);
const NUM=200;const pts=[];const phi=Math.PI*(3-Math.sqrt(5));
for(let i=0;i<NUM;i++){
  const y=1-(i/(NUM-1))*2;const r=Math.sqrt(Math.max(0,1-y*y));
  const theta=phi*i;
  pts.push({ox:Math.cos(theta)*r,oy:y,oz:Math.sin(theta)*r,
            sz:Math.random()*1.5+0.8,phase:Math.random()*Math.PI*2});
}
let ax=0,ay=0,tx=0,ty=0,t=0;
window.addEventListener('mousemove',e=>{
  tx=(e.clientY/canvas.height-0.5)*0.8;
  ty=(e.clientX/canvas.width-0.5)*0.5;
});
function rotY(v,a){const c=Math.cos(a),s=Math.sin(a);return[v[0]*c-v[2]*s,v[1],v[0]*s+v[2]*c];}
function rotX(v,a){const c=Math.cos(a),s=Math.sin(a);return[v[0],v[1]*c-v[2]*s,v[1]*s+v[2]*c];}
function draw(){
  t+=0.006;ax+=(tx-ax)*0.03;ay+=(t*0.25+ty-ay)*0.03;
  const W=canvas.width,H=canvas.height,R=Math.min(W,H)*0.35,fov=700;
  ctx.fillStyle='#050a14';ctx.fillRect(0,0,W,H);
  const cg=ctx.createRadialGradient(W/2,H/2,0,W/2,H/2,R*1.15);
  cg.addColorStop(0,'rgba(255,255,255,0.12)');cg.addColorStop(1,'rgba(0,0,0,0)');
  ctx.fillStyle=cg;ctx.fillRect(0,0,W,H);
  const proj=pts.map(p=>{
    let v=[p.ox,p.oy,p.oz];v=rotY(v,ay);v=rotX(v,ax);
    const sc=fov/(fov+v[2]*R);
    return{sx:W/2+v[0]*R*sc,sy:H/2+v[1]*R*sc,sz:v[2],sc,
           depth:(v[2]+1)/2,sz0:p.sz,phase:p.phase};
  });
  for(let i=0;i<NUM;i++){for(let j=i+1;j<NUM;j++){
    const a=pts[i],b=pts[j];
    const dx=a.ox-b.ox,dy=a.oy-b.oy,dz=a.oz-b.oz;
    const dist=Math.sqrt(dx*dx+dy*dy+dz*dz);
    if(dist<0.45){
      const pa=proj[i],pb=proj[j];
      const alpha=(1-dist/0.45)*0.28*((pa.depth+pb.depth)/2);
      if(alpha<0.003)continue;
      ctx.beginPath();ctx.strokeStyle='rgba(255,255,255,'+alpha.toFixed(3)+')';
      ctx.lineWidth=0.8*(pa.sc+pb.sc)/2;
      ctx.moveTo(pa.sx,pa.sy);ctx.lineTo(pb.sx,pb.sy);ctx.stroke();
    }
  }}
  const sorted=proj.map((p,i)=>({...p,i})).sort((a,b)=>a.sz-b.sz);
  sorted.forEach(p=>{
    const pulse=Math.sin(t*2.5+p.phase)*0.25+0.75;
    const size=p.sz0*p.sc*2.5*pulse,alpha=p.depth*0.9+0.1;
    const gr=ctx.createRadialGradient(p.sx,p.sy,0,p.sx,p.sy,size*5);
    gr.addColorStop(0,'rgba(255,255,255,'+(alpha*0.7).toFixed(3)+')');
    gr.addColorStop(0.35,'rgba(200,200,200,'+(alpha*0.2).toFixed(3)+')');
    gr.addColorStop(1,'rgba(150,150,150,0)');
    ctx.beginPath();ctx.fillStyle=gr;ctx.arc(p.sx,p.sy,size*5,0,6.2832);ctx.fill();
    ctx.beginPath();ctx.fillStyle='rgba(255,255,255,'+alpha.toFixed(3)+')';
    ctx.arc(p.sx,p.sy,size*1.1,0,6.2832);ctx.fill();
  });
  requestAnimationFrame(draw);
}
draw();
</script></body></html>"""

_PARTICLE_B64 = base64.b64encode(_PARTICLE_HTML.encode()).decode()


# ══════════════════════════════════════════════════════════════
# PRE-LOGIN CSS FACTORY
# ══════════════════════════════════════════════════════════════
def _get_css(page):
    if page == "Landing":
        top_pad = "padding-top: 0 !important;"
        btn_css = """
        .stButton{
            max-width: 420px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            display: block !important;
        }
        .stButton > button {
            font-size: 15px !important; padding: 10px 30px !important;
            background: rgba(255,255,255,0.95) !important;
            color: #000000 !important; font-weight: 800 !important;
            border: none !important; border-radius: 50px !important;
            letter-spacing: 1.2px !important; text-transform: uppercase !important;
            width: auto !important; white-space: nowrap !important;
            box-shadow: 0 0 32px rgba(255,255,255,.55), 0 0 70px rgba(255,255,255,.2),
                        0 8px 32px rgba(0,0,0,.45) !important;
            transition: all .3s cubic-bezier(.34,1.56,.64,1) !important;
        }
        .stButton > button:hover {
            transform: scale(1.08) translateY(-4px) !important;
            box-shadow: 0 0 60px rgba(255,255,255,.9), 0 0 110px rgba(255,255,255,.35),
                        0 14px 44px rgba(0,0,0,.5) !important;
        }"""
        card_css = ""
    else:
        top_pad = "padding-top: 9vh !important;"
        btn_css = """
        .stButton{
            max-width:420px !important;
            margin-left:auto !important;
            margin-right:auto !important;
            display:flex !important;
        justify-content:center !important;
        }
        .stButton > button {
            font-size: 15px !important; padding: 13px 22px !important;
            background: rgba(255,255,255,0.95) !important;
            color: #000000 !important; font-weight: 700 !important;
            border: none !important; border-radius: 13px !important;
            width: auto !important; margin-bottom: 8px !important;
            box-shadow: 0 0 18px rgba(255,255,255,.35), 0 4px 16px rgba(0,0,0,.4) !important;
            transition: all .25s ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 0 36px rgba(255,255,255,.65), 0 8px 24px rgba(0,0,0,.5) !important;
        }"""
        card_css = """
        [data-testid="column"]:nth-child(2) {
            background: rgba(6,14,42,0.84) !important;
            border: 1px solid rgba(255,255,255,0.13) !important;
            border-radius: 24px !important;
            padding: 44px 40px !important;
            box-shadow: 0 32px 64px rgba(0,0,0,.65),
                        0 0 50px rgba(255,255,255,.05),
                        inset 0 1px 0 rgba(255,255,255,.04) !important;
        }"""

    return f"""<style>
/* ── DESIGN TOKENS ── */
:root {{
    --accent:#ffffff; --accent-glow:rgba(255,255,255,.4);
    --bg:#050a14; --glass:rgba(6,14,42,.84);
    --glass-border:rgba(255,255,255,.13);
    --text:#fff; --muted:#64748b;
    --r-card:24px; --r-input:12px;
}}
/* ── HIDE STREAMLIT CHROME ── */
#MainMenu,footer,[data-testid="stToolbar"],
[data-testid="stDecoration"],[data-testid="stDeployButton"],
header[data-testid="stHeader"] {{ display:none !important; }}
/* ── BACKGROUNDS ── */
body {{ background:var(--bg) !important; }}
.stApp,[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{ background:transparent !important; }}
/* ── BLOCK CONTAINER ── */
.block-container {{
    max-width:1200px !important;
    padding-left:2rem !important; padding-right:2rem !important;
    {top_pad}
}}
/* ── FADE-IN ANIMATION ── */
@keyframes fadeInUp {{
    from {{ opacity:0; transform:translateY(22px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}
.block-container > * {{ animation:fadeInUp .55s cubic-bezier(.16,1,.3,1); }}
/* ── HERO TYPOGRAPHY ── */
.hero-title {{
    font-family:'Inter','Segoe UI',system-ui,sans-serif;
    font-size:clamp(80px,12vw,140px); font-weight:400;
    text-align:left ; color:#fff; letter-spacing:-3px; line-height:1;
    margin:0 0 10px; padding-top:20vh;
    text-shadow:0 0 40px rgba(255,255,255,.75),
                0 0 85px rgba(255,255,255,.35),
                0 0 130px rgba(255,255,255,.2);
}}
.hero-subtitle {{
    font-family:'Inter','Segoe UI',system-ui,sans-serif;
    text-align:left; font-size:clamp(13px,2vw,17px);
    color:rgba(255,255,255,.65); letter-spacing:4px;
    text-transform:uppercase; font-weight:400; margin:0 0 1px;
}}
/* ── FORM HEADER ── */
.form-header {{
    text-align:center; margin-bottom:26px; padding-bottom:22px;
    border-bottom:1px solid rgba(0,212,255,.08);
}}
.form-icon  {{ font-size:36px; margin-bottom:8px; }}
.form-title {{
    color:#fff; font-size:25px; font-weight:700; margin:0 0 5px;
    font-family:'Inter','Segoe UI',system-ui,sans-serif; letter-spacing:-.5px;
}}
.form-subtitle {{ color:var(--muted); font-size:14px; margin:0;
    font-family:'Inter','Segoe UI',system-ui,sans-serif; }}
/* ── BRAND MARK ── */
.brand-mark {{
    position:fixed; top:22px; left:28px; z-index:999;
    font-family:'Inter','Segoe UI',system-ui,sans-serif;
    font-size:20px; font-weight:800; color:rgba(255,255,255,.9);
    text-shadow:0 0 20px rgba(255,255,255,.65); letter-spacing:-.5px;
    pointer-events:none;
}}
/* ── INPUTS ── */
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label {{
    color:rgba(255,255,255,.65) !important; font-size:11.5px !important;
    font-weight:600 !important; letter-spacing:.9px !important;
    text-transform:uppercase !important;
}}
[data-testid="stTextInput"]{{
    max-width:420px !important;
    margin-left:auto !important;
    margin-right:auto !important;
}}
[data-testid="stTextInput"] input,
[data-testid="stTextInput"] > div > div > input {{
    background:rgba(255,255,255,.04) !important;
    border:1px solid rgba(255,255,255,.18) !important;
    border-radius:var(--r-input) !important; color:#fff !important;
    padding:9px 14px !important; font-size:13px !important;
    font-family:'Inter','Segoe UI',system-ui,sans-serif !important;
    transition:all .25s ease !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextInput"] > div > div > input:focus {{
    border-color:var(--accent) !important;
    box-shadow:0 0 0 3px rgba(255,255,255,.14) !important;
    background:rgba(255,255,255,.07) !important; outline:none !important;
}}
div[data-testid="stButton"] {{
    max-width: 420px;
    margin-left: auto;
    margin-right: auto;
}}
/* ── SELECTBOX ── */
[data-testid="stSelectbox"]{{
    max-width:420px !important;
    margin-left:auto !important;
    margin-right:auto !important;
}}
[data-testid="stSelectbox"] > div > div {{
    background:rgba(255,255,255,.04) !important;
    border:1px solid rgba(255,255,255,.18) !important;
    border-radius:var(--r-input) !important; color:#fff !important;
}}
/* ── BUTTONS ── */
{btn_css}
/* ── GLASS CARD ── */
{card_css}
/* ── ALERTS ── */
[data-testid="stAlert"],div[role="alert"] {{
    background:rgba(0,0,0,.35) !important; border-radius:12px !important;
}}
/* ── SCROLLBAR ── */
::-webkit-scrollbar{{width:4px;}}
::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:rgba(255,255,255,.3);border-radius:2px;}}
</style>"""


# ══════════════════════════════════════════════════════════════
# DASHBOARD CSS (post-login) — role-aware design tokens
# ══════════════════════════════════════════════════════════════
def get_dashboard_css(role):
    themes = {
        "Student": {
            "accent":   "#3b82f6",
            "accent2":  "#06b6d4",
            "glow":     "rgba(59,130,246,0.22)",
            "gradient": "linear-gradient(160deg,#060d20 0%,#0c1a30 60%,#050a14 100%)",
            "btn":      "linear-gradient(135deg,#3b82f6,#06b6d4)",
        },
        "Teacher": {
            "accent":   "#8b5cf6",
            "accent2":  "#a78bfa",
            "glow":     "rgba(139,92,246,0.22)",
            "gradient": "linear-gradient(160deg,#0d0920 0%,#150f30 60%,#050a14 100%)",
            "btn":      "linear-gradient(135deg,#8b5cf6,#a78bfa)",
        },
        "Parent": {
            "accent":   "#f59e0b",
            "accent2":  "#fbbf24",
            "glow":     "rgba(245,158,11,0.22)",
            "gradient": "linear-gradient(160deg,#1a0f00 0%,#0f1209 60%,#050a14 100%)",
            "btn":      "linear-gradient(135deg,#f59e0b,#fbbf24)",
        },
    }
    t = themes.get(role, themes["Student"])

    return f"""<style>
/* ─── TOKENS ─── */
:root {{
    --ac:  {t['accent']};
    --ac2: {t['accent2']};
    --glow:{t['glow']};
    --bg:  #050a14;
    --sur: rgba(255,255,255,0.03);
    --sur2:rgba(255,255,255,0.06);
    --brd: rgba(255,255,255,0.08);
    --brd2:rgba(255,255,255,0.16);
    --txt: #f1f5f9;
    --mu:  #64748b;
    --sft: rgba(255,255,255,0.72);
    --r:16px; --rsm:10px; --rlg:24px;
}}
/* ─── HIDE CHROME ─── */
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stDeployButton"],header[data-testid="stHeader"]{{display:none!important;}}
/* ─── BACKGROUND ─── */
.stApp{{background:{t['gradient']}!important;}}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{{background:transparent!important;}}
/* ─── LAYOUT ─── */
.block-container{{padding:2rem 2.5rem!important;max-width:1320px!important;}}
/* ─── SIDEBAR ─── */
section[data-testid="stSidebar"]{{
    background:rgba(4,8,18,0.98)!important;
    border-right:1px solid var(--brd)!important;
}}
section[data-testid="stSidebar"] > div:first-child{{padding-top:0!important;}}
section[data-testid="stSidebar"] p{{color:var(--sft)!important;font-size:13px!important;}}
/* ─── TYPOGRAPHY ─── */
h1,h2,h3,h4{{font-family:'Inter','Segoe UI',system-ui,sans-serif!important;color:var(--txt)!important;letter-spacing:-0.4px!important;}}
p,li,span,label{{font-family:'Inter','Segoe UI',system-ui,sans-serif;}}
/* ─── BUTTONS ─── */
.stButton>button{{
    background:{t['btn']}!important;color:#fff!important;border:none!important;
    border-radius:var(--rsm)!important;font-weight:600!important;font-size:14px!important;
    padding:11px 22px!important;width:100%!important;letter-spacing:.3px!important;
    transition:all .25s ease!important;box-shadow:0 4px 18px {t['glow']}!important;
}}
.stButton>button:hover{{
    transform:translateY(-2px)!important;filter:brightness(1.12)!important;
    box-shadow:0 8px 30px {t['glow']}!important;
}}
.stButton>button:active{{transform:translateY(0)!important;}}
/* ─── INPUTS ─── */
[data-testid="stTextInput"] label,[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label{{
    color:var(--sft)!important;font-size:11px!important;font-weight:600!important;
    letter-spacing:.8px!important;text-transform:uppercase!important;
}}
[data-testid="stTextInput"] input{{
    background:rgba(255,255,255,0.04)!important;border:1px solid var(--brd2)!important;
    border-radius:var(--rsm)!important;color:var(--txt)!important;
    font-family:'Inter',system-ui,sans-serif!important;font-size:14px!important;
    padding:11px 14px!important;transition:all .2s ease!important;
}}
[data-testid="stTextInput"] input:focus{{
    border-color:var(--ac)!important;box-shadow:0 0 0 3px {t['glow']}!important;
    background:rgba(255,255,255,0.06)!important;outline:none!important;
}}
/* ─── SELECTBOX ─── */
[data-testid="stSelectbox"]>div>div{{
    background:rgba(255,255,255,0.04)!important;border:1px solid var(--brd2)!important;
    border-radius:var(--rsm)!important;color:var(--txt)!important;
}}
/* ─── METRICS ─── */
[data-testid="stMetric"]{{
    background:var(--sur)!important;border:1px solid var(--brd)!important;
    border-radius:var(--r)!important;padding:20px 22px!important;
    position:relative!important;overflow:hidden!important;
    transition:border-color .2s!important;
}}
[data-testid="stMetric"]:hover{{border-color:var(--brd2)!important;background:var(--sur2)!important;}}
[data-testid="stMetric"]::before{{
    content:'';position:absolute;top:0;left:0;right:0;height:2px;
    background:linear-gradient(90deg,var(--ac),var(--ac2));
}}
[data-testid="stMetricValue"]{{color:var(--ac)!important;font-size:26px!important;font-weight:700!important;}}
[data-testid="stMetricLabel"]{{color:var(--mu)!important;font-size:11px!important;text-transform:uppercase!important;letter-spacing:.8px!important;}}
/* ─── TABS ─── */
[role="tab"]{{background:transparent!important;color:var(--mu)!important;
    width:auto!important;box-shadow:none!important;border:none!important;
    border-bottom:2px solid transparent!important;font-weight:500!important;
    border-radius:0!important;padding:10px 16px!important;}}
[role="tab"][aria-selected="true"]{{color:var(--ac)!important;
    border-bottom:2px solid var(--ac)!important;background:rgba(255,255,255,.03)!important;}}
[role="tablist"]{{border-bottom:1px solid var(--brd)!important;}}
/* ─── ALERTS ─── */
[data-testid="stAlert"]{{border-radius:var(--rsm)!important;border:1px solid var(--brd)!important;}}
/* ─── CHART ─── */
[data-testid="stVegaLiteChart"]{{border-radius:var(--r)!important;overflow:hidden!important;
    border:1px solid var(--brd)!important;padding:12px!important;background:var(--sur)!important;}}
/* ─── RADIO ─── */
[data-testid="stRadio"] label span{{color:var(--sft)!important;}}
/* ─── DIVIDER ─── */
hr{{border-color:var(--brd)!important;margin:28px 0!important;}}
/* ─── SPINNER ─── */
[data-testid="stSpinner"]{{color:var(--ac)!important;}}
/* ─── SCROLLBAR ─── */
::-webkit-scrollbar{{width:4px;}}
::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:rgba(255,255,255,.2);border-radius:2px;}}
/* ─── ANIMATIONS ─── */
@keyframes fadeInUp{{from{{opacity:0;transform:translateY(18px);}}to{{opacity:1;transform:translateY(0);}}}}
.block-container>*{{animation:fadeInUp .4s cubic-bezier(.16,1,.3,1);}}
@keyframes pulse{{0%,100%{{opacity:1;}}50%{{opacity:.6;}}}}

/* ══════ CUSTOM COMPONENTS ══════ */

/* HERO BANNER */
.hero-banner{{
    background:linear-gradient(135deg,rgba(255,255,255,.04),rgba(255,255,255,.01));
    border:1px solid var(--brd);border-radius:var(--rlg);
    padding:30px 36px;margin-bottom:28px;
    position:relative;overflow:hidden;
}}
.hero-banner::before{{
    content:'';position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,var(--ac),var(--ac2),transparent);
}}
.hero-banner::after{{
    content:'';position:absolute;top:0;right:0;width:260px;height:100%;
    background:radial-gradient(ellipse at right center,{t['glow']},transparent 70%);
    pointer-events:none;
}}
.hero-banner h2{{
    font-size:26px!important;font-weight:700!important;margin:0 0 7px!important;
    background:linear-gradient(90deg,#fff 30%,{t['accent2']});
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
.hero-banner p{{color:var(--mu);font-size:14px;margin:0;line-height:1.6;}}
.role-badge{{
    display:inline-flex;align-items:center;gap:5px;
    background:linear-gradient(135deg,{t['accent']},{t['accent2']});
    color:#fff;font-size:10px;font-weight:700;text-transform:uppercase;
    letter-spacing:1.5px;padding:4px 12px;border-radius:50px;margin-bottom:12px;
}}

/* SECTION LABEL */
.sec-label{{
    font-size:11px;font-weight:700;color:var(--ac);text-transform:uppercase;
    letter-spacing:2px;margin:0 0 16px;display:flex;align-items:center;gap:10px;
}}
.sec-label::after{{content:'';flex:1;height:1px;background:var(--brd);}}

/* QUESTION CARD */
.q-card{{
    background:rgba(255,255,255,.025);border:1px solid var(--brd);
    border-left:3px solid var(--ac);border-radius:var(--r);
    padding:18px 22px;margin-bottom:6px;
}}
.q-num{{font-size:10px;font-weight:700;color:var(--ac);text-transform:uppercase;
    letter-spacing:1.2px;margin-bottom:8px;}}
.q-text{{font-size:15px;color:var(--txt);font-weight:500;line-height:1.55;}}

/* SIDEBAR TOP */
.sb-top{{padding:22px 18px 18px;border-bottom:1px solid var(--brd);margin-bottom:12px;}}
.sb-logo{{font-size:17px;font-weight:800;color:#fff;letter-spacing:-.5px;margin-bottom:18px;}}
.sb-avatar{{
    width:44px;height:44px;
    background:linear-gradient(135deg,{t['accent']},{t['accent2']});
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-size:16px;font-weight:700;color:#fff;margin-bottom:10px;
}}
.sb-name{{font-size:14px;font-weight:600;color:#fff;margin:0 0 3px;}}
.sb-role{{font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:1px;}}
.sb-stat{{
    background:var(--sur);border:1px solid var(--brd);border-radius:var(--rsm);
    padding:12px 14px;margin-top:12px;
}}
.sb-stat-val{{font-size:20px;font-weight:700;color:var(--ac);}}
.sb-stat-lbl{{font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:.8px;}}

/* RECORD CARD */
.rec-card{{
    background:var(--sur);border:1px solid var(--brd);border-radius:var(--r);
    padding:18px 22px;margin-bottom:12px;transition:border-color .2s;
}}
.rec-card:hover{{border-color:var(--brd2);}}
.rec-subj{{font-weight:600;font-size:15px;color:var(--txt);margin-bottom:4px;}}
.rec-meta{{font-size:12px;color:var(--mu);margin-bottom:10px;}}
.rec-hash{{
    font-family:'Courier New',monospace;font-size:11px;color:var(--ac);
    background:rgba(255,255,255,.04);padding:7px 12px;
    border-radius:6px;word-break:break-all;border:1px solid rgba(255,255,255,.06);
}}

/* SCORE PILLS */
.s-high{{display:inline-block;padding:3px 11px;border-radius:50px;font-size:12px;font-weight:700;
    background:rgba(34,197,94,.15);color:#22c55e;border:1px solid rgba(34,197,94,.3);}}
.s-mid{{display:inline-block;padding:3px 11px;border-radius:50px;font-size:12px;font-weight:700;
    background:rgba(245,158,11,.15);color:#f59e0b;border:1px solid rgba(245,158,11,.3);}}
.s-low{{display:inline-block;padding:3px 11px;border-radius:50px;font-size:12px;font-weight:700;
    background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3);}}

/* TOOL CARD (decorative — sits above the button) */
.tool-card{{
    background:rgba(255,255,255,.03);border:1px solid var(--brd);border-radius:var(--r);
    padding:22px 18px 12px;text-align:center;margin-bottom:6px;
    border-top:2px solid var(--ac);
}}
.tc-icon{{font-size:30px;margin-bottom:10px;}}
.tc-title{{font-size:15px;font-weight:700;color:var(--txt);margin-bottom:4px;}}
.tc-sub{{font-size:12px;color:var(--mu);}}

/* INFO CARD */
.info-card{{
    background:var(--sur);border:1px solid var(--brd);border-radius:var(--r);
    padding:20px 22px;margin-bottom:16px;
}}
.info-card h4{{font-size:14px!important;font-weight:600!important;margin:0 0 10px!important;color:var(--ac)!important;}}

/* WEAK TOPIC TAG */
.wtag{{
    display:inline-block;background:rgba(239,68,68,.1);
    border:1px solid rgba(239,68,68,.25);color:#fca5a5;
    border-radius:6px;padding:5px 12px;font-size:12px;
    margin:4px;line-height:1.4;
}}

/* CATEGORY CARD */
.cat-card{{
    border-radius:16px;padding:22px;min-height:200px;
    box-shadow:0 10px 30px rgba(0,0,0,.4);color:#fff;
    position:relative;overflow:hidden;
}}
.cat-card::before{{
    content:'';position:absolute;top:0;right:0;width:80px;height:80px;
    background:rgba(255,255,255,.06);border-radius:50%;
    transform:translate(20px,-20px);
}}
.cat-card h4{{font-size:13px!important;font-weight:700!important;
    text-transform:uppercase;letter-spacing:1.5px;margin:0 0 14px!important;
    color:rgba(255,255,255,.8)!important;}}
.cat-student{{font-size:13px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.1);}}
.cat-student:last-child{{border-bottom:none;}}

/* AI CHAT BUBBLE */
.ai-bubble{{
    background:rgba(255,255,255,.03);border:1px solid var(--brd);
    border-radius:12px 12px 12px 4px;border-left:3px solid var(--ac);
    padding:16px 20px;margin-bottom:16px;color:var(--txt);
    font-size:14px;line-height:1.7;
}}

/* SCORE HISTORY ROW */
.score-row{{
    display:flex;align-items:center;justify-content:space-between;
    padding:12px 16px;border-bottom:1px solid var(--brd);
    font-size:13px;
}}
.score-row:last-child{{border-bottom:none;}}
.score-row .sr-topic{{color:var(--sft);flex:1;}}
.score-row .sr-subject{{color:var(--mu);font-size:11px;margin-left:8px;}}
</style>"""


# ══════════════════════════════════════════════════════════════
# SIDEBAR RENDERER
# ══════════════════════════════════════════════════════════════
def render_sidebar(role, name, perf_data, username):
    initials = "".join([p[0].upper() for p in name.split()[:2]])

    # Sidebar stats
    scores_raw = []
    if username in perf_data and perf_data[username].get("scores"):
        scores_raw = [extract_score(s) for s in perf_data[username]["scores"]]

    avg_display = f"{round(sum(scores_raw)/len(scores_raw),1)}%" if scores_raw else "—"
    count_display = str(len(scores_raw)) if scores_raw else "0"

    role_icons = {"Student": "🎓", "Teacher": "", "Parent": ""}
    icon = role_icons.get(role, "👤")

    st.sidebar.markdown(f"""
<div class="sb-top">
    <div class="sb-logo">🎓 Acadence</div>
    <div class="sb-avatar">{initials}</div>
    <div class="sb-name">{name}</div>
    <div class="sb-role">{icon} {role}</div>
    {f'''<div class="sb-stat">
        <div class="sb-stat-val">{avg_display}</div>
        <div class="sb-stat-lbl">Avg Score</div>
    </div>''' if role == "Student" else ""}
</div>
""", unsafe_allow_html=True)

    st.sidebar.markdown("<div style='padding:0 18px;'>", unsafe_allow_html=True)
    if role == "Student":
        st.sidebar.markdown(f"""
<div style="margin-bottom:8px;">
  <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px;font-weight:600;">Quick Stats</div>
  <div style="display:flex;gap:8px;">
    <div style="flex:1;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:10px;text-align:center;">
      <div style="font-size:18px;font-weight:700;color:var(--ac);">{count_display}</div>
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.6px;">Tests</div>
    </div>
    <div style="flex:1;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:10px;text-align:center;">
      <div style="font-size:18px;font-weight:700;color:var(--ac);">{avg_display}</div>
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.6px;">Avg</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    st.sidebar.markdown("<div style='height:1px;background:rgba(255,255,255,.08);margin:8px 0;'></div>", unsafe_allow_html=True)

    # Logout button
    st.sidebar.markdown("<div style='padding:0 12px 16px;'>", unsafe_allow_html=True)
    if st.sidebar.button("  Sign Out", key="logout_btn"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# HELPER: score pill HTML
# ══════════════════════════════════════════════════════════════
def score_pill(score):
    cls = "s-high" if score >= 75 else ("s-mid" if score >= 45 else "s-low")
    return f'<span class="{cls}">{score}%</span>'


# ══════════════════════════════════════════════════════════════
# PRE-LOGIN UI
# ══════════════════════════════════════════════════════════════
if not st.session_state.logged_in:

    page = st.session_state.page

    st.markdown(
        f'<iframe src="data:text/html;base64,{_PARTICLE_B64}" '
        'style="position:fixed;top:0;left:25vw;width:100vw;height:100vh;'
        'border:none;z-index:-1;pointer-events:none;" width="100%" height="1"></iframe>',
        unsafe_allow_html=True,
    )

    st.markdown(_get_css(page), unsafe_allow_html=True)

    # ── LANDING ─────────────────────────────────────────────
    if page == "Landing":
        st.markdown(
            '<div class="hero-title">Acadence</div>'
            '<div class="hero-subtitle">AI-Powered Academic Intelligence</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='margin-top:40px; margin-left:5vw;'>", unsafe_allow_html=True)
        if st.button("  Join Now", key="join_btn"):
            st.session_state.page = "Login"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── LOGIN ────────────────────────────────────────────────
    elif page == "Login":
        st.markdown('<div class="brand-mark">🎓 Acadence</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([0.9, 1.5])
        with col1:
            st.markdown("""
            <div class="form-header">
                <div class="form-icon"></div>
                <div class="form-title">Welcome Back</div>
                <div class="form-subtitle">Sign in to your Acadence account</div>
            </div>""", unsafe_allow_html=True)

            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            if st.button("Login", key="login_btn"):
                if username in st.session_state.users:
                    stored_user = st.session_state.users[username]
                    if password == stored_user["password"]:
                        st.session_state.logged_in = True
                        st.session_state.role = stored_user["role"]
                        st.session_state.username = username
                        st.session_state.name = stored_user["name"]
                        st.rerun()
                    else:
                        st.error("Incorrect password")
                else:
                    st.error("User not found")

            if st.button("Go to Sign Up →", key="to_signup"):
                st.session_state.page = "Sign Up"
                st.rerun()

    # ── SIGN UP ──────────────────────────────────────────────
    elif page == "Sign Up":
        st.markdown('<div class="brand-mark">🎓 Acadence</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="form-header">
                <div class="form-title">Create Account</div>
                <div class="form-subtitle">Join the Acadence platform today</div>
            </div>""", unsafe_allow_html=True)

            full_name        = st.text_input("Full Name", placeholder="Your full name")
            username         = st.text_input("Choose Username", placeholder="Pick a username")
            new_role         = st.selectbox("Role", ["Student", "Teacher", "Parent"])

            child_username = None
            if new_role == "Parent":
                child_username = st.text_input("Child's Username", placeholder="Enter child's username")

            new_password     = st.text_input("Password", type="password",
                                             placeholder="Create a strong password", key="new_pass")
            confirm_password = st.text_input("Confirm Password", type="password",
                                             placeholder="Repeat your password", key="confirm_pass")
        
            btn_col = st.columns([0.4,2,1])[1]
            with btn_col:

                if st.button("Create Account", key="create_btn"):
                    if not full_name or not username or not new_password or not confirm_password:
                        st.error("Please fill all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    elif username in st.session_state.users:
                        st.error("Username already taken")
                    elif new_role == "Parent" and child_username not in st.session_state.users:
                        st.error("Child username does not exist")
                    else:
                        user_data = {"name": full_name, "password": new_password, "role": new_role}
                        if new_role == "Parent":
                            user_data["child"] = child_username
                        st.session_state.users[username] = user_data
                        save_users(st.session_state.users)
                        st.session_state.account_created = True

            btn_col2 = st.columns([0.4,2,1])[1]
            with btn_col2:
                if st.button("← Back to Login", key="to_login"):
                    st.session_state.account_created = False
                    st.session_state.page = "Login"
                    st.rerun()
                
                if st.session_state.account_created:
                    st.success(" Account created! You can now log in.")


# ══════════════════════════════════════════════════════════════
# POST-LOGIN DASHBOARDS
# ══════════════════════════════════════════════════════════════
else:
    role     = st.session_state.role
    name     = st.session_state.name
    username = st.session_state.username
    perf     = st.session_state.performance

    # Inject role-specific CSS
    st.markdown(get_dashboard_css(role), unsafe_allow_html=True)

    # Render sidebar
    render_sidebar(role, name, perf, username)

    # ════════════════════════════════════════════════════
    # STUDENT DASHBOARD
    # ════════════════════════════════════════════════════
    if role == "Student":

        if "student_tab" not in st.session_state:
            st.session_state.student_tab = "home"

        # ── Hero Banner
        st.markdown(f"""
<div class="hero-banner">
    <div class="role-badge">🎓 Student Portal</div>
    <h2>Welcome back, {name}!</h2>
    <p>Your AI-powered learning journey continues. Stay consistent and keep improving.</p>
</div>
""", unsafe_allow_html=True)

        # ── Academic Overview
        st.markdown('<div class="sec-label"> Academic Overview</div>', unsafe_allow_html=True)

        if username in perf and perf[username].get("scores"):
            scores_raw = [extract_score(s) for s in perf[username]["scores"]]
            avg_score  = round(sum(scores_raw) / len(scores_raw), 2)

            c1, c2, c3 = st.columns(3)
            c1.metric(" Total Assessments", len(scores_raw))
            c2.metric(" Average Score",      f"{avg_score}%")

            if len(scores_raw) >= 2:
                trend     = scores_raw[-1] - scores_raw[-2]
                predicted = max(0, min(100, round(scores_raw[-1] + trend, 2)))
                c3.metric(" AI Predicted Next", f"{predicted}%",
                          delta=f"{'+' if trend>=0 else ''}{round(trend,1)}%")
            else:
                c3.metric(" AI Predicted", "More data needed")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label"> Performance Trend</div>', unsafe_allow_html=True)
            import pandas as pd
            df = pd.DataFrame(scores_raw, columns=["Score (%)"])
            st.line_chart(df)

        else:
            st.markdown("""
<div class="info-card">
    <h4>No Assessment Data Yet</h4>
    <p style="color:#64748b;font-size:13px;margin:0;">
        Complete your first quiz to see your performance analytics here.
    </p>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ── Learning Tools
        st.markdown('<div class="sec-label">🛠 Learning Tools</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("""
<div class="tool-card">
    <div class="tc-icon"></div>
    <div class="tc-title">Quiz Portal</div>
    <div class="tc-sub">Teacher-assigned &amp; practice quizzes</div>
</div>""", unsafe_allow_html=True)
            if st.button("Open Quiz Portal →", key="quiz_btn"):
                st.session_state.student_tab = "quiz"
                st.rerun()

        with c2:
            st.markdown("""
<div class="tool-card">
    <div class="tc-icon"></div>
    <div class="tc-title">AI Tutor</div>
    <div class="tc-sub">Personalized explanations &amp; doubt solving</div>
</div>""", unsafe_allow_html=True)
            if st.button("Open AI Tutor →", key="ai_btn"):
                st.session_state.student_tab = "ai"
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── TAB: Home
        if st.session_state.student_tab == "home":
            st.markdown("""
<div style="text-align:center;padding:40px 20px;color:#64748b;">
    <div style="font-size:40px;margin-bottom:12px;"></div>
    <div style="font-size:15px;font-weight:500;">Select a learning tool above to get started</div>
</div>""", unsafe_allow_html=True)

        # ── TAB: Quiz
        elif st.session_state.student_tab == "quiz":

            st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
    <span style="font-size:24px;"></span>
    <div>
        <div style="font-size:20px;font-weight:700;color:#f1f5f9;">Quiz Portal</div>
        <div style="font-size:13px;color:#64748b;">Attempt assigned or practice quizzes</div>
    </div>
</div>""", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["  Teacher Assigned Quiz", "  Practice Quiz"])

            # ── Teacher Assigned Quiz
            with tab1:
                if os.path.exists("assigned_quizzes.json"):
                    with open("assigned_quizzes.json", "r") as f:
                        assigned_data = json.load(f)
                else:
                    assigned_data = {"quizzes": []}

                class_quizzes = assigned_data.get("quizzes", [])

                if not class_quizzes:
                    st.info("📭 No quiz has been assigned by your teacher yet.")
                else:
                    latest_quiz = class_quizzes[-1]
                    quiz        = latest_quiz["questions"]

                    st.markdown(f"""
<div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);
     border-radius:12px;padding:18px 22px;margin-bottom:20px;">
    <div style="font-size:18px;font-weight:700;color:#f1f5f9;">{latest_quiz['subject']} — {latest_quiz['topic']}</div>
    <div style="font-size:12px;color:#64748b;margin-top:4px;">
        Assigned by <strong style="color:#f1f5f9;">{latest_quiz['created_by']}</strong>
        &nbsp;·&nbsp; {len(quiz)} Questions
    </div>
</div>""", unsafe_allow_html=True)

                    for i, q in enumerate(quiz):
                        st.markdown(f"""
<div class="q-card">
    <div class="q-num">Question {i+1}</div>
    <div class="q-text">{q['question']}</div>
</div>""", unsafe_allow_html=True)
                        st.radio("Select your answer:", q["options"],
                                 key=f"assigned_{i}", index=None,
                                 label_visibility="collapsed")
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

                    if st.button(" Submit Assigned Quiz", key="submit_assigned"):
                        score = 0
                        wrong_topics = []

                        st.markdown("<hr>", unsafe_allow_html=True)
                        st.markdown('<div class="sec-label"> Results</div>', unsafe_allow_html=True)

                        for i, q in enumerate(quiz):
                            selected = st.session_state.get(f"assigned_{i}")
                            question_text = q["question"]

                            if selected is None:
                                st.warning(f"Q{i+1}: Not attempted")
                                wrong_topics.append(question_text)
                            elif selected == q["correct_answer"]:
                                st.success(f"Q{i+1}: ✓ Correct")
                                score += 1
                            else:
                                st.error(f"Q{i+1}: ✗ Wrong  |  Correct: **{q['correct_answer']}**")
                                wrong_topics.append(question_text)

                            if "explanation" in q:
                                st.info(f" {q['explanation']}")

                        percentage = round((score / len(quiz)) * 100, 2)

                        username = st.session_state.username

                        if username not in st.session_state.performance:
                            st.session_state.performance[username] = {
                                "scores": [],
                                "weak_topics": []
                            }

                        st.session_state.performance[username]["scores"].append(percentage)
                        st.session_state.performance[username]["weak_topics"] = wrong_topics

                        save_performance(st.session_state.performance)

                        topic = latest_quiz["topic"]

                        result = subprocess.run(
                            ["node", "blockchain/weil_client.js", username, topic, str(percentage)],
                            capture_output=True, text=True
                        )
                        blockchain_hash = result.stdout.strip() if result.stdout else "No Hash Returned"

                        st.markdown(f"""
<div style="background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);
     border-radius:12px;padding:20px;margin:16px 0;">
    <div style="font-size:13px;color:#22c55e;font-weight:600;margin-bottom:6px;">
         Academic Record Secured on WeilChain
    </div>
    <div style="font-family:monospace;font-size:11px;color:#64748b;word-break:break-all;">
        {blockchain_hash}
    </div>
</div>""", unsafe_allow_html=True)

                        # Save in teacher.json
                        if os.path.exists("teacher.json"):
                            with open("teacher.json", "r") as f:
                                teacher_data = json.load(f)
                        else:
                            teacher_data = {"records": []}

                        teacher_data["records"].append({
                            "teacher_id":       latest_quiz["created_by"],
                            "subject":          latest_quiz["subject"],
                            "topic":            latest_quiz["topic"],
                            "student_name":     name,
                            "score":            percentage,
                            "weak_topics":      wrong_topics,
                            "blockchain_hash":  blockchain_hash
                        })

                        with open("teacher.json", "w") as f:
                            json.dump(teacher_data, f, indent=4)

                        c1, c2 = st.columns(2)
                        c1.metric(" Final Score", f"{percentage}%")
                        c2.metric(" Correct", f"{score}/{len(quiz)}")
                        st.progress(int(percentage))

            # ── Practice Quiz
            with tab2:
                topic = st.text_input(" Enter topic for quiz", placeholder="e.g. Algebra, Photosynthesis…")

                if st.button("⚡ Generate Quiz", key="gen_quiz"):
                    st.session_state.pop("weak_topics", None)
                    with st.spinner("Generating your quiz…"):
                        quiz = generate_quiz(topic)
                    st.session_state.current_quiz = quiz

                if "current_quiz" in st.session_state:
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                    for i, q in enumerate(st.session_state.current_quiz):
                        st.markdown(f"""
<div class="q-card">
    <div class="q-num">Question {i+1}</div>
    <div class="q-text">{q['question']}</div>
</div>""", unsafe_allow_html=True)
                        st.radio("Select your answer:", q["options"],
                                 key=f"q_{i}", index=None,
                                 label_visibility="collapsed")
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

                    if st.button(" Submit Practice Quiz", key="submit_practice"):
                        score        = 0
                        wrong_topics = []

                        st.markdown("<hr>", unsafe_allow_html=True)
                        st.markdown('<div class="sec-label"> Results</div>', unsafe_allow_html=True)

                        for i, q in enumerate(st.session_state.current_quiz):
                            selected      = st.session_state.get(f"q_{i}")
                            question_text = q["question"]

                            if selected is None:
                                st.warning(f"Q{i+1}: Not attempted")
                                wrong_topics.append(question_text)
                            elif selected == q["correct_answer"]:
                                st.success(f"Q{i+1}: ✓ Correct")
                                score += 1
                            else:
                                st.error(f"Q{i+1}: ✗ Wrong  |  Correct: **{q['correct_answer']}**")
                                wrong_topics.append(question_text)

                            if "explanation" in q:
                                st.info(f" {q['explanation']}")

                        if username not in st.session_state.performance:
                            st.session_state.performance[username] = {"scores": [], "weak_topics": []}

                        percentage = round((score / len(st.session_state.current_quiz)) * 100, 2)

                        result = subprocess.run(
                        ["node", "blockchain/weil_client.js", username, topic, str(percentage)],
                        capture_output=True, text=True
                    )
                        blockchain_hash = result.stdout.strip()

                        st.markdown(f"""
<div style="background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);
     border-radius:12px;padding:20px;margin:16px 0;">
    <div style="font-size:13px;color:#22c55e;font-weight:600;margin-bottom:6px;">
         Academic Record Secured on WeilChain
    </div>
    <div style="font-family:monospace;font-size:11px;color:#64748b;word-break:break-all;">
        {blockchain_hash}
    </div>
</div>""", unsafe_allow_html=True)

                        st.session_state.performance[username]["scores"].append({
                            "subject": "Practice",
                            "topic":   topic,
                            "score":   percentage
                        })
                        st.session_state.performance[username]["weak_topics"] = wrong_topics
                        save_performance(st.session_state.performance)

                        c1, c2 = st.columns(2)
                        c1.metric(" Final Score", f"{percentage}%")
                        c2.metric(" Correct", f"{score}/{len(st.session_state.current_quiz)}")
                        st.progress(int(percentage))

        # ── TAB: AI Tutor
        elif st.session_state.student_tab == "ai":

            st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
    <span style="font-size:24px;"></span>
    <div>
        <div style="font-size:20px;font-weight:700;color:#f1f5f9;">AI Tutor</div>
        <div style="font-size:13px;color:#64748b;">Get personalized explanations and solve your doubts</div>
    </div>
</div>""", unsafe_allow_html=True)

            if username in perf and perf[username].get("weak_topics"):
                weak_list = perf[username]["weak_topics"]

                st.markdown('<div class="sec-label">⚠️ Your Weak Areas</div>', unsafe_allow_html=True)

                tags_html = "".join([f'<span class="wtag">🔴 {t}</span>' for t in weak_list])
                st.markdown(f"<div style='margin-bottom:16px;'>{tags_html}</div>", unsafe_allow_html=True)

                for i, t in enumerate(weak_list):
                    if st.button(f" Explain: {t[:60]}…" if len(t) > 60 else f" Explain: {t}",
                                 key=f"weak_{i}"):
                        with st.spinner("Generating explanation…"):
                            explanation = ask_tutor(t)
                        st.markdown(f'<div class="ai-bubble">{explanation}</div>',
                                    unsafe_allow_html=True)
            else:
                st.info(" No weak areas detected yet. Complete a quiz first!")

            st.markdown("<hr>", unsafe_allow_html=True)

            st.markdown('<div class="sec-label"> Ask Anything</div>', unsafe_allow_html=True)
            question = st.text_input("Type your question here…",
                                     placeholder="e.g. Explain Newton's 2nd law")

            if st.button(" Ask AI Tutor", key="ask_tutor_btn"):
                if question:
                    with st.spinner("Thinking…"):
                        answer = ask_tutor(question)
                    st.markdown(f'<div class="ai-bubble"><strong>AI Tutor:</strong><br><br>{answer}</div>',
                                unsafe_allow_html=True)
                else:
                    st.warning("Please enter a question first.")

    # ════════════════════════════════════════════════════
    # TEACHER DASHBOARD
    # ════════════════════════════════════════════════════
    elif role == "Teacher":

        # ── Hero Banner
        st.markdown(f"""
<div class="hero-banner">
    <div class="role-badge"> Teacher Dashboard</div>
    <h2>Hello, {name}!</h2>
    <p>Manage your class, assign AI-powered quizzes, and track student performance in real time.</p>
</div>
""", unsafe_allow_html=True)

        # ── Load data
        if os.path.exists("teacher.json"):
            with open("teacher.json", "r") as f:
                teacher_data = json.load(f)
        else:
            teacher_data = {"records": []}

        if os.path.exists("assigned_quizzes.json"):
            with open("assigned_quizzes.json", "r") as f:
                assigned_data = json.load(f)
        else:
            assigned_data = {"quizzes": []}

        records = teacher_data.get("records", [])

        # ── Assign Quiz Section
        st.markdown('<div class="sec-label">➕ Assign Quiz to Class</div>', unsafe_allow_html=True)

        st.markdown("""
<div style="background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.08);
     border-radius:16px;padding:24px;margin-bottom:6px;">
    <div style="font-size:13px;color:#64748b;margin-bottom:16px;">
        Generate an AI quiz and instantly assign it to all students.
    </div>
</div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            subject_input = st.text_input(" Subject", placeholder="e.g. Mathematics")
        with c2:
            topic_input = st.text_input(" Topic", placeholder="e.g. Quadratic Equations")

        if st.button("⚡ Generate & Assign Quiz", key="assign_quiz"):
            if not subject_input or not topic_input:
                st.warning("⚠️ Please fill in both subject and topic.")
            else:
                with st.spinner("Generating quiz with AI…"):
                    quiz = generate_quiz(subject_input, topic_input)

                assigned_data["quizzes"].append({
                    "quiz_id":    str(len(assigned_data["quizzes"]) + 1),
                    "subject":    subject_input,
                    "topic":      topic_input,
                    "questions":  quiz,
                    "created_by": name
                })

                with open("assigned_quizzes.json", "w") as f:
                    json.dump(assigned_data, f, indent=4)

                st.success(f" Quiz on **{subject_input} — {topic_input}** assigned successfully!")

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Class Performance Overview
        st.markdown('<div class="sec-label"> Class Performance Overview</div>', unsafe_allow_html=True)

        if not records:
            st.markdown("""
<div class="info-card">
    <h4>No Submissions Yet</h4>
    <p style="color:#64748b;font-size:13px;margin:0;">
        Students haven't submitted any quizzes yet. Assign one above to get started.
    </p>
</div>""", unsafe_allow_html=True)
        else:
            avg_score   = sum(r["score"] for r in records) / len(records)
            top_score   = max(r["score"] for r in records)
            bottom_score= min(r["score"] for r in records)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📋 Submissions", len(records))
            c2.metric("📊 Class Average", f"{round(avg_score,1)}%")
            c3.metric("🏆 Top Score", f"{top_score}%")
            c4.metric("📉 Lowest Score", f"{bottom_score}%")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.progress(int(avg_score))
            st.caption(f"Class average: {round(avg_score,1)}%")

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── Student Categories
            st.markdown('<div class="sec-label">🏅 Student Performance Categories</div>',
                        unsafe_allow_html=True)

            best, good, average, below = [], [], [], []
            weak_counter = {}

            for r in records:
                n, s = r["student_name"], r["score"]
                if s >= 80:   best.append(n)
                elif s >= 60: good.append(n)
                elif s >= 40: average.append(n)
                else:         below.append(n)
                for wt in r.get("weak_topics", []):
                    weak_counter[wt] = weak_counter.get(wt, 0) + 1

            def cat_card(col, title, emoji, students, bg, glow_color):
                with col:
                    rows = "".join([
                        f'<div class="cat-student">👤 {s}</div>'
                        for s in list(dict.fromkeys(students))
                    ]) if students else '<div style="opacity:.5;font-size:13px;">No students</div>'
                    st.markdown(f"""
<div class="cat-card" style="background:{bg};box-shadow:0 8px 30px {glow_color};">
    <h4>{emoji} {title}</h4>
    {rows}
</div>""", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            cat_card(c1, "Excellent", "🥇", best,    "#14532d", "rgba(21,128,61,.25)")
            cat_card(c2, "Good",      "🥈", good,    "#7c2d12", "rgba(234,88,12,.25)")
            cat_card(c3, "Average",   "🥉", average, "#713f12", "rgba(202,138,4,.25)")
            cat_card(c4, "Needs Help","⚠️",  below,  "#7f1d1d", "rgba(185,28,28,.25)")

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── Weak Topics
            st.markdown('<div class="sec-label">🔴 Common Weak Topics</div>', unsafe_allow_html=True)

            if weak_counter:
                sorted_topics = sorted(weak_counter.items(), key=lambda x: x[1], reverse=True)
                tags = ""
                for t, count in sorted_topics:
                    tags += f'<span class="wtag">{t} <strong style="color:#ef4444;">({count})</strong></span>'
                st.markdown(f"<div style='margin-bottom:8px;'>{tags}</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#64748b;font-size:13px;">No weak topics identified yet.</div>',
                            unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── Blockchain Records
            st.markdown('<div class="sec-label">🔗 Verified Academic Records</div>',
                        unsafe_allow_html=True)

            for r in records:
                score_val = r.get("score", 0)
                pill_cls  = "s-high" if score_val >= 75 else ("s-mid" if score_val >= 45 else "s-low")

                st.markdown(f"""
<div class="rec-card">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
        <div class="rec-subj">{r.get('subject','N/A')} — {r.get('topic','N/A')}</div>
        <span class="{pill_cls}">{score_val}%</span>
    </div>
    <div class="rec-meta">
        Student: <strong style="color:#f1f5f9;">{r.get('student_name','—')}</strong>
    </div>
    <div class="rec-hash">🔗 {r.get('blockchain_hash','Not Available')}</div>
</div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # PARENT DASHBOARD
    # ════════════════════════════════════════════════════
    elif role == "Parent":

        parent_user  = username
        child_uname  = st.session_state.users[parent_user].get("child")

        if not child_uname:
            st.warning("⚠️ No child linked to your account. Please contact admin.")
            st.stop()

        child_name = st.session_state.users.get(child_uname, {}).get("name", child_uname)

        # ── Hero Banner
        st.markdown(f"""
<div class="hero-banner">
    <div class="role-badge">👨‍👩‍👧 Parent Dashboard</div>
    <h2>Welcome, {name}!</h2>
    <p>
        Monitoring academic progress for
        <strong style="color:#fbbf24;">{child_name}</strong>
        — stay informed and support their learning journey.
    </p>
</div>
""", unsafe_allow_html=True)

        # ── Child Info Card
        st.markdown(f"""
<div style="background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.2);
     border-radius:16px;padding:20px 24px;margin-bottom:24px;
     display:flex;align-items:center;gap:16px;">
    <div style="width:52px;height:52px;background:linear-gradient(135deg,#f59e0b,#fbbf24);
         border-radius:50%;display:flex;align-items:center;justify-content:center;
         font-size:20px;font-weight:700;color:#000;flex-shrink:0;">
        {child_name[:2].upper()}
    </div>
    <div>
        <div style="font-size:17px;font-weight:700;color:#f1f5f9;">{child_name}</div>
        <div style="font-size:12px;color:#64748b;margin-top:2px;">
            Student  ·  Username: <code style="color:#f59e0b;">@{child_uname}</code>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

        if child_uname in perf and perf[child_uname].get("scores"):
            scores_raw = [extract_score(s) for s in perf[child_uname]["scores"]]
            avg_score  = round(sum(scores_raw) / len(scores_raw), 2)
            top_score  = max(scores_raw)
            last_score = scores_raw[-1]

            # ── Metrics
            st.markdown('<div class="sec-label"> Performance Overview</div>', unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📋 Total Tests",    len(scores_raw))
            c2.metric("📊 Average Score",  f"{avg_score}%")
            c3.metric("🏆 Best Score",     f"{top_score}%")
            c4.metric("📌 Latest Score",   f"{last_score}%")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # Progress bar with context
            color = "#22c55e" if avg_score >= 75 else ("#f59e0b" if avg_score >= 50 else "#ef4444")
            status = "Excellent" if avg_score >= 75 else ("Good" if avg_score >= 50 else "Needs Improvement")
            st.markdown(f"""
<div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);
     border-radius:12px;padding:18px 20px;margin-bottom:20px;">
    <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
        <span style="font-size:13px;color:#f1f5f9;font-weight:600;">Overall Performance</span>
        <span style="font-size:13px;color:{color};font-weight:700;">{status}</span>
    </div>
    <div style="background:rgba(255,255,255,.08);border-radius:50px;height:8px;overflow:hidden;">
        <div style="width:{avg_score}%;height:100%;
             background:linear-gradient(90deg,{color},{color}88);border-radius:50px;
             transition:width .5s ease;"></div>
    </div>
    <div style="font-size:11px;color:#64748b;margin-top:8px;">{avg_score}% average across {len(scores_raw)} assessments</div>
</div>""", unsafe_allow_html=True)

            # ── Trend Chart
            st.markdown('<div class="sec-label">📈 Score Trend</div>', unsafe_allow_html=True)
            import pandas as pd

            df = pd.DataFrame(scores_raw, columns=["Score (%)"])
            st.line_chart(df)

            # ── Score History
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">📋 Score History</div>', unsafe_allow_html=True)

            history_rows = ""
            for i, s in enumerate(reversed(perf[child_uname]["scores"])):
                val     = extract_score(s)
                subj    = s.get("subject", "—") if isinstance(s, dict) else "—"
                topic_s = s.get("topic", "—")   if isinstance(s, dict) else "—"
                pill_cls = "s-high" if val >= 75 else ("s-mid" if val >= 45 else "s-low")
                history_rows += f"""
<div class="score-row">
    <span style="color:#64748b;font-size:12px;width:28px;">#{len(scores_raw)-i}</span>
    <span class="sr-topic">{topic_s}</span>
    <span class="sr-subject">{subj}</span>
    <span class="{pill_cls}">{val}%</span>
</div>"""

            st.markdown(f"""
<div style="background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.08);
     border-radius:14px;overflow:hidden;">
    {history_rows}
</div>""", unsafe_allow_html=True)

            # ── Weak Topics
            if perf[child_uname].get("weak_topics"):
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                st.markdown('<div class="sec-label">⚠️ Areas Needing Attention</div>',
                            unsafe_allow_html=True)
                tags = "".join([f'<span class="wtag">🔴 {t}</span>'
                                for t in perf[child_uname]["weak_topics"]])
                st.markdown(f"<div>{tags}</div>", unsafe_allow_html=True)

        else:
            st.markdown(f"""
<div class="info-card">
    <h4>No Assessment Data Yet</h4>
    <p style="color:#64748b;font-size:13px;margin:0;">
        <strong style="color:#f1f5f9;">{child_name}</strong> hasn't completed any quizzes yet.
        Encourage them to take their first quiz!
    </p>
</div>""", unsafe_allow_html=True)
