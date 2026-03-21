import streamlit as st
import base64
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as GO
from plotly.subplots import make_subplots
from main import analyze_stock
import time
from datetime import datetime
import pytz

st.set_page_config(page_title="StockScore", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --page-bg: #0b1326;
  --sidebar-bg: #0d1526;
  --card-bg: #131d32;
  --elevated-card: #1a2540;
  --border-subtle: rgba(255,255,255,0.07);
  --border-visible: rgba(255,255,255,0.14);
  --primary-text: #e8eeff;
  --secondary-text: #a8b4cc;
  --muted-text: #6b7a99;
  --green: #4edea3;
  --amber: #ffb347;
  --red: #ff6b6b;
  --blue: #5b8dee;
  --interactive-blue: #357df1;
}

.stApp { background-color: var(--page-bg); color: var(--primary-text); font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background-color: var(--sidebar-bg); border-right: 1px solid var(--border-subtle); }

h1, h2, h3, h4, h5, h6, p, span, div { font-family: 'Inter', sans-serif; }
h1, h2, h3, h4, h5, h6 { color: var(--primary-text) !important; }

/* Global components */
.card { background: var(--card-bg); border: 1px solid var(--border-visible); border-radius: 14px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); margin-bottom: 20px; }
.card-header { font-size: 10px; text-transform: uppercase; color: var(--muted-text); margin-bottom: 8px; letter-spacing: 0.5px; font-weight: 600; }
.card-value { font-size: 26px; font-weight: 800; color: var(--primary-text); }
.card-label { font-size: 13px; color: var(--secondary-text); }

hr { border-color: var(--border-subtle); margin: 20px 0; }

table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border-subtle); color: var(--secondary-text); }
th { color: var(--primary-text); font-weight: 600; font-size: 13px; }
tr:nth-child(odd) { background-color: rgba(255,255,255,0.02); }
tr:nth-child(even) { background-color: transparent; }

.better { color: var(--green); font-weight: 600; }
.worse { color: var(--red); font-weight: 600; }
.neutral { color: var(--amber); }

/* Hide Streamlit Header */
[data-testid="stHeader"] { background: transparent !important; height: 0px !important; min-height: 0px !important; }
[data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
.stApp > header { display: none !important; }

/* Buttons & Pills */
.stButton>button { border-radius: 10px !important; font-weight: 600 !important; }
.stButton>button[kind="primary"] { background-color: var(--interactive-blue) !important; color: white !important; }

/* Secondary Buttons (Landing Chips, New Search) */
/* Secondary Buttons (Landing Chips, New Search) */
[data-testid="stButton"] button[kind="secondary"] {
  background-color: #1a2540 !important;
  background: #1a2540 !important;
  border: 1px solid rgba(255,255,255,0.15) !important;
  border-radius: 20px !important;
  color: #a8b4cc !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  padding: 4px 6px !important;
  min-width: 0px !important;
  width: 100% !important;
  height: 38px !important;
  min-height: 38px !important;
  white-space: nowrap !important;
  overflow: visible !important;
  text-align: center !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
  background-color: #1e2d4d !important;
  background: #1e2d4d !important;
  border: 1px solid #4edea3 !important;
  color: #4edea3 !important;
}

/* Search Input */
[data-testid="stTextInput"] input {
  background-color: #131d32 !important;
  color: #e8eeff !important;
  border: 1px solid rgba(255,255,255,0.15) !important;
  border-radius: 10px !important;
  caret-color: #357df1 !important;
}
[data-testid="stTextInput"] input::placeholder {
  color: #6b7a99 !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: #357df1 !important;
  box-shadow: 0 0 0 2px rgba(53,125,241,0.2) !important;
}

/* Sidebar Quick Analyze Chips */
[data-testid="stSidebar"] div.stButton > button {
  width: 100% !important;
  height: 32px !important;
  min-height: 32px !important;
  font-size: 10px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  padding: 2px 4px !important;
  border-radius: 8px !important;
  background: #1a2540 !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  color: #a8b4cc !important;
  text-align: center !important;
}

[data-testid="stSidebar"] div.stButton > button:hover {
  border-color: #4edea3 !important;
  color: #4edea3 !important;
}

.tick-pill { display: inline-block; background: var(--elevated-card); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 8px 16px; min-width: 110px; text-align: center; cursor: pointer; transition: 0.2s; white-space: nowrap; margin: 4px; }
.tick-pill:hover { border-color: var(--green); }
.tick-pill:hover .tp-text { color: var(--green); }
.tp-text { color: var(--primary-text); font-size: 13px; font-weight: 600; transition: 0.2s; }
.tp-sub { color: var(--muted-text); font-size: 11px; margin-left: 6px; }

/* Landing specifics */
.title-gradient { background: linear-gradient(135deg, var(--blue), var(--green)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 72px; font-weight: 800; text-align: center; margin-bottom: 0; line-height: 1.2; }
.subtitle { text-align: center; color: var(--secondary-text); font-size: 16px; margin-bottom: 40px; }
.feature-card {
  background: #131d32 !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 14px !important;
  padding: 24px !important;
  height: 200px !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
  transition: all 0.3s ease !important;
  text-align: left !important;
  box-sizing: border-box !important;
}
.feature-card:hover {
  border-color: rgba(78,222,163,0.25) !important;
  transform: translateY(-3px) !important;
  box-shadow: 0 10px 30px rgba(0,0,0,0.4) !important;
}
.feature-icon { font-size: 28px !important; margin-bottom: 12px !important; }
.feature-title { font-size: 14px !important; font-weight: 700 !important; color: #e8eeff !important; margin-bottom: 0px !important; }
.feature-desc { font-size: 12px !important; color: #6b7a99 !important; line-height: 1.6 !important; margin-top: 8px !important; }

/* Rating badges */
.rating-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.rb-strong { background: #0d3b2e; color: var(--green); }
.rb-good { background: #0d3b2e; color: var(--green); }
.rb-hold { background: #3b2a0d; color: var(--amber); }
.rb-weak { background: #3b0d0d; color: var(--red); }
.rb-avoid { background: #3b0d0d; color: var(--red); }

/* Observations */
.obs-row { display: flex; align-items: flex-start; margin-bottom: 12px; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
.obs-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; margin-right: 12px; flex-shrink: 0; }
.dot-pos { background: var(--green); box-shadow: 0 0 8px rgba(78,222,163,0.5); }
.dot-neg { background: var(--red); box-shadow: 0 0 8px rgba(255,107,107,0.5); }
.dot-neu { background: var(--amber); box-shadow: 0 0 8px rgba(255,179,71,0.5); }
.obs-text { color: var(--secondary-text); font-size: 13px; line-height: 1.5; }

/* Sidebar */
.sb-heading { font-size: 10px; text-transform: uppercase; color: var(--muted-text); margin-bottom: 12px; letter-spacing: 0.5px; font-weight: 600; }
.sb-pill { background: var(--elevated-card); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 6px 12px; color: var(--secondary-text); font-size: 12px; text-align: center; cursor: pointer; transition: 0.2s; margin-bottom: 8px; }
.sb-pill:hover { border-color: var(--green); color: var(--green); }
.sb-divider { height: 1px; background: rgba(255,255,255,0.05); margin: 20px 0; }
.pulse-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.pulse-green { background: var(--green); box-shadow: 0 0 8px rgba(78,222,163,0.6); animation: pulse 2s infinite; }
.pulse-red { background: var(--red); }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
.weight-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.weight-lbl { font-size: 13px; color: var(--secondary-text); }
.weight-val { font-size: 13px; font-weight: 700; color: var(--green); }
.weight-bar { height: 4px; border-radius: 2px; margin-bottom: 12px; }

/* Inactive tabs visibility fix */
[data-testid="stTabs"] [data-baseweb="tab"] p {
  color: #a8b4cc !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] p {
  color: #e8eeff !important;
}

</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# -----------------
# HELPERS
# -----------------
def format_large_number(value, symbol="$", is_price=False):
    if value is None or pd.isna(value): return "N/A"
    try:
        val = float(value)
        if is_price: return f"{symbol}{val:,.2f}"
        abs_v = abs(val)
        if abs_v >= 1e12: return f"{symbol}{val/1e12:.2f}T"
        if abs_v >= 1e9: return f"{symbol}{val/1e9:.2f}B"
        if abs_v >= 1e6: return f"{symbol}{val/1e6:.2f}M"
        if abs_v >= 1e3: return f"{symbol}{val/1e3:.2f}K"
        return f"{symbol}{val:.2f}"
    except:
        return "N/A"

def get_rating_colors(score):
    if score >= 75: return "#4edea3", "#0d3b2e", "#4edea3"
    elif score >= 60: return "#27ae60", "#0d3b2e", "#27ae60"
    elif score >= 45: return "#ffb347", "#3b2a0d", "#ffb347"
    elif score >= 30: return "#ff8c69", "#3b1a0d", "#ff8c69"
    else: return "#ff4757", "#3b0d0d", "#ff4757"

def render_score_ring(score):
    color = "#ff4757"
    if score >= 75: color = "#4edea3"
    elif score >= 60: color = "#27ae60"
    elif score >= 45: color = "#ffb347"
    elif score >= 30: color = "#ff8c69"
    
    pct = score / 100
    arc_len = 251.2 * 0.666 # 240 deg active arc out of 360
    fill_len = arc_len * pct
    
    html = f'<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">' \
           f'<div style="position: relative; width: 100px; height: 100px;">' \
           f'<svg viewBox="0 0 100 100" style="width: 100%; height: 100%; transform: rotate(150deg);">' \
           f'<circle cx="50" cy="50" r="40" fill="none" stroke="#1a2540" stroke-width="8" stroke-dasharray="{arc_len} {251.2 - arc_len}" stroke-dashoffset="0" stroke-linecap="round"/>' \
           f'<circle cx="50" cy="50" r="40" fill="none" stroke="{color}" stroke-width="8" stroke-dasharray="{fill_len} 251.2" stroke-linecap="round"/>' \
           f'</svg>' \
           f'<div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; flex-direction: column;">' \
           f'<span style="font-size: 36px; font-weight: 800; color: var(--primary-text); margin-top: 10px;">{score:.0f}</span>' \
           f'</div></div>' \
           f'<div style="font-size: 12px; color: var(--muted-text); margin-top: -5px;">Final Score / 100</div></div>'
    return html

def render_pillar_card(title, score, max_score, limited, color_border):
    pct = score / max_score if max_score > 0 else 0
    bg_color = "#ff6b6b"
    if pct >= 0.65: bg_color = "#4edea3"
    elif pct >= 0.40: bg_color = "#ffb347"
    
    display_score = round(score)
    
    html = f'<div class="card" style="min-height: 140px; border-top: 3px solid {color_border}; padding: 16px;">' \
           f'<div style="font-size: 14px; font-weight: 600; color: var(--primary-text); margin-bottom: 16px;">{title}</div>' \
           f'<div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px;">' \
           f'<div style="width: 100%; margin-right: 12px;">' \
           f'<div style="width: 100%; height: 6px; background: #1a2540; border-radius: 3px; overflow: hidden;">' \
           f'<div style="height: 100%; width: {pct*100}%; background: {bg_color}; border-radius: 3px;"></div>' \
           f'</div></div>' \
           f'<div style="white-space: nowrap;">' \
           f'<span style="font-size: 18px; font-weight: 700; color: {bg_color};">{display_score}</span>' \
           f'<span style="font-size: 13px; color: var(--muted-text);">/{max_score}</span>' \
           f'</div></div>' \
           f'<div style="text-align: right; font-size: 12px; color: var(--secondary-text);">{pct*100:.0f}%</div></div>'
    return html

# -----------------
# STATE
# -----------------
if "search_ticker" not in st.session_state: st.session_state.search_ticker = ""
if "search_ticker2" not in st.session_state: st.session_state.search_ticker2 = ""
if "do_search" not in st.session_state: st.session_state.do_search = False

# Load and encode logo for UI
img_b64 = ""
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
except Exception as e:
    pass

# -----------------
# SIDEBAR
# -----------------
with st.sidebar:
    # 1. Logo at top
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 20px;">
        <img src="data:image/png;base64,{img_b64}" style="width: 32px; height: 32px; border-radius: 8px; margin-right: 12px; box-shadow: 0 0 15px rgba(91,141,238,0.3);">
        <div style="font-size: 22px; letter-spacing: -0.5px;">
            <span style="font-weight: 800; color: #e8eeff;">Stock</span><span style="font-weight: 400; color: #a8b4cc;">Score</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Divider line
    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # 3. Market Status section
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    is_open = now.weekday() < 5 and (now.hour > 9 or (now.hour == 9 and now.minute >= 15)) and (now.hour < 15 or (now.hour == 15 and now.minute <= 30))
    st.markdown('<div class="sb-heading">MARKET STATUS</div>', unsafe_allow_html=True)
    if is_open:
        st.markdown(f'<div><span class="pulse-dot pulse-green"></span><span style="color:var(--primary-text); font-size:13px;">Market Open</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div><span class="pulse-dot pulse-red"></span><span style="color:var(--primary-text); font-size:13px;">Market Closed</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="color:var(--muted-text); font-size:11px; margin-top:4px;">{now.strftime("%I:%M %p IST")}</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div style="color:var(--muted-text); font-size:10px; text-align:center;">v1.0.4 - Release (Mar 21)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    
    # 5. Weights section
    st.markdown('<div class="sb-heading">WEIGHTS</div>', unsafe_allow_html=True)
    w_html = f"""
    <div class="weight-row"><span class="weight-lbl">Fundamentals</span><span class="weight-val">35</span></div>
    <div class="weight-bar" style="width: 35%; background: #4edea3;"></div>
    
    <div class="weight-row"><span class="weight-lbl">Valuation</span><span class="weight-val">25</span></div>
    <div class="weight-bar" style="width: 25%; background: #5b8dee;"></div>
    
    <div class="weight-row"><span class="weight-lbl">Technicals</span><span class="weight-val">20</span></div>
    <div class="weight-bar" style="width: 20%; background: #357df1;"></div>
    
    <div class="weight-row"><span class="weight-lbl">Ownership</span><span class="weight-val">10</span></div>
    <div class="weight-bar" style="width: 10%; background: #8b5cf6;"></div>
    
    <div class="weight-row" style="margin-top: 12px;"><span class="weight-lbl" style="color:var(--primary-text); font-weight:600;">Total Score</span><span class="weight-val" style="color:var(--primary-text);">90 → 100</span></div>
    """
    st.markdown(w_html, unsafe_allow_html=True)
    
    # 6. Divider line
    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    
    # 7. Quick Analyze section
    st.markdown('<div class="sb-heading">QUICK ANALYZE</div>', unsafe_allow_html=True)
    quick_tickers = [
        ("RELIANCE.NS", "RELIANCE"),
        ("TCS.NS", "TCS"),
        ("HDFCBANK.NS", "HDFC BNK"),
        ("INFY.NS", "INFY"),
        ("AAPL", "AAPL"),
        ("NVDA", "NVDA")
    ]
    q_cols = st.columns([1,1])
    for i, (ticker, label) in enumerate(quick_tickers):
        if q_cols[i%2].button(label, key=f"sb_q_{ticker}"):
            st.session_state.search_ticker = ticker
            st.session_state.do_search = True

    # 8. Divider line
    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    
    # 9. Compare Mode toggle
    st.markdown('<div class="sb-heading">COMPARE MODE</div>', unsafe_allow_html=True)
    is_compare = st.toggle("Compare", False, label_visibility="collapsed")
    
    # 10. Divider line
    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    
    # 11. Footer
    st.markdown('<div style="font-size:11px; font-style:italic; color:var(--muted-text);">For educational purposes only.<br>yfinance v0.2.54+</div>', unsafe_allow_html=True)

# -----------------
# DATA FETCHING UI
# -----------------
def get_company_name(info, ticker):
    return info.get("Company Name") or info.get("longName") or info.get("shortName") or ticker

def get_currency_symbol(info, ticker):
    s = info.get("currency_symbol")
    if s: return s
    if ticker.endswith(".NS") or ticker.endswith(".BO"): return "₹"
    return "$"

def render_52w_bar(curr, low, high):
    if not (curr and low and high) or high == low:
        return ""
    pct = max(0, min(1, (curr - low) / (high - low)))
    html = f"""
    <div style="padding: 0 8px; margin-top: 6px; width: 100%; box-sizing: border-box;">
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #6b7a99; margin-bottom: 3px;">
            <span>L</span>
            <span>H</span>
        </div>
        <div style="width: 100%; height: 4px; background: #1a2540; border-radius: 2px; position: relative;">
            <div style="position: absolute; width: 8px; height: 8px; border-radius: 50%; background: #357df1; top: -2px; transform: translateX(-50%); left: {pct*100}%;"></div>
        </div>
    </div>
    """
    return html

# -----------------
# MAIN APP ROUTING
# -----------------
if st.session_state.do_search:
    st.session_state.do_search = False
    st.rerun()

if not st.session_state.search_ticker and not is_compare:
    # -----------------
    # LANDING PAGE
    # -----------------
    c1, mid, c3 = st.columns([0.1, 3, 0.1])
    with mid:
        st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="text-align: center; margin-bottom: 20px;"><img src="data:image/png;base64,{img_b64}" style="width: 80px; height: 80px; border-radius: 20px; box-shadow: 0 0 30px rgba(91,141,238,0.2);"></div>', unsafe_allow_html=True)
        st.markdown('<h1 class="title-gradient" style="text-align: center;">StockScore</h1>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle" style="text-align: center;">AI-powered stock analysis. Uncover market insights and make smarter investment decisions.</div>', unsafe_allow_html=True)
        
        sc1, sc2 = st.columns([4, 1])
        with sc1:
            query = st.text_input("Search", placeholder="Enter ticker (e.g. AAPL, RELIANCE.NS)", label_visibility="hidden", key="land_q")
        with sc2:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True) # padding to align with input mostly
            if st.button("Analyze", use_container_width=True, type="primary"):
                if query:
                    st.session_state.search_ticker = query.upper()
                    st.rerun()
                    
        # Improved Ticker Chips
        pc_cols = st.columns(6)
        landing_chips = [
            ("RELIANCE.NS", "RELIANCE"),
            ("HDFCBANK.NS", "HDFC"),
            ("TCS.NS", "TCS"),
            ("AAPL", "AAPL"),
            ("GOOGL", "GOOGL"),
            ("NVDA", "NVDA")
        ]
        for i, (ticker, label) in enumerate(landing_chips):
            if pc_cols[i].button(label, key=f"chip_{ticker}", help=ticker):
                st.session_state.search_ticker = ticker
                st.rerun()
        
        st.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)
        
        # Row 1: 3 cards
        fc_cols_r1 = st.columns(3)
        cards_r1 = [
            ("📊", "Fundamentals", "ROE, margins, growth and debt ratios vs industry peers."),
            ("📈", "Technicals", "MA50, MA200, RSI, MACD and volume trend signals."),
            ("💰", "DCF Valuation", "Intrinsic value using 5-year free cash flow projections.")
        ]
        
        for i, (icon, title, desc) in enumerate(cards_r1):
            with fc_cols_r1[i]:
                st.markdown(f'''
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <div class="feature-title">{title}</div>
                    <div class="feature-desc">{desc}</div>
                </div>
                ''', unsafe_allow_html=True)
        
        st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)

        # Row 2: 2 cards centered
        fc_cols_r2 = st.columns([1, 1.5, 1.5, 1])
        cards_r2 = [
            ("🏆", "Smart Scoring", "Unified 0-100 score across all four analysis pillars."),
            ("⚖️", "Comparison", "Head-to-head metrics with winner highlighting.")
        ]
        
        for i, (icon, title, desc) in enumerate(cards_r2):
            with fc_cols_r2[i+1]:
                st.markdown(f'''
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <div class="feature-title">{title}</div>
                    <div class="feature-desc">{desc}</div>
                </div>
                ''', unsafe_allow_html=True)

else:
    # -----------------
    # RESULTS / COMPARE PAGE
    # -----------------
    if st.button("← New Search"):
        st.session_state.search_ticker = ""
        st.session_state.search_ticker2 = ""
        st.rerun()
        
    s1, s2, s3 = st.columns([5, 5, 2] if is_compare else [5, 1, 0.1])
    with s1:
        t1 = st.text_input("Ticker 1", value=st.session_state.search_ticker, label_visibility="collapsed", key="rs_t1")
    if is_compare:
        with s2:
            t2 = st.text_input("Ticker 2", value=st.session_state.search_ticker2, label_visibility="collapsed", key="rs_t2")
    
    with s3 if is_compare else s2:
        if st.button("Analyze", type="primary", use_container_width=True):
            st.session_state.search_ticker = t1.upper()
            if is_compare: st.session_state.search_ticker2 = t2.upper()
            st.rerun()

    st.markdown('<hr style="margin: 10px 0 20px 0;">', unsafe_allow_html=True)

    def do_analysis_with_progress(ticker):
        prog_container = st.empty()
        def p_cb(msg):
            prog_container.info(f"🔄 {msg}")
        res = analyze_stock(ticker, p_cb)
        prog_container.empty()
        return res

    if not is_compare and st.session_state.search_ticker:
        res = do_analysis_with_progress(st.session_state.search_ticker)
        
        if res["error"]:
            st.error("Analysis Failed")
            st.error(res["error_msg"])
        else:
            sym = get_currency_symbol(res["info"], res["ticker"])
            comp_name = get_company_name(res["info"], res["ticker"])
            
            cp = res["info"].get("currentPrice")
            pc = res["info"].get("previousClose")
            day_change_html = ""
            if cp and pc and pc > 0:
                dc = cp - pc
                dp = (dc / pc) * 100
                dc_col = "var(--green)" if dc >= 0 else "var(--red)"
                sign = "+" if dc >= 0 else ""
                day_change_html = f'<div style="font-size: 13px; color: {dc_col}; font-weight: 600; margin-top: 4px;">{sign}{dc:.2f} ({sign}{dp:.2f}%)</div>'
            
            # Summary Cards
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="card" style="min-height: 130px; padding: 15px;">{render_score_ring(res["score"]["final_score"])}</div>', unsafe_allow_html=True)
            
            c2.markdown(f'<div class="card" style="min-height: 130px;"><div class="card-header">COMPANY</div><div style="font-size:17px; font-weight:700; color:var(--primary-text); max-height: 48px; overflow:hidden;">{comp_name}</div><div style="font-size:13px; color:var(--blue); margin-top:4px;">{res["info"].get("sector", "Unknown")}</div></div>', unsafe_allow_html=True)
            
            w52_bar = render_52w_bar(cp, res["info"].get("fiftyTwoWeekLow"), res["info"].get("fiftyTwoWeekHigh"))
            c3.markdown(f'<div class="card" style="min-height: 130px;"><div class="card-header">CURRENT PRICE</div><div class="card-value">{format_large_number(cp, sym, True)}</div>{day_change_html}{w52_bar}</div>', unsafe_allow_html=True)
            
            dot_c, bg_c, text_c = get_rating_colors(res["score"]["final_score"])
            c4.markdown(f'<div class="card" style="min-height: 130px;"><div class="card-header">RATING</div><div style="display:flex; align-items:center; margin-top:12px;"><div style="width:12px; height:12px; border-radius:50%; background:{dot_c}; box-shadow:0 0 8px {dot_c}; margin-right:12px;"></div><div class="rating-badge" style="background:{bg_c}; color:{text_c}; font-size:14px; padding:6px 16px;">{res["score"]["rating"]}</div></div></div>', unsafe_allow_html=True)

            # Breakdown Pillars
            pc_cols = st.columns(4)
            ms = res["score"]["module_scores"]
            pc_cols[0].markdown(render_pillar_card("Fundamentals", ms["Fundamentals"]["score"], ms["Fundamentals"]["max"], ms["Fundamentals"]["limited_data"], "#4edea3"), unsafe_allow_html=True)
            pc_cols[1].markdown(render_pillar_card("Technicals", ms["Technicals"]["score"], ms["Technicals"]["max"], ms["Technicals"]["limited_data"], "#357df1"), unsafe_allow_html=True)
            pc_cols[2].markdown(render_pillar_card("Valuation", ms["Valuation"]["score"], ms["Valuation"]["max"], ms["Valuation"]["limited_data"], "#b91c1c"), unsafe_allow_html=True)
            pc_cols[3].markdown(render_pillar_card("Ownership", ms["Ownership"]["score"], ms["Ownership"]["max"], ms["Ownership"]["limited_data"], "#8b5cf6"), unsafe_allow_html=True)

            r_col, l_col = st.columns(2)
            with r_col:
                st.markdown('<div class="card-header">KEY FINANCIAL RATIOS</div>', unsafe_allow_html=True)
                src = res.get("industry_avg", {}).get("source", "fallback")
                src_col = "var(--green)" if "comput" in src else "var(--amber)"
                tbl = f'<table><tr><th>Metric</th><th>Company</th><th>Industry Avg <span style="color:{src_col}; font-weight:normal; font-size:10px; margin-left:6px;">({src})</span></th></tr>'
                
                ratios = res["fundamental"]["ratios"]
                avgs = res["industry_avg"].get("averages", {})
                
                rows = [
                    ("PE Ratio", ratios.get("PE Ratio"), avgs.get("pe"), False, True),
                    ("Price to Book", ratios.get("PB Ratio"), avgs.get("pb"), False, True),
                    ("ROE", ratios.get("ROE"), avgs.get("roe"), True, False),
                    ("Debt to Equity", ratios.get("Debt/Equity"), avgs.get("debt_equity"), False, True),
                    ("Net Profit Margin", ratios.get("Net Margin"), avgs.get("net_margin"), True, False),
                    ("Operating Margin", ratios.get("Operating Margin"), avgs.get("operating_margin"), True, False),
                    ("ROA", ratios.get("ROA"), avgs.get("roa"), True, False),
                    ("EV to EBITDA", None, None, False, True), # omitted for brevity unless in dict
                    ("PEG Ratio", ratios.get("PEG Ratio"), None, False, True),
                    ("Current Ratio", ratios.get("Current Ratio"), avgs.get("current_ratio"), False, False),
                    ("Revenue Growth YoY", ratios.get("Revenue Growth"), avgs.get("rev_growth"), True, False),
                    ("Earnings Growth YoY", ratios.get("Earnings Growth"), avgs.get("earn_growth"), True, False)
                ]
                
                for label, val, avg, is_pct, curr_lower_better in rows:
                    v_str = f"{val:.2f}{'%' if is_pct else 'x'}" if val is not None else "N/A"
                    a_str = f"{avg:.2f}{'%' if is_pct else 'x'}" if avg is not None else "N/A"
                    cls = ""
                    if val is not None and avg is not None:
                        if curr_lower_better: cls = "better" if val <= avg else "worse"
                        else: cls = "better" if val >= avg else "worse"
                    tbl += f'<tr><td style="font-size:13px; color:var(--secondary-text);">{label}</td><td class="{cls}" style="font-size:13px;">{v_str}</td><td style="font-size:13px;">{a_str}</td></tr>'
                tbl += '</table>'
                st.markdown(f'<div class="card" style="padding:0;">{tbl}</div>', unsafe_allow_html=True)

            with l_col:
                st.markdown('<div class="card-header">OBSERVATIONS & REASONING</div>', unsafe_allow_html=True)
                obs_html = '<div class="card" style="height: 520px; overflow-y: auto;">'
                for flag in res["score"]["reasoning"]:
                    dot_cls = "dot-neu"
                    if flag.startswith("[+]"): dot_cls = "dot-pos"
                    elif flag.startswith("[-]"): dot_cls = "dot-neg"
                    
                    text = flag[4:] if flag.startswith("[") else flag
                    obs_html += f'<div class="obs-row"><div class="obs-dot {dot_cls}"></div><div class="obs-text">{text}</div></div>'
                obs_html += '</div>'
                st.markdown(obs_html, unsafe_allow_html=True)

            # Chart
            st.markdown('<div class="card-header">PRICE HISTORY</div>', unsafe_allow_html=True)
            df = res["technical"].get("price_df_with_indicators")
            if df is not None and not df.empty:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(GO.Scatter(x=df["Date"], y=df["Close"], name="Close", line=dict(color="#5b8dee", width=2)), secondary_y=False)
                if "MA50" in df.columns: fig.add_trace(GO.Scatter(x=df["Date"], y=df["MA50"], name="MA50", line=dict(color="#ffb347", width=1.5, dash="dash")), secondary_y=False)
                if "MA200" in df.columns: fig.add_trace(GO.Scatter(x=df["Date"], y=df["MA200"], name="MA200", line=dict(color="#4edea3", width=1.5, dash="dash")), secondary_y=False)
                if "Support" in df.columns: fig.add_trace(GO.Scatter(x=df["Date"], y=df["Support"], name="Support", line=dict(color="#4edea3", width=1, dash="dot")), secondary_y=False)
                if "Resistance" in df.columns: fig.add_trace(GO.Scatter(x=df["Date"], y=df["Resistance"], name="Resistance", line=dict(color="#ff6b6b", width=1, dash="dot")), secondary_y=False)
                fig.add_trace(GO.Bar(x=df["Date"], y=df["Volume"], name="Volume", marker_color="rgba(255,255,255,0.08)"), secondary_y=True)
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    margin=dict(l=0, r=0, t=30, b=0), 
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="right", 
                        x=1,
                        font=dict(color="#e8eeff")
                    )
                )
                fig.update_layout(title=dict(text=f"{res['ticker']} Price History", font=dict(color="#e8eeff")))
                fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color="#a8b4cc"))
                fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)', secondary_y=False, tickfont=dict(color="#a8b4cc"))
                fig.update_yaxes(showgrid=False, secondary_y=True, tickfont=dict(color="#a8b4cc"))
                st.plotly_chart(fig, use_container_width=True)

            # Deep dive tabs
            t_fund, t_val, t_tech, t_own = st.tabs(["Fundamentals", "Valuation", "Technicals", "Ownership"])
            
            with t_fund:
                ratios = res["fundamental"].get("ratios", {})
                html = '<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top:20px;">'
                for k, v in ratios.items():
                    val_str = f"{v:.2f}" if v is not None else "N/A"
                    if v is not None and ('Growth' in k or 'Margin' in k or 'ROE' in k or 'ROA' in k): val_str += "%"
                    elif v is not None: val_str += "x"
                    html += f'<div class="card" style="margin-bottom:0;"><div class="card-header">{k}</div><div class="card-value" style="font-size:20px;">{val_str}</div></div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)
                
            with t_val:
                dcf = res["valuation"].get("dcf", {})
                c1, c2, c3 = st.columns(3)
                c1.markdown(f'<div class="card"><div class="card-header">Intrinsic Value (DCF)</div><div class="card-value">{format_large_number(dcf.get("intrinsic_value_per_share"), sym, True)}</div></div>', unsafe_allow_html=True)
                c2.markdown(f'<div class="card"><div class="card-header">Current Price</div><div class="card-value">{format_large_number(dcf.get("current_price"), sym, True)}</div></div>', unsafe_allow_html=True)
                
                up_val = dcf.get('upside_pct')
                up_str = f"{up_val:.2f}%" if up_val is not None else "N/A"
                up_col = "var(--green)" if up_val is not None and up_val > 0 else "var(--red)" if up_val is not None else "var(--primary-text)"
                c3.markdown(f'<div class="card"><div class="card-header">Upside</div><div class="card-value" style="color:{up_col}">{up_str}</div></div>', unsafe_allow_html=True)

            with t_tech:
                ti = res["technical"].get("indicators", {})
                html = '<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top:20px;">'
                mapping = {"MA50": "50-Day MA", "MA200": "200-Day MA", "RSI": "RSI (14d)", "MACD_Line": "MACD Line", "Signal_Line": "Signal Line", "MACD_Hist": "MACD Histogram", "Momentum_3M": "3-Month Momentum", "Pos_52W": "52-Week Position"}
                for k, v in mapping.items():
                    val = ti.get(k)
                    html += f'<div class="card" style="margin-bottom:0;"><div class="card-header">{v}</div><div class="card-value" style="font-size:20px;">{f"{val:.2f}" if val is not None else "N/A"}</div></div>'
                html += f'<div class="card" style="margin-bottom:0;"><div class="card-header">Golden Cross</div><div class="card-value" style="font-size:20px;">{"Yes ✅" if ti.get("Golden_Cross") else "No"}</div></div>'
                html += f'<div class="card" style="margin-bottom:0;"><div class="card-header">Death Cross</div><div class="card-value" style="font-size:20px;">{"Yes ⚠️" if ti.get("Death_Cross") else "No"}</div></div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)
                
            with t_own:
                om = res["ownership"].get("metrics", {})
                html = '<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top:20px;">'
                for k, v in om.items():
                    if k not in ["promoter_pct", "institutional_pct"]:
                        html += f'<div class="card" style="margin-bottom:0;"><div class="card-header">{k}</div><div class="card-value" style="font-size:20px;">{v}</div></div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)

    elif is_compare and st.session_state.search_ticker and st.session_state.search_ticker2:
        r1 = do_analysis_with_progress(st.session_state.search_ticker)
        r2 = do_analysis_with_progress(st.session_state.search_ticker2)
        
        c1, c2 = st.columns(2)
        
        for idx, (res, col) in enumerate([(r1, c1), (r2, c2)]):
            with col:
                # 1. Header Card (Score + Info + Rating)
                dot_c, bg_c, text_c = get_rating_colors(res["score"]["final_score"])
                st.markdown(f'<div class="card" style="display:flex; flex-direction:column; align-items:center; text-align:center;">'
                            f'<div style="width:60px; height:60px; border-radius:30px; background:var(--interactive-blue); display:flex; align-items:center; justify-content:center; font-size:24px; font-weight:800; color:white; margin-bottom:12px;">{res["ticker"][0] if res["ticker"] else "?"}</div>'
                            f'<div style="font-size:20px; font-weight:800; color:var(--primary-text);">{res["ticker"]}</div>'
                            f'<div style="font-size:13px; color:var(--secondary-text); margin-bottom:20px;">{get_company_name(res.get("info",{}), res["ticker"])}</div>'
                            f'{render_score_ring(res.get("score",{}).get("final_score",0))}'
                            f'<div style="margin: 20px 0;">'
                            f'<span class="rating-badge" style="background:{bg_c}; color:{text_c};">{res.get("score",{}).get("rating","")}</span>'
                            f'</div></div>', unsafe_allow_html=True)
                
                # 2. Price Card
                cp = res["info"].get("currentPrice") or res["info"].get("regularMarketPrice")
                sym = get_currency_symbol(res["info"], res["ticker"])
                dc = res["info"].get("regularMarketChange", 0)
                dp = res["info"].get("regularMarketChangePercent", 0)
                dc_col = "var(--green)" if dc >= 0 else "var(--red)"
                sign = "+" if dc >= 0 else ""
                day_change_html = f'<div style="font-size: 11px; color: {dc_col}; font-weight: 600; margin-top: 2px;">{sign}{dc:.2f} ({sign}{dp:.2f}%)</div>'
                w52_bar = render_52w_bar(cp, res["info"].get("fiftyTwoWeekLow"), res["info"].get("fiftyTwoWeekHigh"))
                
                st.markdown(f'<div class="card" style="margin-top:12px; min-height:100px;">'
                            f'<div class="card-header" style="font-size:10px;">CURRENT PRICE</div>'
                            f'<div class="card-value" style="font-size:20px;">{format_large_number(cp, sym, True)}</div>'
                            f'{day_change_html}{w52_bar}</div>', unsafe_allow_html=True)
                
                # 3. Pillar Cards (2x2 Grid)
                ms = res["score"]["module_scores"]
                p_html = '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:12px;">'
                p_html += render_pillar_card("Fundamentals", ms["Fundamentals"]["score"], ms["Fundamentals"]["max"], ms["Fundamentals"]["limited_data"], "#4edea3")
                p_html += render_pillar_card("Technicals", ms["Technicals"]["score"], ms["Technicals"]["max"], ms["Technicals"]["limited_data"], "#357df1")
                p_html += render_pillar_card("Valuation", ms["Valuation"]["score"], ms["Valuation"]["max"], ms["Valuation"]["limited_data"], "#ff4757")
                p_html += render_pillar_card("Ownership", ms["Ownership"]["score"], ms["Ownership"]["max"], ms["Ownership"]["limited_data"], "#8b5cf6")
                p_html += '</div>'
                st.markdown(p_html, unsafe_allow_html=True)
                
        def format_val(v, is_str=False, is_pct=False):
            if v is None: return "N/A"
            if is_str: return v
            return f"{v:.2f}{'%' if is_pct else ''}"
            
        def get_winner(v1, v2, low_better=False, is_str=False):
            if v1 is None or v2 is None or is_str: return "<div style='text-align:center;'>-</div>"
            if v1 == v2: return "<div style='text-align:center;'>-</div>"
            w1 = (v1 < v2 and low_better) or (v1 > v2 and not low_better)
            if w1: return f'<div style="text-align:center; color:var(--green); font-weight:bold;">↑ {st.session_state.search_ticker[:6]}</div>'
            return f'<div style="text-align:center; color:var(--green); font-weight:bold;">↑ {st.session_state.search_ticker2[:6]}</div>'

        f1, f2 = r1.get("fundamental",{}).get("ratios",{}), r2.get("fundamental",{}).get("ratios",{})
        v1, v2 = r1.get("valuation",{}).get("dcf",{}), r2.get("valuation",{}).get("dcf",{})
        o1, o2 = r1.get("ownership",{}).get("metrics",{}), r2.get("ownership",{}).get("metrics",{})
        te1, te2 = r1.get("technical",{}).get("indicators",{}), r2.get("technical",{}).get("indicators",{})

        t_html = f'<div class="card" style="padding:0; overflow:hidden;">' \
                 f'<table style="width:100%; border-collapse:collapse; table-layout:fixed;">' \
                 f'<thead><tr>' \
                 f'<th style="width:30%; background:#1a2540; color:#e8eeff; font-weight:600; font-size:12px; text-transform:uppercase; text-align:left; padding:12px;">METRIC</th>' \
                 f'<th style="width:23%; background:#1a2540; color:#e8eeff; font-weight:600; font-size:12px; text-transform:uppercase; text-align:center; padding:12px;">{r1["ticker"]}</th>' \
                 f'<th style="width:23%; background:#1a2540; color:#e8eeff; font-weight:600; font-size:12px; text-transform:uppercase; text-align:center; padding:12px;">{r2["ticker"]}</th>' \
                 f'<th style="width:24%; background:#1a2540; color:#e8eeff; font-weight:600; font-size:12px; text-transform:uppercase; text-align:center; padding:12px;">WINNER</th>' \
                 f'</tr></thead><tbody>'
        
        rows = [
            ("Overall Score", r1.get("score",{}).get("final_score"), r2.get("score",{}).get("final_score"), False, False, False),
            ("ROE", f1.get("ROE"), f2.get("ROE"), False, False, True),
            ("Net Margin", f1.get("Net Margin"), f2.get("Net Margin"), False, False, True),
            ("Operating Margin", f1.get("Operating Margin"), f2.get("Operating Margin"), False, False, True),
            ("PE Ratio", f1.get("PE Ratio"), f2.get("PE Ratio"), True, False, False),
            ("Debt to Equity", f1.get("Debt/Equity"), f2.get("Debt/Equity"), True, False, False),
            ("Revenue Growth", f1.get("Revenue Growth"), f2.get("Revenue Growth"), False, False, True),
            ("Earnings Growth", f1.get("Earnings Growth"), f2.get("Earnings Growth"), False, False, True),
            ("DCF Upside", v1.get("upside_pct"), v2.get("upside_pct"), False, False, True),
            ("Insider Holding", o1.get("Promoter Holding"), o2.get("Promoter Holding"), False, True, False)
        ]
        
        for name, val1, val2, low_better, is_str, is_pct in rows:
            v1_s = format_val(val1, is_str, is_pct)
            v2_s = format_val(val2, is_str, is_pct)
            win = get_winner(val1, val2, low_better, is_str)
            
            c1_win, c2_win = "", ""
            if val1 is not None and val2 is not None and not is_str:
                if (val1 < val2 and low_better) or (val1 > val2 and not low_better): c1_win = "better"; c2_win = "worse"
                elif val1 != val2: c1_win = "worse"; c2_win = "better"
                
            t_html += f'<tr>' \
                      f'<td style="padding:12px; font-weight:600; font-size:13px; color:var(--secondary-text);">{name}</td>' \
                      f'<td class="{c1_win}" style="padding:12px; text-align:center; font-weight:700;">{v1_s}</td>' \
                      f'<td class="{c2_win}" style="padding:12px; text-align:center; font-weight:700;">{v2_s}</td>' \
                      f'<td style="padding:12px; text-align:center;">{win}</td>' \
                      f'</tr>'

        rsi1, rsi2 = te1.get("RSI"), te2.get("RSI")
        t_html += f'<tr><td style="padding:12px; font-weight:600; font-size:13px; color:var(--secondary-text);">RSI (14d)</td><td style="padding:12px; text-align:center;">{format_val(rsi1)}</td><td style="padding:12px; text-align:center;">{format_val(rsi2)}</td><td style="padding:12px; text-align:center;">-</td></tr>'
        t_html += '</tbody></table></div>'
        
        st.markdown(t_html, unsafe_allow_html=True)
        
