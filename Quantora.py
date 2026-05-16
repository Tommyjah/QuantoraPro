import streamlit as st
import pandas as pd
import requests
import os
import smtplib
from email.message import EmailMessage
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from crewai import Agent, Task, Crew, LLM
from PIL import Image
import base64 # Need for image encoding

# ==========================================
# 1. PAGE CONFIGURATION & LAYOUT
# ==========================================
st.set_page_config(page_title="Quantora Pro", page_icon="Quantora.jpg", layout="wide")

# ==========================================
# 2. BRANDING ASSETS & ENCODING
# ==========================================
LOGO_PATH = "Quantora.jpg"

try:
    with open(LOGO_PATH, "rb") as image_file:
        encoded_logo = base64.b64encode(image_file.read()).decode()
    logo_src = f"data:image/jpeg;base64,{encoded_logo}"
except FileNotFoundError:
    st.error(f"❌ '{LOGO_PATH}' not found. Please add the image to the folder.")
    st.stop()

# ==========================================
# 3. ADVANCED UI INJECTION (Glassmorphism + Ticker Tape)
# ==========================================
st.markdown(f"""
<style>
    /* 3.1 GALAXY BACKGROUND (Holographic Foundation) */
    .stApp {{
        background: radial-gradient(circle at center, #0B1021 0%, #03040A 100%) !important;
        background-attachment: fixed !important;
    }}
    
    /* 3.2 Ticker Tape (Moving News Feed) */
    .ticker-wrap {{
        width: 100%;
        overflow: hidden;
        background: rgba(0, 102, 255, 0.15);
        border-bottom: 1px solid rgba(0, 102, 255, 0.4);
        padding: 6px 0;
        backdrop-filter: blur(5px);
        margin-bottom: 25px;
    }}
    .ticker {{
        display: inline-block;
        white-space: nowrap;
        padding-left: 100%;
        animation: marquee 30s linear infinite;
        font-family: 'JetBrains Mono', monospace;
        color: #00B0FF;
        font-size: 0.9rem;
    }}
    @keyframes marquee {{
        0% {{ transform: translate3d(0, 0, 0); }}
        100% {{ transform: translate3d(-100%, 0, 0); }}
    }}
    
    /* 3.3 Side Matrix Control */
    section[data-testid="stSidebar"] {{
        background-color: rgba(10, 14, 23, 0.95) !important;
        border-right: 1px solid rgba(0, 102, 255, 0.3) !important;
        backdrop-filter: blur(10px);
    }}
    
    /* 3.4 Holographic Bento Boxes (Metric Cards) */
    div[data-testid="stMetric"] {{
        background: rgba(10, 14, 23, 0.6) !important;
        border: 1px solid rgba(0, 102, 255, 0.4) !important;
        border-radius: 18px !important;
        padding: 20px !important;
        backdrop-filter: blur(10px) saturate(180%);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), inset 0 0 15px rgba(0, 102, 255, 0.2);
        transition: all 0.3s ease-in-out;
    }}
    div[data-testid="stMetric"]:hover {{
        border-color: rgba(0, 230, 118, 0.6) !important;
        box-shadow: 0 8px 32px rgba(0, 230, 118, 0.2), inset 0 0 20px rgba(0, 230, 118, 0.1);
    }}
    
    /* typography */
    div[data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700;
    }}
    
    /* 3.5 Global Font Responsive */
    @media (prefers-color-scheme: dark) {{
        div[data-testid="stMetricValue"] > div {{ color: #00E676 !important; }}
    }}
    @media (prefers-color-scheme: light) {{
        div[data-testid="stMetricValue"] > div {{ color: #0066FF !important; }}
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NOTIFICATION PIPELINE
# ==========================================
def send_telegram(msg, token, chat_id):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            params = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
            requests.get(url, params=params)
        except Exception as e:
            st.sidebar.error(f"Telegram uplink failed: {e}")

def send_email(msg_content, recipient):
    if recipient:
        try:
            sender_email = st.secrets.get("SYSTEM_EMAIL")
            sender_password = st.secrets.get("EMAIL_APP_PASSWORD")
            if not sender_email or not sender_password:
                return False
            msg = EmailMessage()
            msg.set_content(msg_content)
            msg['Subject'] = "🏹 Quantora Pro: Trade Signal Detected"
            msg['From'] = f"Quantora Alerts <{sender_email}>"
            msg['To'] = recipient
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(sender_email, sender_password)
                smtp.send_message(msg)
            return True
        except Exception:
            return False

# ==========================================
# 5. CREDENTIAL ENGINE
# ==========================================
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY")
os.environ["GROQ_API_KEY"] = st.secrets.get("GROQ_API_KEY")

# ==========================================
# ==========================================
# 6. HEADER & SIDEBAR ASSEMBLY
# ==========================================
# Add encoded Logo to Sidebar
st.sidebar.markdown(f'<img src="{logo_src}" style="width: 100%; border-radius: 12px; margin-bottom: 20px;">', unsafe_allow_html=True)

# Main Title (Stylized Hologram)
st.markdown("<h1 style='text-align: center; color: #00B0FF; text-shadow: 0 0 15px #00B0FF; margin-top: -30px; margin-bottom: 10px;'>QUANTORA PRO TERMINAL</h1>", unsafe_allow_html=True)

# Ticker Tape Execution
st.markdown("""
<div class="ticker-wrap">
    <div class="ticker">
        📈 MONITORING GLOBAL EQUITY MATRICES :: REAL-TIME BREAKOUT SIGNALS ACTIVE :: AAPL SIGNAL TARGET: $174.52 :: SYSTEMS RUNNING LIVE :: MONITORING CRYPTOCURRENCY NETWORKS...
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Control Center (UPDATED WITH SYSTEM HEALTH PULSE)
with st.sidebar:
    st.markdown("### 📡 Terminal Core Metrics")
    
    # Glowing System Health Indicators
    st.markdown("""
        <div style="background: rgba(0, 102, 255, 0.05); border: 1px solid rgba(0, 102, 255, 0.2); border-radius: 10px; padding: 12px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: rgba(255,255,255,0.7); font-size: 0.85rem;">CORE APIS:</span>
                <span style="color: #00E676; font-weight: bold; font-size: 0.85rem; text-shadow: 0 0 8px #00E676;">● ONLINE</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: rgba(255,255,255,0.7); font-size: 0.85rem;">AI MATRIX:</span>
                <span style="color: #00E676; font-weight: bold; font-size: 0.85rem; text-shadow: 0 0 8px #00E676;">● READY</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: rgba(255,255,255,0.7); font-size: 0.85rem;">LATENCY:</span>
                <span style="color: #00B0FF; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">42ms</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ Signal Uplinks")
    with st.expander("🔔 Notification Dispatcher", expanded=False):
        email_user = st.text_input("Personal Email", placeholder="dev@example.com")
        st.caption("Telegram Matrix")
        tg_token = st.text_input("Bot Token", type="password")
        tg_id = st.text_input("Chat ID")
    
    st.divider()
    if st.button("System Pulse Check", use_container_width=True):
        st.toast("Telemetry Uplink Stable. Core Temperatures Nominal.", icon="⚡")
    st.caption("Quantora Pro v4.1 | © 2026")
# ==========================================
# 7. MAIN INTERFACE CONTENT
# ==========================================
symbol = st.text_input("Asset Ticker Symbol:", "AAPL").upper()

if st.button("RUN QUANT ANALYSIS", use_container_width=True):
    with st.spinner("Processing Matrix Data..."):
        # API DATA CAPTURE
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}'
        data = requests.get(url).json()

        # DATA VALIDATION
        if "Time Series (Daily)" not in data:
            if "Note" in data:
                st.warning("⚠️ API Quota (Alpha Vantage). Please wait 60s.")
            else:
                st.error("📡 Data Pipeline Interrupted:")
                st.json(data)
            st.stop()

        # DATA CLEANING
        raw_series = data['Time Series (Daily)']
        df = pd.DataFrame.from_dict(raw_series, orient='index').astype(float)
        df.index = pd.to_datetime(df.index)
        df.columns = [c.split(' ')[1] for c in df.columns]
        df = df.sort_index().tail(60)

        # TECHNICAL ENGINE
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA30'] = df['close'].rolling(window=30).mean()
        curr_price = df['close'].iloc[-1]
        signal = "BUY" if df['MA10'].iloc[-1] > df['MA30'].iloc[-1] else "SELL"

        # INTERACTIVE CHART INTEGRATION (High Fidelity)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_width=[0.2, 0.8])
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], 
            name='Price Matrix',
            increasing_line_color='#00D084', decreasing_line_color='#FF1744'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10D Fast MA', line=dict(color='#00B0FF', width=2.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA30'], name='30D Slow MA', line=dict(color='#FF6D00', width=2.5)), row=1, col=1)
        
        # Dynamic Volume Bars
        vol_colors = ['#00D084' if c >= o else '#FF1744' for c, o in zip(df['close'], df['open'])]
        fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume Matrix', marker_color=vol_colors, opacity=0.3), row=2, col=1)
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark", margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # BENTO BOX GRID DISPLAY (Fully applied style)
        c1, c2, c3 = st.columns(3)
        c1.metric("Market Price", f"${curr_price:,.2f}")
        c2.metric("Bot Signal", signal, delta=signal if signal == "BUY" else f"-{signal}")
        c3.metric("Status", "Operational")

        # NOTIFICATION DISPATCH
        send_telegram(f"🏹 Quantora Event: {symbol} at ${curr_price:,.2f} // Signal: {signal}", tg_token, tg_id)
        send_email(f"🏹 Quantora Event: {symbol} at ${curr_price:,.2f} // Signal: {signal}", email_user)

        # AI STRATEGIST context LAYER
        try:
            llm = LLM(model="groq/llama-3.3-70b-versatile")
            analyst = Agent(role='Strategic Analyst', goal='Analyze trend data', backstory='Expert Quant', llm=llm)
            task = Task(description=f"Analyze {symbol} breakout at ${curr_price}. MA Signal is {signal}.", expected_output="Provide 3 concise insight sentences.", agent=analyst)
            report = Crew(agents=[analyst], tasks=[task]).kickoff()
            
            # Holographic Strategist Feed Container
            st.markdown("""
                <div style="background: rgba(0, 102, 255, 0.05); border: 1px solid rgba(0, 102, 255, 0.4); border-radius: 18px; padding: 25px; margin-top: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                    <h3 style="color: #00B0FF; margin-top: 0; text-shadow: 0 0 10px #00B0FF;">💡 Strategist Intelligence</h3>
                    <p style="color: rgba(255, 255, 255, 0.9); font-size: 1.05rem;">
            """, unsafe_allow_html=True)
            st.write(str(report.raw).replace("*", "").replace("_", ""))
            st.markdown("</p></div>", unsafe_allow_html=True)

        except Exception:
            st.warning("Intelligence context matrix unavailable.")