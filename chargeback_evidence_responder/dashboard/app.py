"""Nexsus.Guard — AI Risk Manager Dashboard.

Design System: Apple Human Interface Guidelines (DESIGN.md)
  Canvas:        #08080A (Pure Deep Dark Canvas)
  Material:      rgba(28, 28, 30, 0.75) with backdrop-filter blur(30px)
  Surface-2:     rgba(44, 44, 46, 0.85) (Elevated card & input)
  Border:        rgba(255, 255, 255, 0.10) (Hairline divider)
  System Blue:   #0A84FF (Apple System Blue Primary)
  System Green:  #30D158 (Apple System Green)
  System Orange: #FF9F0A (Apple System Orange)
  System Red:    #FF453A (Apple System Red)
  System Purple: #BF5AF2 (Apple System Purple)
  Text Primary:  #F5F5F7 (San Francisco Pro)
  Text Muted:    #8E8E93 (Secondary System Gray)
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

# ── Apple Design Tokens ──────────────────────────────────────────────────────
AP_BG          = "#08080A"
AP_SURFACE     = "rgba(28, 28, 30, 0.75)"
AP_SURFACE_HI  = "rgba(44, 44, 46, 0.85)"
AP_SURFACE_HOV = "rgba(58, 58, 60, 0.90)"
AP_BORDER      = "rgba(255, 255, 255, 0.10)"
AP_BORDER_HI   = "rgba(255, 255, 255, 0.18)"

AP_BLUE        = "#0A84FF"
AP_BLUE_GRAD   = "linear-gradient(180deg, #0A84FF 0%, #0071E3 100%)"
AP_GREEN       = "#30D158"
AP_ORANGE      = "#FF9F0A"
AP_RED         = "#FF453A"
AP_PURPLE      = "#BF5AF2"
AP_TEXT        = "#F5F5F7"
AP_MUTED       = "#8E8E93"
AP_SUBTLE      = "#636366"

TONE_HEX       = {"green": AP_GREEN, "yellow": AP_ORANGE, "red": AP_RED}
STRENGTH_TON   = {"STRONG": AP_GREEN, "MODERATE": AP_ORANGE, "WEAK": AP_RED}

# ── Apple CSS ────────────────────────────────────────────────────────────────
CSS = f"""
<style>
/* ── Typography: Apple SF Pro System Fonts ── */
html, body, [class*="css"] {{
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
  letter-spacing: -0.015em;
}}

.stApp {{
  background: {AP_BG};
  color: {AP_TEXT};
}}

.block-container {{
  padding: 0 2rem 4rem !important;
  max-width: 1400px;
}}

#MainMenu, footer, header[data-testid="stHeader"] {{
  visibility: hidden;
}}

/* ── Sidebar (macOS Glass) ── */
[data-testid="stSidebar"] {{
  background: rgba(20, 20, 22, 0.85) !important;
  backdrop-filter: blur(40px) saturate(180%) !important;
  border-right: 1px solid {AP_BORDER} !important;
}}

/* ── Top Bar (iOS / macOS Translucent Material) ── */
.ap-topbar {{
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 28px;
  background: rgba(18, 18, 20, 0.78);
  backdrop-filter: blur(30px) saturate(190%);
  -webkit-backdrop-filter: blur(30px) saturate(190%);
  border-bottom: 1px solid {AP_BORDER};
  margin: 0 -2rem 24px;
}}

.ap-brand {{
  display: flex;
  align-items: center;
  gap: 14px;
}}

.ap-logo-icon {{
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: {AP_BLUE_GRAD};
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 19px;
  color: #FFFFFF;
  box-shadow: 0 4px 16px rgba(10, 132, 255, 0.35);
}}

.ap-title {{
  font-size: 1.15rem;
  font-weight: 700;
  color: {AP_TEXT};
  letter-spacing: -0.025em;
  line-height: 1.15;
}}

.ap-subtitle {{
  font-size: 0.74rem;
  color: {AP_MUTED};
  font-weight: 500;
  margin-top: 2px;
}}

.ap-chips {{
  display: flex;
  align-items: center;
  gap: 10px;
}}

.ap-chip {{
  font-size: 0.74rem;
  font-weight: 600;
  padding: 5px 14px;
  border-radius: 980px;
  letter-spacing: -0.01em;
}}

.ap-chip-blue {{
  background: rgba(10, 132, 255, 0.15);
  color: {AP_BLUE};
  border: 1px solid rgba(10, 132, 255, 0.30);
}}

.ap-chip-green {{
  background: rgba(48, 209, 88, 0.15);
  color: {AP_GREEN};
  border: 1px solid rgba(48, 209, 88, 0.30);
}}

/* ── Frosted Glass Cards ── */
.ap-card {{
  background: {AP_SURFACE};
  backdrop-filter: blur(30px) saturate(180%);
  -webkit-backdrop-filter: blur(30px) saturate(180%);
  border: 1px solid {AP_BORDER};
  border-radius: 18px;
  padding: 22px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.36);
  margin-bottom: 16px;
  transition: all 0.2s ease;
}}

.ap-card:hover {{
  border-color: {AP_BORDER_HI};
}}

.ap-card-glow {{
  border-color: rgba(10, 132, 255, 0.35);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.40), 0 0 30px rgba(10, 132, 255, 0.08);
}}

/* ── Eyebrow Labels ── */
.ap-eyebrow {{
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {AP_MUTED};
  margin-bottom: 12px;
}}

/* ── Apple Health / Watch KPI Cards ── */
.ap-kpi {{
  background: {AP_SURFACE_HI};
  border: 1px solid {AP_BORDER};
  border-radius: 14px;
  padding: 16px 18px;
  position: relative;
}}

.ap-kpi-label {{
  font-size: 0.68rem;
  font-weight: 600;
  color: {AP_MUTED};
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}}

.ap-kpi-value {{
  font-size: 1.6rem;
  font-weight: 800;
  color: {AP_TEXT};
  letter-spacing: -0.03em;
  line-height: 1.1;
}}

.ap-kpi-hint {{
  font-size: 0.72rem;
  color: {AP_SUBTLE};
  margin-top: 4px;
}}

/* ── Win Probability Hero Display ── */
.ap-prob-label {{
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {AP_MUTED};
  margin-bottom: 6px;
}}

.ap-prob-number {{
  font-size: 4.2rem;
  font-weight: 900;
  letter-spacing: -0.05em;
  line-height: 1;
}}

.ap-prob-sub {{
  font-size: 0.82rem;
  color: {AP_MUTED};
  margin-top: 6px;
}}

/* ── Badges & Pills (Apple Capsule Style) ── */
.ap-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.76rem;
  font-weight: 700;
  padding: 6px 16px;
  border-radius: 980px;
  letter-spacing: -0.01em;
  text-transform: uppercase;
}}

.b-green  {{ background: rgba(48, 209, 88, 0.15); color: {AP_GREEN}; border: 1px solid rgba(48, 209, 88, 0.35); }}
.b-yellow {{ background: rgba(255, 159, 10, 0.15); color: {AP_ORANGE}; border: 1px solid rgba(255, 159, 10, 0.35); }}
.b-red    {{ background: rgba(255, 69, 58, 0.15); color: {AP_RED}; border: 1px solid rgba(255, 69, 58, 0.35); }}
.b-blue   {{ background: rgba(10, 132, 255, 0.15); color: {AP_BLUE}; border: 1px solid rgba(10, 132, 255, 0.35); }}
.b-gray   {{ background: rgba(142, 142, 147, 0.15); color: {AP_MUTED}; border: 1px solid rgba(142, 142, 147, 0.30); }}

/* ── Evidence Checklist Rows ── */
.ap-check {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 0.85rem;
  color: {AP_TEXT};
  background: {AP_SURFACE_HI};
  border: 1px solid {AP_BORDER};
  margin-bottom: 8px;
}}

.ap-check .ic {{
  width: 20px;
  height: 20px;
  border-radius: 50%;
  font-size: 0.65rem;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}}

.ap-check.ok .ic   {{ background: rgba(48, 209, 88, 0.20); color: {AP_GREEN}; }}
.ap-check.miss .ic {{ background: rgba(255, 69, 58, 0.20); color: {AP_RED}; }}
.ap-check .lbl     {{ font-weight: 600; color: {AP_TEXT}; }}
.ap-check .tag     {{ margin-left: auto; font-size: 0.65rem; font-weight: 700; color: {AP_SUBTLE}; text-transform: uppercase; letter-spacing: 0.05em; }}

/* ── Factor Rows ── */
.ap-factor {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 0.84rem;
  margin-bottom: 8px;
  border: 1px solid;
}}

.f-up   {{ background: rgba(48, 209, 88, 0.08); border-color: rgba(48, 209, 88, 0.25); color: #75F991; }}
.f-down {{ background: rgba(255, 69, 58, 0.08); border-color: rgba(255, 69, 58, 0.25); color: #FF8077; }}
.ap-factor b {{ font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.80rem; font-weight: 700; }}

/* ── Progress Bar ── */
.ap-progress {{
  height: 8px;
  background: rgba(142, 142, 147, 0.20);
  border-radius: 980px;
  overflow: hidden;
  margin: 12px 0 8px;
}}

.ap-progress-fill {{
  height: 100%;
  border-radius: 980px;
}}

/* ── Explanation Callout ── */
.ap-quote {{
  border-left: 3px solid {AP_BLUE};
  background: rgba(10, 132, 255, 0.08);
  padding: 14px 18px;
  border-radius: 0 12px 12px 0;
  font-size: 0.88rem;
  line-height: 1.6;
  color: {AP_TEXT};
}}

.ap-divider {{
  height: 1px;
  background: {AP_BORDER};
  margin: 18px 0;
}}

/* ── Apple Segmented Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
  gap: 4px;
  background: rgba(118, 118, 128, 0.20);
  backdrop-filter: blur(20px);
  padding: 4px;
  border-radius: 12px;
  border-bottom: none;
  margin-bottom: 22px;
}}

.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{
  display: none;
}}

.stTabs [data-baseweb="tab"] {{
  background: transparent;
  border: none;
  padding: 8px 20px;
  border-radius: 9px;
  font-size: 0.86rem;
  font-weight: 600;
  color: {AP_MUTED};
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}}

.stTabs [data-baseweb="tab"]:hover {{
  color: {AP_TEXT};
}}

.stTabs [aria-selected="true"] {{
  background: rgba(255, 255, 255, 0.16) !important;
  color: #FFFFFF !important;
  font-weight: 700;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.35);
}}

/* ── Form Inputs (Apple Dark Style) ── */
div[data-testid="stDateInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
  background: {AP_SURFACE_HI} !important;
  color: {AP_TEXT} !important;
  border: 1px solid {AP_BORDER} !important;
  border-radius: 10px;
  font-size: 0.88rem;
}}

div[data-testid="stDateInput"] input:focus,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {{
  border-color: {AP_BLUE} !important;
  box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.25);
}}

div[data-testid="stTextArea"] textarea {{
  background: {AP_SURFACE_HI} !important;
  color: {AP_TEXT} !important;
  border: 1px solid {AP_BORDER} !important;
  border-radius: 12px;
}}

div[data-baseweb="select"] > div {{
  background: {AP_SURFACE_HI} !important;
  border: 1px solid {AP_BORDER} !important;
  color: {AP_TEXT} !important;
  border-radius: 10px;
}}

label[data-testid="stWidgetLabel"] p {{
  color: {AP_MUTED} !important;
  font-size: 0.82rem;
  font-weight: 600;
}}

/* ── Apple Capsule Action Buttons ── */
.stButton > button {{
  border-radius: 980px;
  font-weight: 700;
  font-size: 0.92rem;
  padding: 0.65rem 1.4rem;
  border: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  letter-spacing: -0.01em;
}}

.stButton > button[kind="primary"] {{
  background: {AP_BLUE_GRAD};
  color: #FFFFFF;
  box-shadow: 0 4px 18px rgba(10, 132, 255, 0.40);
}}

.stButton > button[kind="primary"]:hover {{
  box-shadow: 0 6px 24px rgba(10, 132, 255, 0.60);
  transform: scale(1.01);
}}

.stButton > button[kind="primary"]:active {{
  transform: scale(0.98);
}}

.stDownloadButton > button {{
  border-radius: 980px;
  font-weight: 700;
  background: rgba(10, 132, 255, 0.12) !important;
  color: {AP_BLUE} !important;
  border: 1px solid rgba(10, 132, 255, 0.35) !important;
  transition: all 0.2s ease;
}}

.stDownloadButton > button:hover {{
  background: rgba(10, 132, 255, 0.22) !important;
  box-shadow: 0 4px 16px rgba(10, 132, 255, 0.25);
}}

/* ── Grids & Utilities ── */
.ap-grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.ap-grid4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
.ap-note  {{ font-size: 0.76rem; color: {AP_MUTED}; }}

.ap-footer {{
  text-align: center;
  color: {AP_SUBTLE};
  font-size: 0.72rem;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid {AP_BORDER};
  line-height: 1.8;
}}
.ap-footer a {{ color: {AP_BLUE}; text-decoration: none; font-weight: 600; }}
</style>
"""

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nexsus.Guard — AI Risk Manager",
    page_icon="🛡️",
    layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)

LABELS = {
    "is_3ds_verified":           "3-D Secure Authenticated",
    "avs_match":                 "Billing Address (AVS) Match",
    "cvv_match":                 "CVV Security Match",
    "has_delivery_confirmation": "Courier Delivery Proof",
    "has_signed_receipt":        "Signed Proof of Delivery",
    "has_login_after_purchase":  "Post-Purchase Account Activity",
    "has_support_interaction":   "Support Interaction Log",
    "order_confirmation_sent":   "Order Confirmation Delivered",
    "refund_policy_acknowledged":"Refund Terms Acknowledged",
}

# ── Component Helpers ────────────────────────────────────────────────────────
def eyebrow(text: str) -> None:
    st.markdown(f'<div class="ap-eyebrow">{text}</div>', unsafe_allow_html=True)

def kpi(title: str, value: str, hint: str = "", color: str = AP_TEXT) -> str:
    return (
        f'<div class="ap-kpi">'
        f'<div class="ap-kpi-label">{title}</div>'
        f'<div class="ap-kpi-value" style="color:{color}">{value}</div>'
        f'<div class="ap-kpi-hint">{hint}</div>'
        f'</div>'
    )

def check_row(lbl: str, found: bool, tag: str = "") -> str:
    cls   = "ok" if found else "miss"
    ic    = "✓"  if found else "✕"
    tag_h = f'<span class="tag">{tag}</span>' if tag else ""
    return (
        f'<div class="ap-check {cls}">'
        f'<span class="ic">{ic}</span>'
        f'<span class="lbl">{lbl}</span>{tag_h}</div>'
    )

def factor_row(name: str, pts: float, up: bool) -> str:
    arrow = f'<span style="color:{AP_GREEN}">▲</span>' if up else f'<span style="color:{AP_RED}">▼</span>'
    sign, cls = ("+", "f-up") if up else ("", "f-down")
    return (
        f'<div class="ap-factor {cls}">{arrow}'
        f'<b>{name}</b>'
        f'<span style="margin-left:auto;font-weight:800">{sign}{pts:.0f} pts</span></div>'
    )

def strength_badge(s: str) -> str:
    cls = {"STRONG": "b-green", "MODERATE": "b-yellow", "WEAK": "b-red"}.get(s, "b-gray")
    return f'<span class="ap-badge {cls}">{s}</span> <span class="ap-note">evidence package</span>'

def plotly_ap(fig: go.Figure, title: str = "") -> go.Figure:
    """Apple-style dark mode clean Plotly theme."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=13, color=AP_TEXT, family="-apple-system, BlinkMacSystemFont, SF Pro Display"),
            x=0
        ),
        template="plotly_dark",
        height=310,
        margin=dict(l=8, r=8, t=42, b=8),
        font=dict(family="-apple-system, BlinkMacSystemFont, SF Pro Text", size=11, color=AP_MUTED),
        paper_bgcolor="rgba(28, 28, 30, 0.75)",
        plot_bgcolor="rgba(28, 28, 30, 0.75)",
        legend=dict(
            bgcolor="rgba(44, 44, 46, 0.85)",
            bordercolor=AP_BORDER,
            borderwidth=1,
            font=dict(size=10, color=AP_MUTED)
        ),
    )
    fig.update_xaxes(gridcolor=AP_BORDER, linecolor=AP_BORDER, zerolinecolor=AP_BORDER)
    fig.update_yaxes(gridcolor=AP_BORDER, linecolor=AP_BORDER, zerolinecolor=AP_BORDER)
    return fig

# ── Model Loading ────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading model artifacts …")
def get_pipeline():
    import yaml
    from api.routes import load_artifacts, state
    with open(PACKAGE_DIR / "config.yaml", "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    load_artifacts()
    return state, config

@st.cache_data(show_spinner="Evaluating test set …")
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

# ══════════════════════════════════════════════════════════════
# TOP BAR (Apple Frosted Translucency)
# ══════════════════════════════════════════════════════════════
st.markdown(
    f"""
    <div class="ap-topbar">
      <div class="ap-brand">
        <div class="ap-logo-icon"></div>
        <div>
          <div class="ap-title">Nexsus.Guard</div>
          <div class="ap-subtitle">AI Risk Manager · Chargeback Evidence Responder</div>
        </div>
      </div>
      <div class="ap-chips">
        <span class="ap-chip ap-chip-blue">XGBoost · SHAP</span>
        <span class="ap-chip ap-chip-blue">Threshold&nbsp;<b>{state.trainer.recommended_threshold_:.2f}</b></span>
        <span class="ap-chip ap-chip-green">● Online</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════
# SEGMENTED TABS (Apple Style)
# ══════════════════════════════════════════════════════════════
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
        eyebrow("Transaction Details")
        c1, c2 = st.columns(2)
        cb_id        = c1.text_input("Chargeback ID", "CHB-2026-000001")
        txn_id       = c2.text_input("Transaction ID", "TXN-2026-000001")
        txn_date     = st.date_input("Transaction Date", value=date.today() - timedelta(days=21))
        amount       = st.number_input("Amount (₹)", min_value=1.0, value=12500.0, step=100.0)
        
        c3, c4 = st.columns(2)
        pay_method = c3.selectbox("Payment Method",
            ["card_credit", "card_debit", "upi", "netbanking", "wallet"],
            format_func=lambda x: {
                "card_credit": "💳 Credit Card",
                "card_debit":  "💳 Debit Card",
                "upi":         "📱 UPI",
                "netbanking":  "🏦 Net Banking",
                "wallet":      "👛 Digital Wallet"
            }[x]
        )
        merchant_cat = c4.selectbox("Merchant Category",
            ["electronics", "fashion", "travel", "food", "grocery",
             "education", "healthcare", "gaming", "subscription", "other"]
        )
        reason_code = st.selectbox("Reason Code",
            ["CB001", "CB002", "CB003", "CB004"],
            format_func=lambda c: {
                "CB001": "CB001 — Unauthorized Transaction",
                "CB002": "CB002 — Item Not Received",
                "CB003": "CB003 — Not as Described",
                "CB004": "CB004 — Friendly Fraud"
            }[c]
        )
        c5, c6 = st.columns(2)
        merchant_name = c5.text_input("Merchant Name", "TechNova Retail Pvt Ltd")
        customer_name = c6.text_input("Customer Name", "Ravi Kumar")
        deadline_date = st.date_input("Response Deadline", value=date.today() + timedelta(days=2))

        st.markdown('<div class="ap-divider"></div>', unsafe_allow_html=True)
        eyebrow("Customer Profile")
        acct_age    = st.slider("Account Age (days)", 0, 2000, 890)
        prev_orders = st.slider("Previous Successful Orders", 0, 200, 34)
        prev_cbs    = st.slider("Previous Chargebacks", 0, 10, 0)

        st.markdown('<div class="ap-divider"></div>', unsafe_allow_html=True)
        eyebrow("Security & Verification")
        v1, v2, v3 = st.columns(3)
        three_ds = v1.checkbox("3DS Verified", True)
        avs      = v2.checkbox("AVS Match",    True)
        cvv      = v3.checkbox("CVV Match",    True)

        st.markdown('<div class="ap-divider"></div>', unsafe_allow_html=True)
        eyebrow("Evidence on File")
        e1, e2 = st.columns(2)
        delivery     = e1.checkbox("Delivery Confirmation", True)
        signed       = e1.checkbox("Signed Receipt",        False)
        login_after  = e1.checkbox("Post-Purchase Login",   True)
        support      = e2.checkbox("Support Interaction",   False)
        confirm_sent = e2.checkbox("Confirmation Sent",     True)
        policy_ack   = e2.checkbox("Policy Acknowledged",   True)

        st.markdown('<div class="ap-divider"></div>', unsafe_allow_html=True)
        submit = st.button("Evaluate Dispute Risk", type="primary", use_container_width=True)

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
            with st.spinner("Analyzing signals · Auditing evidence · Generating case …"):
                out = analyze_one(payload)
            res  = out["result"]
            pct  = res["win_probability"] * 100
            hexc = TONE_HEX[res["recommendation_color"]]
            bcls = {"FIGHT": "b-green", "REVIEW": "b-yellow", "SKIP": "b-red"}[res["recommendation"]]

            with right:
                # ── Win Probability Hero Card ──────────────────────────────
                st.markdown(
                    f"""
                    <div class="ap-card ap-card-glow">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px">
                        <div>
                          <div class="ap-prob-label">Estimated Win Probability</div>
                          <div class="ap-prob-number" style="color:{hexc}">{pct:.0f}%</div>
                          <div class="ap-prob-sub">{res['confidence_label']} Confidence &nbsp;·&nbsp; {res['chargeback_id']}</div>
                        </div>
                        <span class="ap-badge {bcls}" style="font-size:0.85rem;padding:8px 22px">
                          {res['recommendation']}
                        </span>
                      </div>
                      <div class="ap-grid2">
                        {kpi('Estimated Recovery', f"₹{res['estimated_recovery_inr']:,.0f}", '80% of disputed value', AP_GREEN)}
                        {kpi('Cost Risk If Lost', f"₹{res['false_positive_cost_inr']:,.0f}", 'Fees + representation effort', AP_ORANGE)}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if res["deadline_warning"]:
                    st.warning(f"⏰ {res['deadline_warning']} — Submit early to guarantee bank processing.")

                # ── Evidence Audit ─────────────────────────────────────────
                st.markdown('<div class="ap-card">', unsafe_allow_html=True)
                eyebrow("Evidence Completeness Audit")
                tier = {
                    "is_3ds_verified": "Tier 1", "avs_match": "Tier 1",
                    "cvv_match": "Tier 1", "has_delivery_confirmation": "Tier 1",
                    "has_signed_receipt": "Supporting",
                    "has_login_after_purchase": "Supporting",
                    "has_support_interaction": "Supporting",
                    "order_confirmation_sent": "Standard",
                    "refund_policy_acknowledged": "Standard",
                }
                ca, cb_col = st.columns(2)
                with ca:
                    st.markdown(
                        "".join(check_row(LABELS[k], payload[k], tier.get(k, ""))
                                for k in ["is_3ds_verified", "avs_match", "cvv_match",
                                          "has_delivery_confirmation", "has_signed_receipt"]),
                        unsafe_allow_html=True
                    )
                with cb_col:
                    st.markdown(
                        "".join(check_row(LABELS[k], payload[k], tier.get(k, ""))
                                for k in ["has_login_after_purchase",
                                          "has_support_interaction",
                                          "order_confirmation_sent",
                                          "refund_policy_acknowledged"]),
                        unsafe_allow_html=True
                    )

                fill = min(res["evidence_completeness_pct"], 100)
                bar_c = AP_GREEN if fill > 70 else (AP_ORANGE if fill >= 40 else AP_RED)
                st.markdown(
                    f'<div class="ap-progress">'
                    f'<div class="ap-progress-fill" style="width:{fill}%;background:{bar_c}"></div></div>'
                    f'{strength_badge(res["evidence_strength"])}',
                    unsafe_allow_html=True,
                )
                if res["missing_critical_evidence"]:
                    missing = ", ".join(LABELS.get(m, m) for m in res["missing_critical_evidence"])
                    st.error(f"Tier-1 Evidence Missing: **{missing}** — highly recommended for submission.")
                st.markdown("</div>", unsafe_allow_html=True)

                # ── SHAP Explainability ────────────────────────────────────
                st.markdown(
                    f'<div class="ap-card">'
                    f'<div class="ap-eyebrow">Decision Intelligence & Rationale</div>'
                    f'<div class="ap-quote">{res["explanation_text"]}</div>',
                    unsafe_allow_html=True
                )
                f1c, f2c = st.columns(2)
                f1c.markdown('<div class="ap-eyebrow" style="margin-top:12px">Positive Drivers</div>', unsafe_allow_html=True)
                f1c.markdown(
                    "".join(factor_row(f["feature"], abs(f.get("pct_points", 0)), True)
                            for f in res["top_positive_factors"][:3])
                    or '<div class="ap-note">No significant positive drivers.</div>',
                    unsafe_allow_html=True
                )
                f2c.markdown('<div class="ap-eyebrow" style="margin-top:12px">Risk Drivers</div>', unsafe_allow_html=True)
                f2c.markdown(
                    "".join(factor_row(f["feature"], abs(f.get("pct_points", 0)), False)
                            for f in res["top_negative_factors"][:3])
                    or '<div class="ap-note">No material risk factors detected.</div>',
                    unsafe_allow_html=True
                )
                st.markdown("</div>", unsafe_allow_html=True)

                # ── Rebuttal Letter ────────────────────────────────────────
                st.markdown(
                    '<div class="ap-card">'
                    '<div class="ap-eyebrow">Auto-Generated Bank Rebuttal Letter</div>',
                    unsafe_allow_html=True
                )
                st.text_area("", res["letter_preview"], height=160, disabled=True, label_visibility="collapsed")
                st.download_button(
                    "Download Rebuttal Package (.docx)",
                    data=out["docx"],
                    file_name=f"rebuttal_{res['chargeback_id']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
    else:
        with right:
            st.markdown(
                f"""
                <div class="ap-card" style="border-style:dashed;text-align:center;padding:64px 24px;">
                  <div style="font-size:3rem;margin-bottom:14px;">⚖️</div>
                  <div style="font-size:1.15rem;font-weight:700;color:{AP_TEXT};margin-bottom:8px;">Ready for Evaluation</div>
                  <div style="color:{AP_MUTED};font-size:0.88rem;line-height:1.6;max-width:320px;margin:0 auto">
                    Enter the transaction details on the left to compute instant ML win probability and generate evidence packages.
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

    k1, k2, k3, k4, k5 = st.columns(5, gap="small")
    with k1:
        st.markdown(kpi("Precision", f"{m['precision']:.3f}", "of FIGHT decisions won"), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi("Recall", f"{m['recall']:.3f}", "of winnable cases caught"), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi("F1 Score", f"{m['f1_score']:.3f}", "harmonic mean"), unsafe_allow_html=True)
    with k4:
        st.markdown(kpi("ROC-AUC", f"{m['roc_auc_score']:.3f}", "discrimination power"), unsafe_allow_html=True)
    with k5:
        st.markdown(kpi("ROI", f"+{m['roi_percent']:,.0f}%", "net recovery vs cost", AP_GREEN), unsafe_allow_html=True)

    st.markdown(
        f'<div class="ap-note" style="margin:10px 0 20px">'
        f'Held-Out Test Set: <b>{m["n_samples"]:,}</b> cases &nbsp;·&nbsp; '
        f'Decision Threshold: <b>{m["threshold"]:.2f}</b> &nbsp;·&nbsp; '
        f'Base Win Rate: <b>{m["base_win_rate"]:.0%}</b></div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="ap-divider"></div>', unsafe_allow_html=True)

    g1, g2 = st.columns(2)
    fig_roc = go.Figure()
    fig_roc.add_trace(go.Scatter(
        x=ev["fpr"], y=ev["tpr"], mode="lines",
        name=f"AUC {m['roc_auc_score']:.4f}",
        line=dict(color=AP_BLUE, width=3),
        fill="tozeroy", fillcolor="rgba(10, 132, 255, 0.12)"
    ))
    fig_roc.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines", name="Random Baseline",
        line=dict(dash="dot", color=AP_SUBTLE, width=1.5)
    ))
    g1.plotly_chart(plotly_ap(fig_roc, "ROC Curve"), use_container_width=True)

    fig_pr = go.Figure()
    fig_pr.add_trace(go.Scatter(
        x=ev["recall_curve"], y=ev["precision_curve"], mode="lines",
        name=f"AP {m['average_precision_score']:.4f}",
        line=dict(color=AP_GREEN, width=3),
        fill="tozeroy", fillcolor="rgba(48, 209, 88, 0.12)"
    ))
    g2.plotly_chart(plotly_ap(fig_pr, "Precision–Recall Curve"), use_container_width=True)

    g3, g4 = st.columns(2)
    fig_cost = go.Figure()
    fig_cost.add_trace(go.Scatter(
        x=ev["thresholds"],
        y=np.array(ev["total_costs"]) / 1e6,
        mode="lines", name="Total Cost (₹M)",
        line=dict(color=AP_RED, width=3),
        fill="tozeroy", fillcolor="rgba(255, 69, 58, 0.08)"
    ))
    fig_cost.add_vline(
        x=ev["best_threshold"], line_dash="dot", line_color=AP_BLUE,
        annotation_text=f"Optimal: ₹{min(ev['total_costs'])/1e6:.2f}M @ {ev['best_threshold']:.2f}",
        annotation_font_color=AP_BLUE
    )
    g3.plotly_chart(plotly_ap(fig_cost, "Business Cost vs Threshold (₹M)"), use_container_width=True)

    imp = list(ev["importance"].items())[:12][::-1]
    fig_imp = go.Figure(go.Bar(
        x=[v for _, v in imp], y=[k for k, _ in imp],
        orientation="h",
        marker=dict(color=AP_BLUE, opacity=0.9)
    ))
    g4.plotly_chart(plotly_ap(fig_imp, "Feature Importance (Mean |SHAP|)"), use_container_width=True)

    st.markdown('<div class="ap-divider"></div>', unsafe_allow_html=True)
    eyebrow("Cost & Recovery Analysis (Test Set)")
    cost_df = pd.DataFrame([
        ("True Wins Fought (TP)",                   f"{cm['TP']:,}"),
        ("False Positives — Fought but Lost",       f"{cm['FP']:,}"),
        ("False Negatives — Skipped but Winnable",  f"{cm['FN']:,}"),
        ("Total False-Positive Cost",               f"₹{m['total_false_positive_cost_inr']:,.0f}"),
        ("Estimated Missed Recovery",               f"₹{m['total_false_negative_cost_inr']:,.0f}"),
        ("Net Value Recovered",                     f"₹{m['net_value_recovered_inr']:,.0f}"),
        ("ROI on Dispute Representation",           f"+{m['roi_percent']:.1f}%"),
    ], columns=["Metric", "Value"])
    st.dataframe(cost_df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
# TAB 3 — BATCH SCORING
# ══════════════════════════════════════════════════════════════
with t3:
    eyebrow("Bulk Chargeback Assessment")
    st.markdown(
        f'<div class="ap-note" style="margin-bottom:16px">'
        "Upload a batch CSV file to execute the complete detection, verification, and scoring pipeline across hundreds of disputes simultaneously."
        "</div>",
        unsafe_allow_html=True
    )
    uploaded = st.file_uploader("", type=["csv"], label_visibility="collapsed")
    TEMPLATE_COLS = list(payload.keys())

    if uploaded:
        df_up = pd.read_csv(uploaded)
        st.markdown(f'<div class="ap-note" style="margin-bottom:6px">Preview (first 5 of {len(df_up):,} rows)</div>', unsafe_allow_html=True)
        st.dataframe(df_up.head(5), use_container_width=True)

        missing_cols = [c for c in TEMPLATE_COLS if c not in df_up.columns]
        if missing_cols:
            st.error("Missing required columns: " + ", ".join(missing_cols))

        if st.button("Execute Batch Analysis", type="primary", disabled=bool(missing_cols)):
            results, errors = [], 0
            prog = st.progress(0.0, text="Evaluating cases …")
            for i, row in enumerate(df_up.to_dict(orient="records")):
                row = {**{c: None for c in TEMPLATE_COLS}, **row}
                try:
                    n = dict(row)
                    n["transaction_date"] = pd.to_datetime(n["transaction_date"]).date()
                    n["deadline_date"]    = pd.to_datetime(n["deadline_date"]).date()
                    for bc in ["is_3ds_verified", "avs_match", "cvv_match",
                               "has_delivery_confirmation", "has_signed_receipt",
                               "has_login_after_purchase", "has_support_interaction",
                               "order_confirmation_sent", "refund_policy_acknowledged"]:
                        n[bc] = bool(n[bc])
                    for ic in ["customer_account_age_days", "previous_orders_count",
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
                prog.progress((i + 1) / len(df_up), text=f"Scored {i+1:,} of {len(df_up):,}")

            if results:
                df_res   = pd.DataFrame(results)
                n_fight  = int((df_res.recommendation == "FIGHT").sum())
                n_review = int((df_res.recommendation == "REVIEW").sum())
                n_skip   = int((df_res.recommendation == "SKIP").sum())
                total_r  = float(df_res.estimated_recovery_inr.sum())

                st.markdown(
                    '<div class="ap-grid4" style="margin:16px 0">' +
                    kpi("To FIGHT",  str(n_fight),  "High win probability", AP_GREEN) +
                    kpi("To REVIEW", str(n_review), "Borderline confidence", AP_ORANGE) +
                    kpi("To SKIP",   str(n_skip),   "Low probability", AP_RED) +
                    kpi("Est. Total Recovery", f"₹{total_r:,.0f}", "Across all FIGHT cases", AP_BLUE) +
                    "</div>",
                    unsafe_allow_html=True
                )
                st.dataframe(df_res, use_container_width=True)
                st.download_button(
                    "Download Evaluated Batch (CSV)",
                    df_res.to_csv(index=False).encode("utf-8"),
                    file_name="batch_evaluation_results.csv",
                    mime="text/csv"
                )

# ══════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ══════════════════════════════════════════════════════════════
with t4:
    from utils.db import db_manager
    rows = db_manager.get_all_predictions()

    if not rows:
        st.markdown(
            f"""
            <div class="ap-card" style="border-style:dashed;text-align:center;padding:52px 24px;">
              <div style="font-size:2.5rem;margin-bottom:12px">🕒</div>
              <div style="font-size:1.1rem;font-weight:700;color:{AP_TEXT};margin-bottom:6px">No Disputed Records Yet</div>
              <div style="color:{AP_MUTED};font-size:0.85rem">Every analyzed case is persistently logged in SQLite.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        df_hist = pd.DataFrame(rows)
        df_hist["predicted_at"] = pd.to_datetime(df_hist["predicted_at"])

        eyebrow("Filter History")
        f1, f2, f3 = st.columns([1, 1, 1.4])
        rf = f1.selectbox("Recommendation", ["ALL", "FIGHT", "REVIEW", "SKIP"])
        rz = f2.selectbox("Reason Code",    ["ALL", "CB001", "CB002", "CB003", "CB004"])
        dmin = df_hist.predicted_at.min().date()
        dmax = df_hist.predicted_at.max().date()
        dr   = f3.date_input("Date Range", (dmin, max(dmin, dmax)))

        mask = pd.Series(True, index=df_hist.index)
        if rf != "ALL": mask &= df_hist.recommendation == rf
        if rz != "ALL": mask &= df_hist.reason_code == rz
        if len(dr) == 2:
            mask &= df_hist.predicted_at.dt.date.between(dr[0], dr[1])
        view = df_hist[mask]

        fought = view[(view.recommendation == "FIGHT") & view.actual_outcome.notna()]
        wr     = fought.actual_outcome.mean() if len(fought) else 0.0
        tot    = pd.to_numeric(view.get("amount_inr"), errors="coerce").fillna(0).sum()

        st.markdown(
            '<div class="ap-grid4" style="margin:10px 0 20px">' +
            kpi("Cases Logged",   f"{len(view):,}") +
            kpi("Win Rate",       f"{wr:.0%}", "of fought cases", AP_GREEN) +
            kpi("Avg P(Win)",     f"{view.win_probability.mean():.0%}" if len(view) else "—", "", AP_BLUE) +
            kpi("Total Disputed", f"₹{tot:,.0f}") +
            "</div>",
            unsafe_allow_html=True
        )

        eyebrow("Dispute Decision History")
        view_table = view.sort_values("predicted_at", ascending=False)[[
            "predicted_at", "chargeback_id", "amount_inr", "reason_code",
            "win_probability", "recommendation", "evidence_strength",
        ]].rename(columns={
            "predicted_at": "Date",
            "chargeback_id": "Case ID",
            "amount_inr": "Amount (₹)",
            "reason_code": "Reason",
            "win_probability": "P(Win)",
            "recommendation": "Decision",
            "evidence_strength": "Evidence Strength",
        })
        st.dataframe(view_table, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
# SIDEBAR (macOS HIG Palette)
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        f"""
        <div style="padding:10px 0 14px">
          <div class="ap-logo-icon" style="width:36px;height:36px;font-size:16px;border-radius:9px;margin-bottom:12px"></div>
          <div style="font-weight:800;color:{AP_TEXT};font-size:1.05rem;letter-spacing:-0.02em">Nexsus.Guard</div>
          <div style="font-size:0.75rem;color:{AP_MUTED};font-weight:500">AI Risk Manager · Apple HIG UI</div>
        </div>
        <div class="ap-divider"></div>

        <div class="ap-eyebrow">Model Architecture</div>
        <table style="font-size:0.78rem;line-height:2.2;width:100%;color:{AP_TEXT}">
          <tr><td style="color:{AP_MUTED}">Engine</td><td style="text-align:right"><b>XGBoost</b></td></tr>
          <tr><td style="color:{AP_MUTED}">Engineered Features</td><td style="text-align:right"><b>27</b></td></tr>
          <tr><td style="color:{AP_MUTED}">Dataset</td><td style="text-align:right"><b>50,000 cases</b></td></tr>
          <tr><td style="color:{AP_MUTED}">Decision Threshold</td><td style="text-align:right"><b>{state.trainer.recommended_threshold_:.2f}</b></td></tr>
          <tr><td style="color:{AP_MUTED}">Interpretability</td><td style="text-align:right"><b>SHAP Values</b></td></tr>
        </table>

        <div class="ap-divider"></div>
        <div class="ap-eyebrow">Decision Matrix</div>
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:16px">
          <span class="ap-badge b-green">FIGHT &nbsp;≥ {thr['fight_above']}</span>
          <span class="ap-badge b-yellow">REVIEW &nbsp;{thr['review_between'][0]}–{thr['review_between'][1]}</span>
          <span class="ap-badge b-red">SKIP &nbsp;≤ {thr['skip_below']}</span>
        </div>
        <div class="ap-divider"></div>
        """,
        unsafe_allow_html=True,
    )

    try:
        from utils.db import db_manager as _db
        preds = _db.get_all_predictions()
        st.markdown(kpi("Total Analyses", f"{len(preds):,}", "Persistent Database"), unsafe_allow_html=True)
    except Exception:
        pass

    st.markdown(
        f"""
        <div class="ap-footer">
          Designed with <a href="#">Apple Human Interface Guidelines</a><br/>
          Strictly Defence-Only · Razorpay Hackathon 2026<br/><br/>
          <span class="ap-badge b-blue" style="font-size:0.65rem">
             &nbsp;Apple Design System
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
