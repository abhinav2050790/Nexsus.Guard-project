"""Razorpay AI Risk Manager — Chargeback Evidence Responder.

Visual Design: Floney Fintech Dashboard Dark Mode (Nija Works)
─────────────────────────────────────────────────────────────
Palette
  Background    #0F0F12   deep charcoal canvas
  Surface       #17171C   card / panel
  Surface-hi    #1E1E26   elevated / hover surface
  Border        #2A2A38   subtle border
  Violet-500    #7C3AED   primary accent (Floney signature)
  Violet-400    #9D63F7   lighter violet for gradients / hover
  Violet-glow   rgba(124,58,237,.35)  glow / shadow
  Cyan          #22D3EE   secondary data accent (chart fills)
  Green         #10B981   positive / win
  Amber         #F59E0B   warning / review
  Red           #EF4444   negative / skip / danger
  Text-primary  #F0F0FF   near-white
  Text-muted    #8B8BA7   secondary text
  Text-subtle   #52526B   placeholder / disabled

Run:
    .venv\\Scripts\\python.exe -m streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Floney design tokens ─────────────────────────────────────────────────────
FL_BG        = "#0F0F12"
FL_SURFACE   = "#17171C"
FL_SURFACE_H = "#1E1E26"
FL_BORDER    = "#2A2A38"
FL_VIOLET    = "#7C3AED"
FL_VIOLET_L  = "#9D63F7"
FL_VIOLET_D  = "#5B21B6"
FL_CYAN      = "#22D3EE"
FL_GREEN     = "#10B981"
FL_AMBER     = "#F59E0B"
FL_RED       = "#EF4444"
FL_TEXT      = "#F0F0FF"
FL_MUTED     = "#8B8BA7"
FL_SUBTLE    = "#52526B"

TONE_HEX     = {"green": FL_GREEN, "yellow": FL_AMBER, "red": FL_RED}
STRENGTH_TON = {"STRONG": FL_GREEN, "MODERATE": FL_AMBER, "WEAK": FL_RED}

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {{
  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}}
.stApp {{ background: {FL_BG}; }}
.block-container {{ padding: 0 2rem 4rem !important; max-width: 1440px; }}
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
  background: {FL_SURFACE};
  border-right: 1px solid {FL_BORDER};
}}

/* ══════════════════════════════════════════════
   NAVBAR — Floney top bar style
══════════════════════════════════════════════ */
.fl-topbar {{
  position: sticky; top: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 28px;
  background: rgba(15,15,18,.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid {FL_BORDER};
  margin: 0 -2rem 28px;
}}
.fl-brand {{ display: flex; align-items: center; gap: 14px; }}
.fl-logo {{
  width: 42px; height: 42px; border-radius: 12px; flex: 0 0 auto;
  background: linear-gradient(135deg, {FL_VIOLET}, {FL_VIOLET_D});
  display: flex; align-items: center; justify-content: center;
  font-weight: 900; font-size: 18px; color: #fff; letter-spacing: -.02em;
  box-shadow: 0 0 20px rgba(124,58,237,.5), 0 4px 12px rgba(0,0,0,.4);
}}
.fl-appname {{
  font-size: 1.05rem; font-weight: 800; color: {FL_TEXT};
  letter-spacing: -.025em; line-height: 1.2;
}}
.fl-appsub {{
  font-size: .70rem; color: {FL_MUTED}; font-weight: 500; margin-top: 1px;
}}
.fl-nav-chips {{ display: flex; align-items: center; gap: 10px; }}
.fl-chip {{
  font-size: .72rem; font-weight: 700; padding: 6px 14px; border-radius: 999px;
  border: 1px solid; letter-spacing: .02em;
}}
.fl-chip-violet {{
  background: rgba(124,58,237,.15); color: {FL_VIOLET_L};
  border-color: rgba(124,58,237,.35);
}}
.fl-chip-green {{
  background: rgba(16,185,129,.12); color: #34D399;
  border-color: rgba(16,185,129,.30);
  animation: chip-pulse 2.5s ease-in-out infinite;
}}
@keyframes chip-pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.65}} }}

/* ══════════════════════════════════════════════
   SECTION LABELS
══════════════════════════════════════════════ */
.fl-label {{
  font-size: .63rem; font-weight: 800; letter-spacing: .13em;
  text-transform: uppercase; color: {FL_VIOLET_L};
  margin-bottom: 10px; margin-top: 2px;
}}

/* ══════════════════════════════════════════════
   CARDS — Floney glass card style
══════════════════════════════════════════════ */
.fl-card {{
  background: {FL_SURFACE};
  border: 1px solid {FL_BORDER};
  border-radius: 18px;
  padding: 20px 22px;
  box-shadow: 0 4px 24px rgba(0,0,0,.35);
  margin-bottom: 14px;
  transition: border-color .2s;
}}
.fl-card:hover {{ border-color: rgba(124,58,237,.4); }}
.fl-card-glow {{
  border-color: rgba(124,58,237,.4);
  box-shadow: 0 0 0 1px rgba(124,58,237,.2),
              0 4px 24px rgba(0,0,0,.35),
              0 0 40px rgba(124,58,237,.08);
}}
.fl-card-accent {{ border-left: 3px solid {FL_VIOLET}; }}

/* ══════════════════════════════════════════════
   KPI / METRIC CARDS — Floney big-number style
══════════════════════════════════════════════ */
.fl-kpi {{
  background: {FL_SURFACE};
  border: 1px solid {FL_BORDER};
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,.3);
  position: relative; overflow: hidden;
}}
.fl-kpi::before {{
  content:''; position:absolute; top:-30px; right:-20px;
  width:80px; height:80px; border-radius:50%;
  background: radial-gradient(circle, rgba(124,58,237,.15) 0%, transparent 70%);
  pointer-events:none;
}}
.fl-kpi-label {{
  font-size: .62rem; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: {FL_MUTED}; margin-bottom: 7px;
}}
.fl-kpi-value {{
  font-size: 1.65rem; font-weight: 900; color: {FL_TEXT};
  letter-spacing: -.035em; line-height: 1;
}}
.fl-kpi-hint {{ font-size: .70rem; color: {FL_SUBTLE}; margin-top: 5px; }}
.fl-kpi-icon {{
  position: absolute; top: 16px; right: 18px;
  font-size: 1.4rem; opacity: .25;
}}

/* ══════════════════════════════════════════════
   WIN PROBABILITY HERO
══════════════════════════════════════════════ */
.fl-prob-label {{
  font-size: .62rem; font-weight: 800; letter-spacing: .13em;
  text-transform: uppercase; color: {FL_MUTED}; margin-bottom: 6px;
}}
.fl-prob-number {{
  font-size: 4rem; font-weight: 900; letter-spacing: -.05em; line-height: 1;
}}
.fl-prob-sub {{
  font-size: .80rem; color: {FL_MUTED}; font-weight: 500; margin-top: 4px;
}}

/* ══════════════════════════════════════════════
   BADGES / PILLS
══════════════════════════════════════════════ */
.fl-badge {{
  display: inline-flex; align-items: center; gap: 5px;
  font-size: .74rem; font-weight: 800; padding: 6px 16px;
  border-radius: 999px; letter-spacing: .04em; text-transform: uppercase;
}}
.b-green  {{ background:rgba(16,185,129,.15); color:#34D399; border:1px solid rgba(16,185,129,.35); }}
.b-yellow {{ background:rgba(245,158,11,.15); color:#FCD34D; border:1px solid rgba(245,158,11,.35); }}
.b-red    {{ background:rgba(239,68,68,.15);  color:#F87171; border:1px solid rgba(239,68,68,.35); }}
.b-violet {{ background:rgba(124,58,237,.18); color:{FL_VIOLET_L}; border:1px solid rgba(124,58,237,.40); }}
.b-cyan   {{ background:rgba(34,211,238,.12); color:#67E8F9; border:1px solid rgba(34,211,238,.30); }}
.b-gray   {{ background:rgba(82,82,107,.15);  color:{FL_MUTED}; border:1px solid rgba(82,82,107,.30); }}

/* ══════════════════════════════════════════════
   EVIDENCE CHECKLIST — Floney row style
══════════════════════════════════════════════ */
.fl-check {{
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 12px;
  font-size: .83rem; color: {FL_TEXT};
  background: rgba(30,30,38,.7);
  border: 1px solid {FL_BORDER};
  margin-bottom: 8px;
  transition: border-color .15s;
}}
.fl-check:hover {{ border-color: rgba(124,58,237,.35); }}
.fl-check .ic {{
  width: 22px; height: 22px; border-radius: 50%;
  font-size: .65rem; font-weight: 900;
  display: flex; align-items: center; justify-content: center; flex: 0 0 auto;
}}
.fl-check.ok   .ic {{ background:rgba(16,185,129,.18); color:#34D399; }}
.fl-check.miss .ic {{ background:rgba(239,68,68,.15); color:#F87171; }}
.fl-check .lbl {{ font-weight: 600; color: {FL_TEXT}; }}
.fl-check .tag {{
  margin-left: auto; font-size: .62rem; font-weight: 700;
  color: {FL_SUBTLE}; text-transform: uppercase; letter-spacing: .08em;
}}

/* ══════════════════════════════════════════════
   FACTOR ROWS
══════════════════════════════════════════════ */
.fl-factor {{
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 12px;
  font-size: .82rem; margin-bottom: 8px; border: 1px solid;
}}
.f-up   {{ background:rgba(16,185,129,.07); border-color:rgba(16,185,129,.22); color:#6EE7B7; }}
.f-down {{ background:rgba(239,68,68,.07);  border-color:rgba(239,68,68,.22);  color:#FCA5A5; }}
.fl-factor b {{ font-family: 'Courier New', monospace; font-size: .78rem; font-weight: 700; }}
.fl-arrow {{ font-weight: 900; font-size: .95rem; }}

/* ══════════════════════════════════════════════
   PROGRESS / GAUGE
══════════════════════════════════════════════ */
.fl-progress {{
  height: 10px; background: rgba(42,42,56,.8);
  border-radius: 999px; overflow: hidden; margin: 10px 0 8px;
}}
.fl-progress-fill {{ height: 100%; border-radius: 999px; }}

/* ══════════════════════════════════════════════
   EXPLANATION QUOTE
══════════════════════════════════════════════ */
.fl-quote {{
  border-left: 3px solid {FL_VIOLET};
  background: rgba(124,58,237,.07);
  padding: 14px 18px; border-radius: 0 12px 12px 0;
  font-size: .88rem; line-height: 1.65; color: {FL_TEXT};
}}

/* ══════════════════════════════════════════════
   DIVIDER
══════════════════════════════════════════════ */
.fl-divider {{ height:1px; background:{FL_BORDER}; margin:16px 0; }}

/* ══════════════════════════════════════════════
   FOOTER
══════════════════════════════════════════════ */
.fl-footer {{
  text-align:center; color:{FL_SUBTLE}; font-size:.68rem;
  margin-top:40px; padding-top:18px; border-top:1px solid {FL_BORDER};
  line-height:1.9;
}}
.fl-footer a {{ color:{FL_VIOLET_L}; text-decoration:none; font-weight:700; }}

/* ══════════════════════════════════════════════
   TABS — Floney pill tabs
══════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {{
  gap: 6px; background: transparent; padding: 0 0 0;
  border-bottom: 1px solid {FL_BORDER}; margin-bottom: 20px;
}}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{ display: none; }}
.stTabs [data-baseweb="tab"] {{
  background: transparent; border: 1px solid transparent;
  padding: 10px 22px; border-radius: 10px 10px 0 0;
  font-size: .86rem; font-weight: 700; color: {FL_MUTED};
  transition: all .15s;
}}
.stTabs [data-baseweb="tab"]:hover {{
  background: rgba(124,58,237,.08); color: {FL_VIOLET_L};
  border-color: rgba(124,58,237,.25);
}}
.stTabs [aria-selected="true"] {{
  background: linear-gradient(135deg, {FL_VIOLET}, {FL_VIOLET_D}) !important;
  color: #fff !important; font-weight: 800;
  border-color: {FL_VIOLET} !important;
  box-shadow: 0 0 20px rgba(124,58,237,.45), 0 -2px 0 {FL_VIOLET};
}}

/* ══════════════════════════════════════════════
   FORM INPUTS — dark glass style
══════════════════════════════════════════════ */
div[data-testid="stDateInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
  background: {FL_SURFACE_H} !important;
  color: {FL_TEXT} !important;
  border: 1px solid {FL_BORDER} !important;
  border-radius: 10px; font-size: .87rem;
}}
div[data-testid="stTextArea"] textarea {{
  background: {FL_SURFACE_H} !important;
  color: {FL_TEXT} !important;
  border: 1px solid {FL_BORDER} !important;
  border-radius: 12px;
}}
div[data-baseweb="select"] > div {{
  background: {FL_SURFACE_H} !important;
  border: 1px solid {FL_BORDER} !important;
  color: {FL_TEXT} !important; border-radius: 10px;
}}
div[data-testid="stFileUploaderDropzone"] {{
  border-radius: 14px; background: {FL_SURFACE} !important;
  border: 2px dashed {FL_BORDER} !important;
}}
div[data-testid="stForm"] {{ border: none !important; }}
label[data-testid="stWidgetLabel"] p {{
  color: {FL_MUTED} !important; font-size: .83rem; font-weight: 600;
}}
div[data-testid="stCheckbox"] label {{
  color: {FL_TEXT} !important; font-weight: 600;
}}

/* ══════════════════════════════════════════════
   BUTTONS — Floney gradient CTA
══════════════════════════════════════════════ */
.stButton > button {{
  border-radius: 12px; font-weight: 800; font-size: .9rem;
  padding: .6rem 1.2rem; border: none; transition: all .2s; letter-spacing:.01em;
}}
.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, {FL_VIOLET}, {FL_VIOLET_D});
  color: #fff;
  box-shadow: 0 4px 20px rgba(124,58,237,.45), 0 2px 6px rgba(0,0,0,.3);
}}
.stButton > button[kind="primary"]:hover {{
  box-shadow: 0 6px 28px rgba(124,58,237,.65);
  transform: translateY(-2px);
}}
.stButton > button[kind="secondary"] {{
  background: {FL_SURFACE_H};
  color: {FL_VIOLET_L};
  border: 1px solid rgba(124,58,237,.4) !important;
}}
.stDownloadButton > button {{
  border-radius: 12px; font-weight: 800;
  background: rgba(124,58,237,.12) !important;
  color: {FL_VIOLET_L} !important;
  border: 1px solid rgba(124,58,237,.40) !important;
  transition: all .2s;
}}
.stDownloadButton > button:hover {{
  background: rgba(124,58,237,.22) !important;
  box-shadow: 0 4px 16px rgba(124,58,237,.35);
}}

/* ══════════════════════════════════════════════
   MISC
══════════════════════════════════════════════ */
[data-testid="stDataFrame"] {{
  border: 1px solid {FL_BORDER} !important;
  border-radius: 12px; overflow: hidden;
}}
.fl-note {{ font-size: .75rem; color: {FL_MUTED}; }}
.fl-grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.fl-grid4 {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
</style>
"""

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nexsus.Guard",
    page_icon="🛡️",
    layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)

LABELS = {
    "is_3ds_verified":           "3-D Secure Verified",
    "avs_match":                 "Address (AVS) Match",
    "cvv_match":                 "CVV Match",
    "has_delivery_confirmation": "Delivery Confirmation",
    "has_signed_receipt":        "Signed Proof of Delivery",
    "has_login_after_purchase":  "Post-Purchase Login",
    "has_support_interaction":   "Support Interaction",
    "order_confirmation_sent":   "Order Confirmation Sent",
    "refund_policy_acknowledged":"Refund Policy Accepted",
}

# ── Component helpers ─────────────────────────────────────────────────────────
def label(text: str) -> None:
    st.markdown(f'<div class="fl-label">{text}</div>', unsafe_allow_html=True)

def kpi(icon: str, title: str, value: str,
        hint: str = "", color: str = FL_TEXT) -> str:
    return (
        f'<div class="fl-kpi">'
        f'<div class="fl-kpi-icon">{icon}</div>'
        f'<div class="fl-kpi-label">{title}</div>'
        f'<div class="fl-kpi-value" style="color:{color}">{value}</div>'
        f'<div class="fl-kpi-hint">{hint}</div>'
        f'</div>'
    )

def check_row(lbl: str, found: bool, tag: str = "") -> str:
    cls  = "ok"  if found else "miss"
    ic   = "✓"   if found else "✕"
    tag_h = f'<span class="tag">{tag}</span>' if tag else ""
    return (
        f'<div class="fl-check {cls}">'
        f'<span class="ic">{ic}</span>'
        f'<span class="lbl">{lbl}</span>{tag_h}</div>'
    )

def factor_row(name: str, pts: float, up: bool) -> str:
    arrow = (f'<span class="fl-arrow" style="color:{FL_GREEN}">▲</span>'
             if up else
             f'<span class="fl-arrow" style="color:{FL_RED}">▼</span>')
    sign, cls = ("+", "f-up") if up else ("", "f-down")
    return (
        f'<div class="fl-factor {cls}">{arrow}'
        f'<b>{name}</b>'
        f'<span style="margin-left:auto;font-weight:900">'
        f'{sign}{pts:.0f} pts</span></div>'
    )

def strength_badge(s: str) -> str:
    cls = {"STRONG":"b-green","MODERATE":"b-yellow","WEAK":"b-red"}.get(s,"b-gray")
    return (f'<span class="fl-badge {cls}">{s}</span>'
            f' <span class="fl-note">evidence package</span>')

def plotly_fl(fig: go.Figure, title: str = "") -> go.Figure:
    """Floney dark-glass Plotly theme."""
    fig.update_layout(
        title=dict(text=title,
                   font=dict(size=13, color=FL_TEXT, family="Plus Jakarta Sans"),
                   x=0),
        template="plotly_dark",
        height=310,
        margin=dict(l=8, r=8, t=42, b=8),
        font=dict(family="Plus Jakarta Sans", size=11, color=FL_MUTED),
        paper_bgcolor=FL_SURFACE,
        plot_bgcolor=FL_SURFACE,
        legend=dict(bgcolor=FL_SURFACE_H, bordercolor=FL_BORDER,
                    borderwidth=1, font=dict(size=10, color=FL_MUTED)),
    )
    fig.update_xaxes(gridcolor=FL_BORDER, linecolor=FL_BORDER,
                     zerolinecolor=FL_BORDER)
    fig.update_yaxes(gridcolor=FL_BORDER, linecolor=FL_BORDER,
                     zerolinecolor=FL_BORDER)
    return fig


# ── Model loading ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading model …")
def get_pipeline():
    import yaml
    from api.routes import load_artifacts, state
    with open(PACKAGE_DIR / "config.yaml", "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    load_artifacts()
    return state, config

@st.cache_data(show_spinner="Running test-set evaluation …")
def get_eval():
    sys.path.insert(0, str(PACKAGE_DIR / "dashboard"))
    from eval_utils import evaluate_everything
    return evaluate_everything(PACKAGE_DIR)

def analyze_one(payload: dict) -> dict:
    from api.routes import LETTER_CACHE
    from api.schemas import ChargebackInput
    from api.routes import analyze as _analyze
    result = _analyze(ChargebackInput(**payload)).model_dump()
    docx   = LETTER_CACHE.get(result["chargeback_id"], b"")
    return {"result": result, "docx": docx}

state, config = get_pipeline()
thr = config["thresholds"]

# ════════════════════════════════════════════════
# TOP BAR
# ════════════════════════════════════════════════
st.markdown(
    f"""
    <div class="fl-topbar">
      <div class="fl-brand">
        <div class="fl-logo">R</div>
        <div>
          <div class="fl-appname">Nexsus.Guard</div>
          <div class="fl-appsub">AI Risk Manager &nbsp;·&nbsp; Chargeback Evidence Responder</div>
        </div>
      </div>
      <div class="fl-nav-chips">
        <span class="fl-chip fl-chip-violet">XGBoost · SHAP</span>
        <span class="fl-chip fl-chip-violet">
          Threshold&nbsp;<b>{state.trainer.recommended_threshold_:.2f}</b>
        </span>
        <span class="fl-chip fl-chip-green">&#x25CF;&nbsp; Model online</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════
t1, t2, t3, t4 = st.tabs([
    "⚖️  Analyze Case",
    "📊  Model Performance",
    "📂  Batch Scoring",
    "🕒  History",
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — ANALYZE
# ══════════════════════════════════════════════════════════════
with t1:
    left, right = st.columns([1, 1.35], gap="large")

    with left:
        label("Transaction details")
        c1, c2 = st.columns(2)
        cb_id        = c1.text_input("Chargeback ID", "CHB-2026-000001")
        txn_id       = c2.text_input("Transaction ID", "TXN-2026-000001")
        txn_date     = st.date_input("Transaction date",
                                      value=date.today() - timedelta(days=21))
        amount       = st.number_input("Amount (₹)", min_value=1.0,
                                        value=12500.0, step=100.0)
        c3, c4 = st.columns(2)
        pay_method = c3.selectbox("Payment method",
            ["card_credit","card_debit","upi","netbanking","wallet"],
            format_func=lambda x: {"card_credit":"💳 Credit Card",
                                    "card_debit": "💳 Debit Card",
                                    "upi":        "📱 UPI",
                                    "netbanking": "🏦 Net Banking",
                                    "wallet":     "👛 Wallet"}[x])
        merchant_cat = c4.selectbox("Merchant category",
            ["electronics","fashion","travel","food","grocery",
             "education","healthcare","gaming","subscription","other"])
        reason_code = st.selectbox("Chargeback reason code",
            ["CB001","CB002","CB003","CB004"],
            format_func=lambda c: {
                "CB001":"CB001 — Unauthorized Transaction",
                "CB002":"CB002 — Item Not Received",
                "CB003":"CB003 — Not as Described",
                "CB004":"CB004 — Friendly Fraud"}[c])
        c5, c6 = st.columns(2)
        merchant_name = c5.text_input("Merchant name", "TechNova Retail Pvt Ltd")
        customer_name = c6.text_input("Customer name", "Ravi Kumar")
        deadline_date = st.date_input("Response deadline",
                                       value=date.today() + timedelta(days=2))

        st.markdown('<div class="fl-divider"></div>', unsafe_allow_html=True)
        label("Customer profile")
        acct_age    = st.slider("Account age (days)", 0, 2000, 890)
        prev_orders = st.slider("Previous orders", 0, 200, 34)
        prev_cbs    = st.slider("Previous chargebacks", 0, 10, 0)

        st.markdown('<div class="fl-divider"></div>', unsafe_allow_html=True)
        label("Verification signals")
        v1, v2, v3 = st.columns(3)
        three_ds = v1.checkbox("3DS verified", True)
        avs      = v2.checkbox("AVS match",    True)
        cvv      = v3.checkbox("CVV match",    True)

        st.markdown('<div class="fl-divider"></div>', unsafe_allow_html=True)
        label("Evidence on file")
        e1, e2 = st.columns(2)
        delivery     = e1.checkbox("Delivery confirmation", True)
        signed       = e1.checkbox("Signed receipt",        False)
        login_after  = e1.checkbox("Post-purchase login",   True)
        support      = e2.checkbox("Support interaction",   False)
        confirm_sent = e2.checkbox("Confirmation sent",     True)
        policy_ack   = e2.checkbox("Policy acknowledged",   True)

        st.markdown('<div class="fl-divider"></div>', unsafe_allow_html=True)
        submit = st.button("⚖️  Analyze Chargeback",
                            type="primary", use_container_width=True)

    payload = {
        "chargeback_id": cb_id, "transaction_id": txn_id,
        "transaction_date": txn_date, "amount_inr": float(amount),
        "payment_method": pay_method, "merchant_category": merchant_cat,
        "chargeback_reason_code": reason_code, "merchant_name": merchant_name,
        "customer_name": customer_name, "deadline_date": deadline_date,
        "customer_account_age_days": acct_age,
        "previous_orders_count": prev_orders,
        "previous_chargebacks_count": prev_cbs,
        "is_3ds_verified": three_ds, "avs_match": avs, "cvv_match": cvv,
        "has_delivery_confirmation": delivery, "has_signed_receipt": signed,
        "has_login_after_purchase": login_after,
        "has_support_interaction": support,
        "order_confirmation_sent": confirm_sent,
        "refund_policy_acknowledged": policy_ack,
    }

    if submit:
        try:
            with st.spinner("Scoring · auditing evidence · drafting rebuttal …"):
                out = analyze_one(payload)
            res  = out["result"]
            pct  = res["win_probability"] * 100
            hexc = TONE_HEX[res["recommendation_color"]]
            bcls = {"FIGHT":"b-green","REVIEW":"b-yellow","SKIP":"b-red"}[
                res["recommendation"]]

            with right:
                # ── Win probability hero card ──────────────────────────────
                glow_color = {
                    "FIGHT": "rgba(16,185,129,.20)",
                    "REVIEW":"rgba(245,158,11,.15)",
                    "SKIP":  "rgba(239,68,68,.15)",
                }[res["recommendation"]]
                st.markdown(
                    f"""
                    <div class="fl-card fl-card-glow" style="
                         background:linear-gradient(135deg,
                           {FL_SURFACE} 60%,
                           {glow_color} 100%);
                         border-radius:20px; padding:24px 26px;">
                      <div style="display:flex;justify-content:space-between;
                                  align-items:flex-start;margin-bottom:18px">
                        <div>
                          <div class="fl-prob-label">Win probability</div>
                          <div class="fl-prob-number" style="color:{hexc}">
                            {pct:.0f}%
                          </div>
                          <div class="fl-prob-sub">
                            {res['confidence_label']} confidence
                            &nbsp;·&nbsp; {res['chargeback_id']}
                          </div>
                        </div>
                        <span class="fl-badge {bcls}" style="font-size:.82rem;padding:9px 22px">
                          {res['recommendation']}
                        </span>
                      </div>
                      <div class="fl-grid2">
                        {kpi('💰','Estimated recovery',
                              f"₹{{res['estimated_recovery_inr']:,.0f}}",
                              '80% of transaction value', FL_GREEN)}
                        {kpi('⚠️','Cost if lost',
                              f"₹{{res['false_positive_cost_inr']:,.0f}}",
                              'fees + response effort', FL_AMBER)}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if res["deadline_warning"]:
                    st.warning(
                        f"⏰  {res['deadline_warning']} — "
                        "Submit early; banks rarely extend windows."
                    )

                # ── Evidence audit ─────────────────────────────────────────
                st.markdown('<div class="fl-card">', unsafe_allow_html=True)
                label("Evidence audit")
                tier = {
                    "is_3ds_verified":"tier 1","avs_match":"tier 1",
                    "cvv_match":"tier 1","has_delivery_confirmation":"tier 1",
                    "has_signed_receipt":"supporting",
                    "has_login_after_purchase":"supporting",
                    "has_support_interaction":"supporting",
                    "order_confirmation_sent":"routine",
                    "refund_policy_acknowledged":"routine",
                }
                ca, cb_col = st.columns(2)
                with ca:
                    st.markdown(
                        "".join(check_row(LABELS[k], payload[k], tier.get(k,""))
                                for k in ["is_3ds_verified","avs_match","cvv_match",
                                          "has_delivery_confirmation","has_signed_receipt"]),
                        unsafe_allow_html=True)
                with cb_col:
                    st.markdown(
                        "".join(check_row(LABELS[k], payload[k], tier.get(k,""))
                                for k in ["has_login_after_purchase",
                                          "has_support_interaction",
                                          "order_confirmation_sent",
                                          "refund_policy_acknowledged"]),
                        unsafe_allow_html=True)

                fill = min(res["evidence_completeness_pct"], 100)
                bar_c = (FL_GREEN if fill > 70
                         else FL_AMBER if fill >= 40 else FL_RED)
                st.markdown(
                    f'<div class="fl-progress">'
                    f'<div class="fl-progress-fill" '
                    f'style="width:{fill}%;background:linear-gradient('
                    f'90deg,{bar_c},{bar_c}88)"></div></div>'
                    f'{strength_badge(res["evidence_strength"])}',
                    unsafe_allow_html=True,
                )
                if res["missing_critical_evidence"]:
                    missing = ", ".join(
                        LABELS.get(m, m) for m in res["missing_critical_evidence"])
                    st.error(
                        f"🔴 Tier-1 gaps (banks weight these highest): "
                        f"**{missing}** — obtain before filing."
                    )
                st.markdown("</div>", unsafe_allow_html=True)

                # ── SHAP explanation ───────────────────────────────────────
                st.markdown(
                    f'<div class="fl-card">'
                    f'<div class="fl-label">Why this score</div>'
                    f'<div class="fl-quote">{res["explanation_text"]}</div>',
                    unsafe_allow_html=True)
                f1c, f2c = st.columns(2)
                f1c.markdown(
                    '<div class="fl-label" style="margin-top:12px">'
                    'Working in your favour</div>',
                    unsafe_allow_html=True)
                f1c.markdown(
                    "".join(factor_row(f["feature"],
                                       abs(f.get("pct_points",0)), True)
                            for f in res["top_positive_factors"][:3])
                    or f'<div class="fl-note">Nothing significant.</div>',
                    unsafe_allow_html=True)
                f2c.markdown(
                    '<div class="fl-label" style="margin-top:12px">'
                    'Working against you</div>',
                    unsafe_allow_html=True)
                f2c.markdown(
                    "".join(factor_row(f["feature"],
                                       abs(f.get("pct_points",0)), False)
                            for f in res["top_negative_factors"][:3])
                    or f'<div class="fl-note">No material risk factors.</div>',
                    unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # ── Rebuttal letter ────────────────────────────────────────
                st.markdown(
                    '<div class="fl-card">'
                    '<div class="fl-label">Rebuttal letter — ready to file</div>',
                    unsafe_allow_html=True)
                st.text_area("", res["letter_preview"], height=160,
                             disabled=True, label_visibility="collapsed")
                st.download_button(
                    "📥  Download Rebuttal Letter (.docx)",
                    data=out["docx"],
                    file_name=f"rebuttal_{res['chargeback_id']}.docx",
                    mime=("application/vnd.openxmlformats-officedocument"
                          ".wordprocessingml.document"),
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
    else:
        with right:
            st.markdown(
                f"""
                <div class="fl-card" style="border-style:dashed;text-align:center;
                     padding:64px 24px;">
                  <div style="font-size:3rem;margin-bottom:14px;
                       filter:drop-shadow(0 0 18px {FL_VIOLET})">⚖️</div>
                  <div style="font-size:1.1rem;font-weight:800;color:{FL_TEXT};
                       margin-bottom:8px;letter-spacing:-.02em">No case loaded</div>
                  <div style="color:{FL_MUTED};font-size:.86rem;line-height:1.7;
                       max-width:280px;margin:0 auto">
                    Fill in the form and click <b style="color:{FL_VIOLET_L}">
                    Analyze Chargeback</b> — get a win probability score, evidence
                    audit and a ready-to-file rebuttal letter in under a second.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════
# TAB 2 — MODEL PERFORMANCE
# ══════════════════════════════════════════════════════════════
with t2:
    ev = get_eval()
    m  = ev["metrics"]
    cm = m["confusion_matrix"]

    # ── KPI strip ──────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5, gap="small")
    with k1:
        st.markdown(kpi("🎯","Precision", f"{m['precision']:.3f}",
                        "of FIGHT decisions won"), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi("🔍","Recall", f"{m['recall']:.3f}",
                        "of winnable cases caught"), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi("⚡","F1 Score", f"{m['f1_score']:.3f}",
                        "harmonic mean"), unsafe_allow_html=True)
    with k4:
        st.markdown(kpi("📈","ROC-AUC", f"{m['roc_auc_score']:.3f}",
                        "discrimination ability"), unsafe_allow_html=True)
    with k5:
        st.markdown(kpi("💹","ROI", f"+{m['roi_percent']:,.0f}%",
                        "net recovery vs cost", FL_GREEN), unsafe_allow_html=True)

    st.markdown(
        f'<div class="fl-note" style="margin:8px 0 20px">'
        f'Test set: <b>{m["n_samples"]:,}</b> cases &nbsp;·&nbsp; '
        f'Threshold: <b>{m["threshold"]:.2f}</b> &nbsp;·&nbsp; '
        f'Base win rate: <b>{m["base_win_rate"]:.0%}</b></div>',
        unsafe_allow_html=True)

    st.markdown('<div class="fl-divider"></div>', unsafe_allow_html=True)

    # ── Charts ─────────────────────────────────────────────────
    g1, g2 = st.columns(2)

    fig_roc = go.Figure()
    fig_roc.add_trace(go.Scatter(
        x=ev["fpr"], y=ev["tpr"], mode="lines",
        name=f"AUC {m['roc_auc_score']:.4f}",
        line=dict(color=FL_VIOLET, width=3),
        fill="tozeroy",
        fillcolor=f"rgba(124,58,237,.12)",
    ))
    fig_roc.add_trace(go.Scatter(
        x=[0,1], y=[0,1], mode="lines", name="Random",
        line=dict(dash="dot", color=FL_SUBTLE, width=1.5),
    ))
    g1.plotly_chart(plotly_fl(fig_roc, "ROC Curve"), use_container_width=True)

    fig_pr = go.Figure()
    fig_pr.add_trace(go.Scatter(
        x=ev["recall_curve"], y=ev["precision_curve"], mode="lines",
        name=f"AP {m['average_precision_score']:.4f}",
        line=dict(color=FL_CYAN, width=3),
        fill="tozeroy", fillcolor="rgba(34,211,238,.10)",
    ))
    g2.plotly_chart(plotly_fl(fig_pr, "Precision–Recall Curve"),
                    use_container_width=True)

    g3, g4 = st.columns(2)

    fig_cost = go.Figure()
    fig_cost.add_trace(go.Scatter(
        x=ev["thresholds"],
        y=np.array(ev["total_costs"]) / 1e6,
        mode="lines", name="Total cost (₹M)",
        line=dict(color=FL_RED, width=3),
        fill="tozeroy", fillcolor="rgba(239,68,68,.08)",
    ))
    fig_cost.add_vline(
        x=ev["best_threshold"], line_dash="dot", line_color=FL_VIOLET,
        annotation_text=f"min ₹{min(ev['total_costs'])/1e6:.2f}M "
                        f"@ {ev['best_threshold']:.2f}",
        annotation_font_color=FL_VIOLET_L,
    )
    g3.plotly_chart(
        plotly_fl(fig_cost, "Business Cost vs Threshold (₹M)"),
        use_container_width=True)

    imp = list(ev["importance"].items())[:12][::-1]
    colours = [FL_VIOLET if i >= len(imp)//2 else FL_VIOLET_L
               for i in range(len(imp))]
    fig_imp = go.Figure(go.Bar(
        x=[v for _, v in imp], y=[k for k, _ in imp],
        orientation="h",
        marker=dict(color=colours, opacity=.9),
    ))
    g4.plotly_chart(
        plotly_fl(fig_imp, "Feature Importance (mean |SHAP|)"),
        use_container_width=True)

    st.markdown('<div class="fl-divider"></div>', unsafe_allow_html=True)

    label("Cost analysis — test set")
    cost_df = pd.DataFrame([
        ("True wins fought (TP)",                  f"{cm['TP']:,}"),
        ("False positives — fought but lost",       f"{cm['FP']:,}"),
        ("False negatives — skipped but winnable",  f"{cm['FN']:,}"),
        ("Total false-positive cost",               f"₹{m['total_false_positive_cost_inr']:,.0f}"),
        ("Estimated missed recovery",               f"₹{m['total_false_negative_cost_inr']:,.0f}"),
        ("Net value recovered",                     f"₹{m['net_value_recovered_inr']:,.0f}"),
        ("ROI on fighting",                         f"+{m['roi_percent']:.1f}%"),
    ], columns=["Metric","Value"])
    st.dataframe(cost_df, use_container_width=True, hide_index=True)

    label("Performance by reason code")
    rc_rows = [{
        "Code":  code,
        "Type":  {"CB001":"Unauthorized","CB002":"Non-Receipt",
                  "CB003":"Not as Described","CB004":"Friendly Fraud"}.get(code,""),
        "Count": r["count"],
        "Win Rate": f"{r['win_rate']:.1%}",
        "Precision": round(r["precision"], 3),
        "Recall":    round(r["recall"], 3),
        "F1":        round(r["f1"], 3),
    } for code, r in m["per_reason_code"].items()]
    st.dataframe(pd.DataFrame(rc_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
# TAB 3 — BATCH SCORING
# ══════════════════════════════════════════════════════════════
with t3:
    label("Bulk chargeback scoring")
    st.markdown(
        f'<div class="fl-note" style="margin-bottom:16px">'
        "Upload a CSV matching the Analyze form columns. "
        "Every row runs through the full production pipeline — "
        "win probability, evidence audit and recommendation."
        "</div>", unsafe_allow_html=True)
    uploaded      = st.file_uploader("", type=["csv"],
                                      label_visibility="collapsed")
    TEMPLATE_COLS = list(payload.keys())

    if uploaded:
        df_up = pd.read_csv(uploaded)
        st.markdown(
            f'<div class="fl-note" style="margin-bottom:6px">'
            f'Preview — first 5 of {len(df_up):,} rows</div>',
            unsafe_allow_html=True)
        st.dataframe(df_up.head(5), use_container_width=True)

        missing_cols = [c for c in TEMPLATE_COLS if c not in df_up.columns]
        if missing_cols:
            st.error("Missing required columns: " + ", ".join(missing_cols))

        if st.button("🚀  Score All Rows", type="primary",
                     disabled=bool(missing_cols)):
            results, errors = [], 0
            prog = st.progress(0.0, text="Scoring …")
            for i, row in enumerate(df_up.to_dict(orient="records")):
                row = {**{c: None for c in TEMPLATE_COLS}, **row}
                try:
                    n = dict(row)
                    n["transaction_date"] = pd.to_datetime(n["transaction_date"]).date()
                    n["deadline_date"]    = pd.to_datetime(n["deadline_date"]).date()
                    for bc in ["is_3ds_verified","avs_match","cvv_match",
                               "has_delivery_confirmation","has_signed_receipt",
                               "has_login_after_purchase","has_support_interaction",
                               "order_confirmation_sent","refund_policy_acknowledged"]:
                        n[bc] = bool(n[bc])
                    for ic in ["customer_account_age_days","previous_orders_count",
                               "previous_chargebacks_count"]:
                        n[ic] = int(float(n[ic] or 0))
                    n["amount_inr"] = float(n["amount_inr"])
                    o = analyze_one({c: n[c] for c in TEMPLATE_COLS})
                    r = o["result"]
                    results.append({
                        "chargeback_id":         r["chargeback_id"],
                        "win_probability":        r["win_probability"],
                        "recommendation":         r["recommendation"],
                        "evidence_strength":      r["evidence_strength"],
                        "estimated_recovery_inr": r["estimated_recovery_inr"],
                    })
                except Exception:
                    errors += 1
                prog.progress((i+1)/len(df_up),
                              text=f"Scored {i+1:,}/{len(df_up):,}")

            if results:
                df_res   = pd.DataFrame(results)
                n_fight  = int((df_res.recommendation=="FIGHT").sum())
                n_review = int((df_res.recommendation=="REVIEW").sum())
                n_skip   = int((df_res.recommendation=="SKIP").sum())
                total_r  = float(df_res.estimated_recovery_inr.sum())

                st.markdown(
                    '<div class="fl-grid4" style="margin:16px 0">' +
                    kpi("⚔️","To FIGHT",  str(n_fight),
                        "strong — submit rebuttal", FL_GREEN) +
                    kpi("👁","To REVIEW", str(n_review),
                        "borderline — human decides", FL_AMBER) +
                    kpi("✕","To SKIP",   str(n_skip),
                        "accept the loss", FL_RED) +
                    kpi("💸","Est. Recovery", f"₹{total_r:,.0f}",
                        "across FIGHT cases", FL_CYAN) +
                    "</div>", unsafe_allow_html=True)
                if errors:
                    st.warning(f"{errors} row(s) failed — check dates/booleans.")
                st.dataframe(df_res, use_container_width=True)
                st.download_button(
                    "📥  Download Results (CSV)",
                    df_res.to_csv(index=False).encode("utf-8"),
                    file_name="batch_results.csv", mime="text/csv")
    else:
        st.markdown(
            f"""
            <div class="fl-card" style="border-style:dashed;text-align:center;
                 padding:52px 24px;">
              <div style="font-size:2.5rem;margin-bottom:12px;
                   filter:drop-shadow(0 0 14px {FL_VIOLET})">📂</div>
              <div style="font-size:1rem;font-weight:800;color:{FL_TEXT};
                   margin-bottom:6px">Drop a CSV here</div>
              <div style="color:{FL_MUTED};font-size:.84rem">
                Score hundreds of chargebacks at once through the full pipeline
              </div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ══════════════════════════════════════════════════════════════
with t4:
    from utils.db import db_manager
    rows = db_manager.get_all_predictions()

    if not rows:
        st.markdown(
            f"""
            <div class="fl-card" style="border-style:dashed;text-align:center;
                 padding:52px 24px;">
              <div style="font-size:2.5rem;margin-bottom:12px">🕒</div>
              <div style="font-size:1rem;font-weight:800;color:{FL_TEXT};
                   margin-bottom:6px">No history yet</div>
              <div style="color:{FL_MUTED};font-size:.84rem">
                Every analysis is logged automatically — run your first case.
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        df_hist = pd.DataFrame(rows)
        df_hist["predicted_at"] = pd.to_datetime(df_hist["predicted_at"])

        label("Filters")
        f1, f2, f3 = st.columns([1,1,1.4])
        rf = f1.selectbox("Recommendation", ["ALL","FIGHT","REVIEW","SKIP"])
        rz = f2.selectbox("Reason code",    ["ALL","CB001","CB002","CB003","CB004"])
        dmin = df_hist.predicted_at.min().date()
        dmax = df_hist.predicted_at.max().date()
        dr   = f3.date_input("Date range", (dmin, max(dmin, dmax)))

        mask = pd.Series(True, index=df_hist.index)
        if rf != "ALL": mask &= df_hist.recommendation == rf
        if rz != "ALL": mask &= df_hist.reason_code == rz
        if len(dr) == 2:
            mask &= df_hist.predicted_at.dt.date.between(dr[0], dr[1])
        view = df_hist[mask]

        fought = view[(view.recommendation=="FIGHT") & view.actual_outcome.notna()]
        wr     = fought.actual_outcome.mean() if len(fought) else 0.0
        tot    = pd.to_numeric(
            view.get("amount_inr"), errors="coerce").fillna(0).sum()

        st.markdown(
            '<div class="fl-grid4" style="margin:10px 0 20px">' +
            kpi("🗂️","Cases",        f"{len(view):,}") +
            kpi("🏆","Win rate",      f"{wr:.0%}", "of fought cases") +
            kpi("🎯","Avg P(win)",
                f"{view.win_probability.mean():.0%}" if len(view) else "—") +
            kpi("💰","Disputed value", f"₹{tot:,.0f}") +
            "</div>", unsafe_allow_html=True)

        label("Prediction log")
        view_table = view.sort_values("predicted_at", ascending=False)[[
            "predicted_at","chargeback_id","amount_inr","reason_code",
            "win_probability","recommendation","evidence_strength",
        ]].rename(columns={
            "predicted_at":"Date","chargeback_id":"Case ID",
            "amount_inr":"Amount (₹)","reason_code":"Reason",
            "win_probability":"P(win)","recommendation":"Decision",
            "evidence_strength":"Evidence",
        })
        st.dataframe(view_table, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        f"""
        <div style="padding:10px 0 14px">
          <div class="fl-logo" style="width:38px;height:38px;font-size:16px;
               border-radius:10px;margin-bottom:12px">R</div>
          <div style="font-weight:900;color:{FL_TEXT};font-size:1rem;
               letter-spacing:-.025em">Nexsus.Guard</div>
          <div style="font-size:.75rem;color:{FL_MUTED};font-weight:600">
            AI Risk Manager · v1.0
          </div>
        </div>
        <div class="fl-divider"></div>

        <div class="fl-label">Model card</div>
        <table style="font-size:.78rem;line-height:2.1;width:100%;
                      color:{FL_TEXT}">
          <tr><td style="color:{FL_MUTED}">Algorithm</td>
              <td style="text-align:right"><b>XGBoost</b></td></tr>
          <tr><td style="color:{FL_MUTED}">Features</td>
              <td style="text-align:right"><b>27 engineered</b></td></tr>
          <tr><td style="color:{FL_MUTED}">Training data</td>
              <td style="text-align:right"><b>50,000 cases</b></td></tr>
          <tr><td style="color:{FL_MUTED}">Threshold</td>
              <td style="text-align:right">
                <b>{state.trainer.recommended_threshold_:.2f}</b></td></tr>
          <tr><td style="color:{FL_MUTED}">Explainability</td>
              <td style="text-align:right"><b>SHAP</b></td></tr>
        </table>

        <div class="fl-divider"></div>
        <div class="fl-label">Decision bands</div>
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:16px">
          <span class="fl-badge b-green">
            ⚔️&nbsp; FIGHT &nbsp;≥ {thr['fight_above']}
          </span>
          <span class="fl-badge b-yellow">
            👁&nbsp; REVIEW &nbsp;{thr['review_between'][0]}–{thr['review_between'][1]}
          </span>
          <span class="fl-badge b-red">
            ✕&nbsp; SKIP &nbsp;≤ {thr['skip_below']}
          </span>
        </div>
        <div class="fl-divider"></div>
        """,
        unsafe_allow_html=True,
    )

    try:
        from utils.db import db_manager as _db
        preds = _db.get_all_predictions()
        st.markdown(kpi("📊","Lifetime analyses", f"{len(preds):,}",
                        "logged in SQLite"), unsafe_allow_html=True)
        if preds:
            avg_p = sum(p["win_probability"] for p in preds) / len(preds)
            st.markdown(kpi("🎯","Avg P(win)", f"{avg_p:.0%}"),
                        unsafe_allow_html=True)
    except Exception:
        pass

    st.markdown(
        f"""
        <div class="fl-footer">
          Built for <a href="https://razorpay.com">Razorpay</a><br/>
          Internship Hackathon 2026<br/>
          <span style="color:{FL_SUBTLE}">
            Defence-only · no customer targeting
          </span><br/><br/>
          <span class="fl-badge b-violet" style="font-size:.65rem">
            🛡️ &nbsp;Strictly Defence-Only
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
