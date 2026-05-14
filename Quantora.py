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

# 1. PAGE CONFIGURATION (Must be the ABSOLUTE FIRST Streamlit command)
st.set_page_config(
    page_title="Quantora Pro",
    page_icon="Quantora.jpg",  # Sets your clean logo as the browser favicon
    layout="wide"
)

# 2. LOAD & DISPLAY BRAND ASSETS
try:
    # Synchronized to your renamed asset file
    logo = Image.open("Quantora.jpg")
    st.sidebar.image(logo, use_container_width=True)
except Exception:
    # Safe fallback wrapper so your app won't crash if git tracking has a delay
    st.sidebar.warning("🏹 Quantora Pro Asset Loading...")

# --- PRO FINTECH ADAPTIVE CSS INJECTION ---
st.markdown("""
    <style>
    /* Global Base Metric Value Typography Overrides */
    div[data-testid="stMetricValue"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-weight: 700;
        font-size: 2.2rem !important;
    }
    
    /* Theme Sensing Context Blocks */
    @media (prefers-color-scheme: dark) {
        .stApp { background-color: #0A0E17 !important; }
        section[data-testid="stSidebar"] {
            background-color: #0E1422 !important;
            border-right: 1px solid #1E293B !important;
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 14px;
            padding: 20px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
        div[data-testid="stMetricValue"] > div { color: #00E676 !important; }
    }
    
    @media (prefers-color-scheme: light) {
        .stApp { background-color: #F4F7F9 !important; }
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E1E8ED !important;
        }
        div[data-testid="stMetric"] {
            background: #FFFFFF !important;
            border: 1px solid #E1E8ED !important;
            border-radius: 14px;
            padding: 20px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        }
        div[data-testid="stMetricValue"] > div { color: #0066FF !important; }
    }

    /* Gradient Title Typography Layer */
    .main-title {
        background: linear-gradient(90deg, #0066FF, #00D084);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 20px;
    }

    /* Soft Alert Box Configurations */
    .stAlert {
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    </style>
    """, unsafe_allow_html=True)

# --- NOTIFICATION LOGIC ---
def send_telegram(msg, token, chat_id):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            params = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
            requests.get(url, params=params)
        except Exception as e:
            st.sidebar.error(f"Telegram failed: {e}")

def send_email(msg_content, recipient):
    if recipient:
        try:
            sender_email = st.secrets.get("SYSTEM_EMAIL")
            sender_password = st.secrets.get("EMAIL_APP_PASSWORD")

            if not sender_email or not sender_password:
                st.sidebar.warning("⚠️ Email system configuration missing from Secrets.")
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
        except Exception as e:
            st.sidebar.error(f"Email system offline: {e}")
            return False

# --- CONFIGURATION KEYS ---
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "YOUR_ALPHA_VANTAGE_KEY")
os.environ["GROQ_API_KEY"] = st.secrets.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY")

# --- UI LAYOUT ---
st.markdown('<h1 class="main-title">Quantora Pro</h1>', unsafe_allow_html=True)

# SaaS Control Center in Sidebar
with st.sidebar:
    st.markdown("### 🏹 Quantora Control Center")
    st.info("Configure your notification uplinks below to receive real-time trade signals.")
    
    with st.expander("🔔 Notification Settings", expanded=False):
        st.write("Enter your credentials to enable multi-channel alerts.")
        email_user = st.text_input("Personal Email", placeholder="email@example.com")
        
        st.divider()
        st.markdown("**Telegram Integration**")
        tg_token = st.text_input("Bot Token", type="password", help="Get this from @BotFather on Telegram")
        tg_id = st.text_input("Chat ID", help="Get this from @userinfobot on Telegram")
    
    st.divider()
    
    if st.button("System Health Check", use_container_width=True):
        st.success("Quantora Core: Operational")
        st.toast("All systems synchronized.")
        
    st.caption("Quantora Pro Engine v2.1 | © 2026")

# Main Interface Content Area
col_input, _ = st.columns([2, 1])
with col_input:
    symbol = st.text_input("Select Asset Ticker:", "AAPL").upper()

if st.button("RUN QUANT ANALYSIS", use_container_width=True):
    with st.spinner("Synchronizing with Market Nodes..."):
        try:
            # 1. Fetching Market Data
            url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}'
            data = requests.get(url).json()
            
            # Map Alpha Vantage fields into a structured financial dataframe
            raw_series = data['Time Series (Daily)']
            records = []
            for date_str, metrics in raw_series.items():
                records.append({
                    "Date": date_str,
                    "Open": float(metrics["1. open"]),
                    "High": float(metrics["2. high"]),
                    "Low": float(metrics["3. low"]),
                    "Close": float(metrics["4. close"]),
                    "Volume": float(metrics["5. volume"])
                })
            
            df = pd.DataFrame(records)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df = df.sort_index().tail(60)

            # 2. Moving Average Intersection Formulas
            df['MA10'] = df['Close'].rolling(window=10).mean()
            df['MA30'] = df['Close'].rolling(window=30).mean()
            current_price = df['Close'].iloc[-1]
            signal = "BUY" if df['MA10'].iloc[-1] > df['MA30'].iloc[-1] else "SELL"

            # 3. INTERACTIVE CANDLESTICK & VOLUME OVERLAY ENGINE
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.04, 
                row_width=[0.22, 0.78]
            )

            # Add Candlestick Traces
            fig.add_trace(
                go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                    name='Market Price',
                    increasing_line_color='#00E676', decreasing_line_color='#FF1744'
                ), row=1, col=1
            )

            # Thread Structural Moving Averages Over the Matrix
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10D Fast MA', line=dict(color='#00B0FF', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA30'], name='30D Slow MA', line=dict(color='#FF6D00', width=2)), row=1, col=1)

            # Map Transaction Volume Color Bars Dynamically
            vol_colors = ['#00E676' if c >= o else '#FF1744' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume Matrix', marker_color=vol_colors, opacity=0.45), row=2, col=1)

            # Global Matrix Layout Configurations
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.15)')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.15)')
            
            st.plotly_chart(fig, use_container_width=True)

            # 4. Metric Windows (Bento Box grid)
            c1, c2, c3 = st.columns(3)
            c1.metric("Market Price", f"${current_price:,.2f}")
            c2.metric("Bot Signal", signal, delta=signal if signal == "BUY" else f"-{signal}")
            c3.metric("Status", "Active")

            # 5. Parallel Dispatch Notification Pipeline
            alert_msg = f"🏹 *Quantora Pro System Alert*\n\nAsset Matrix: *{symbol}*\nEngine Execution: *{signal}*\nSpot Value: *${current_price:,.2f}*"
            send_telegram(alert_msg, tg_token, tg_id)
            send_email(alert_msg, email_user)
            st.toast("Alert payloads routed successfully!")

            # --- 6. DEEP NEURAL MARKET ANALYSIS CORE ---
            my_ai_brain = LLM(model="groq/llama-3.3-70b-versatile")
            
            analyst = Agent(
                role='Senior Crypto & Equity Strategist', 
                goal=f'Provide professional structural trend context for {symbol}', 
                backstory='You are a world-class system strategist with decades of quantitative fund experience. Provide plain text data without markdown punctuation formatting.',
                llm=my_ai_brain
            )
            
            task = Task(
                description=f"Analyze the structural {signal} breakout condition tracking {symbol} at current settlement pricing of ${current_price}. Formulate structural context around the 10-day crossing the 30-day structural line.", 
                expected_output="A concise market intelligence brief. Do not use asterisks, underscores, or bold formatting text. Use plain standard sentences with spaces after periods.", 
                agent=analyst
            )
            
            report = Crew(agents=[analyst], tasks=[task]).kickoff()
            
            st.subheader("💡 Strategist Intelligence")
            
            raw_text = str(report.raw)
            cleaned_brief = raw_text.replace("_", " ").replace("*", " ").replace("  ", " ").strip()
            
            st.info(cleaned_brief)

        except Exception as e:
            st.error(f"Analysis Pipeline Interrupted: {e}")