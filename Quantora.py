import streamlit as st
import pandas as pd
import requests
import os
import smtplib
from email.message import EmailMessage
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from crewai import Agent, Task, Crew, LLM
import base64
import yfinance as fy

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
    .stApp {{
        background: radial-gradient(circle at center, #0B1021 0%, #03040A 100%) !important;
        background-attachment: fixed !important;
    }}
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
    section[data-testid="stSidebar"] {{
        background-color: rgba(10, 14, 23, 0.95) !important;
        border-right: 1px solid rgba(0, 102, 255, 0.3) !important;
        backdrop-filter: blur(10px);
    }}
    div[data-testid="stMetric"] {{
        background: rgba(10, 14, 23, 0.6) !important;
        border: 1px solid rgba(0, 102, 255, 0.4) !important;
        border-radius: 18px !important;
        padding: 20px !important;
        backdrop-filter: blur(10px) saturate(180%);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), inset 0 0 15px rgba(0, 102, 255, 0.2);
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700;
    }}
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
# 4.5 TICKER TAPE LIVE DATA ENGINE
# ==========================================
def fetch_ticker_tape_matrix():
    tickers_map = {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "BTC-USD": "BITCOIN",
        "ETH-USD": "ETHEREUM",
        "EURUSD=X": "EUR/USD"
    }
    tape_elements = []
    try:
        import yfinance as yf
        for sym, label in tickers_map.items():
            try:
                ticker_obj = yf.Ticker(sym)
                df_hist = ticker_obj.history(period="7d", interval="1d")
                if df_hist.empty or len(df_hist) < 2:
                    continue
                if isinstance(df_hist.columns, pd.MultiIndex):
                    df_hist.columns = df_hist.columns.get_level_values(-1)
                df_hist.columns = [str(col).lower() for col in df_hist.columns]
                
                if 'close' in df_hist.columns:
                    close_curr = float(df_hist['close'].values[-1])
                    close_prev = float(df_hist['close'].values[-2])
                    change = close_curr - close_prev
                    pct = (change / close_prev) * 100
                    sign = "▲" if change >= 0 else "▼"
                    color = "#00E676" if change >= 0 else "#FF1744"
                    
                    if "USD" in sym or "BTC" in sym or "ETH" in sym:
                        fmt_price = f"${close_curr:,.2f}"
                    elif "X" in sym:
                        fmt_price = f"${close_curr:.4f}"
                    else:
                        fmt_price = f"{close_curr:,.2f}"
                        
                    tape_elements.append(
                        f"🔹 {label}: <span style='color:{color}; font-weight:bold;'>{fmt_price} {sign} {pct:.2f}%</span>"
                    )
            except Exception:
                continue
    except Exception:
        return "📈 QUANTORA PRO SUITE ONLINE :: PIPELINE RUNNING..."

    if len(tape_elements) > 0:
        return " &nbsp;&nbsp;&nbsp;&nbsp;::&nbsp;&nbsp;&nbsp;&nbsp; ".join(tape_elements)
    return "📈 SECURING DATA PIPELINE LINK..."

# ==========================================
# 5. CREDENTIAL ENGINE
# ==========================================
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY")
os.environ["GROQ_API_KEY"] = st.secrets.get("GROQ_API_KEY")

# ==========================================
# 6. HEADER & SIDEBAR ASSEMBLY
# ==========================================
live_tape_stream = fetch_ticker_tape_matrix()
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker">
        {live_tape_stream} :: TERMINAL READY FOR ANALYSIS ENGINE...
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    # 🌟 FIXED: Renders logo at the top of the sidebar view
    st.image(LOGO_PATH, use_container_width=True)
    
    st.markdown("### 📡 Terminal Core Metrics")
    st.markdown("""
        <div style="background: rgba(0, 102, 255, 0.05); border: 1px solid rgba(0, 102, 255, 0.2); border-radius: 10px; padding: 12px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: rgba(255,255,255,0.7); font-size: 0.85rem;">DATA CHANNEL:</span>
                <span style="color: #00B0FF; font-weight: bold; font-size: 0.85rem; text-shadow: 0 0 8px #00B0FF;">● HYBRID ENGINE</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: rgba(255,255,255,0.7); font-size: 0.85rem;">AI MATRIX:</span>
                <span style="color: #00E676; font-weight: bold; font-size: 0.85rem; text-shadow: 0 0 8px #00E676;">● READY</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: rgba(255,255,255,0.7); font-size: 0.85rem;">LATENCY:</span>
                <span style="color: #00B0FF; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">19ms</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 Asset Profile Engine")
    asset_class = st.selectbox(
        "Select Asset Class Matrix:",
        ["Equities (Stocks)", "Digital Assets (Crypto)", "Foreign Exchange (Forex)"]
    )
    
    trading_style = st.selectbox(
        "Execution Strategy Blueprint:",
        ["⚡ Scalper Profile (M5/M15 Fast Horizon)", "⏳ Swing Profile (H4/D1 Trend Horizon)"]
    )
    
    if "Equities" in asset_class:
        ticker_placeholder = "e.g., AAPL, NVDA, TSLA"
    elif "Digital" in asset_class:
        ticker_placeholder = "e.g., BTC-USD, ETH-USD"
    else:
        ticker_placeholder = "e.g., EURGBP=X, EURUSD=X"

    st.markdown("---")
    st.subheader("⚙️ Strategy Tuning Knobs")
    
    with st.expander("📊 Momentum & Volatility Parameters", expanded=True):
        rsi_period = st.slider("RSI Lookback Period", min_value=5, max_value=30, value=14, step=1)
        bb_period = st.slider("Bollinger Period", min_value=10, max_value=50, value=20, step=1)
        bb_std = st.slider("Bollinger Std Dev", min_value=1.0, max_value=3.5, value=2.0, step=0.1)
        atr_period = st.slider("ATR Volatility Window", min_value=5, max_value=25, value=14, step=1)
        atr_multiplier_input = st.slider("ATR Risk Multiplier", min_value=1.5, max_value=5.0, value=3.0, step=0.1)

    st.markdown("---")
    st.markdown("### ⚙️ Signal Uplinks")
    with st.expander("🔔 Notification Dispatcher", expanded=False):
        email_user = st.text_input("Personal Email", placeholder="dev@example.com")
        st.caption("Telegram Matrix")
        tg_token = st.text_input("Bot Token", type="password")
        tg_id = st.text_input("Chat ID")
    
    st.divider()
    if st.button("System Pulse Check", use_container_width=True):
        st.toast("Telemetry Uplink Stable. Indicator Matrix Compiling.", icon="⚡")
    st.caption("Quantora Pro v4.7 | © 2026")

# ==========================================
# 7. MAIN INTERFACE WORKSPACE INPUTS
# ==========================================
col_input, col_style = st.columns([3, 1])

with col_input:
    symbol = st.text_input("Active Target Symbol:", value="AAPL", placeholder=ticker_placeholder).upper()

with col_style:
    st.markdown(f"""
        <div style="background: rgba(0, 102, 255, 0.1); border: 1px solid rgba(0, 102, 255, 0.3); border-radius: 10px; padding: 10px; text-align: center; margin-top: 28px;">
            <span style="color: #00B0FF; font-weight: bold; font-size: 0.85rem;">MODE ACTIVE</span><br>
            <span style="color: #FFF; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">{trading_style.split(' ')[1]}</span>
        </div>
    """, unsafe_allow_html=True)

# Initialize reactive calculations in state tracking mapping matrix
if 'last_calculated_symbol' not in st.session_state:
    st.session_state['last_calculated_symbol'] = None

run_clicked = st.button("RUN QUANT ANALYSIS", use_container_width=True)

# ==========================================
# 8. HYBRID ROUTING DATA MATRIX & CALC ENGINE (REACTIVE TO SIDEBAR CONTROLS)
# ==========================================
if run_clicked or (st.session_state['last_calculated_symbol'] == symbol):
    if run_clicked:
        st.session_state['last_calculated_symbol'] = symbol

    with st.spinner("Processing Matrix Data Pipeline..."):
        df = None
        engine_used = "Alpha Vantage"
        force_yfinance = False
        if ("Digital" in asset_class or "Foreign" in asset_class) and "Scalper" in trading_style:
            force_yfinance = True

        if not force_yfinance:
            try:
                if "Equities" in asset_class:
                    if "Scalper" in trading_style:
                        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={ALPHA_VANTAGE_KEY}'
                        time_key = "Time Series (5min)"
                    else:
                        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}'
                        time_key = "Time Series (Daily)"
                elif "Digital" in asset_class:
                    url = f'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol.replace("-USD","")}&market=USD&apikey={ALPHA_VANTAGE_KEY}'
                    time_key = "Time Series (Digital Currency Daily)"
                elif "Foreign" in asset_class:
                    clean_sym = symbol.replace("=X","")
                    url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={clean_sym[:3]}&to_symbol={clean_sym[3:]}&apikey={ALPHA_VANTAGE_KEY}'
                    time_key = "Time Series FX (Daily)"

                data = requests.get(url).json()
                if time_key in data:
                    raw_series = data[time_key]
                    df = pd.DataFrame.from_dict(raw_series, orient='index').astype(float)
                    df.index = pd.to_datetime(df.index)
                    df.columns = [c.split('. ')[1] if '. ' in c else c.split(' ')[1] if ' ' in c else c for c in df.columns]
                    if 'close (USD)' in df.columns:
                        df = df.rename(columns={'open (USD)': 'open', 'high (USD)': 'high', 'low (USD)': 'low', 'close (USD)': 'close', 'volume': 'volume'})
                else:
                    force_yfinance = True
            except Exception:
                force_yfinance = True

        if force_yfinance or df is None:
            engine_used = "Yahoo Finance (Failover Uplink)"
            try:
                yf_ticker = symbol
                if "Foreign" in asset_class and not yf_ticker.endswith("=X"):
                    yf_ticker = f"{yf_ticker[:3]}{yf_ticker[3:]}=X"
                elif "Digital" in asset_class and not yf_ticker.endswith("-USD"):
                    yf_ticker = f"{yf_ticker.replace('USD','')}-USD"

                interval_param = "5m" if "Scalper" in trading_style else "1d"
                period_param = "5d" if "Scalper" in trading_style else "120d"
                
                ticker_obj = fy.Ticker(yf_ticker)
                df_raw = ticker_obj.history(period=period_param, interval=interval_param)
                if not df_raw.empty:
                    df = df_raw[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    df.columns = ['open', 'high', 'low', 'close', 'volume']
                else:
                    st.error(f"🚨 Ticker trace fault: {symbol}")
                    st.stop()
            except Exception as e:
                st.error(f"📡 System Core Outage: {e}")
                st.stop()

        df = df.sort_index()

        # ==========================================
        # 9. RUNTIME DATA MATHEMATICS (DYNAMICALLY BOUND)
        # ==========================================
        high_low = df['high'] - df['low']
        high_cp = (df['high'] - df['close'].shift()).abs()
        low_cp = (df['low'] - df['close'].shift()).abs()
        df['TR'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = df['TR'].rolling(window=int(atr_period)).mean().fillna(df['TR'].mean())
        
        df['BB_MA'] = df['close'].rolling(window=int(bb_period)).mean()
        df['BB_STD'] = df['close'].rolling(window=int(bb_period)).std()
        df['BB_Upper'] = df['BB_MA'] + (float(bb_std) * df['BB_STD'])
        df['BB_Lower'] = df['BB_MA'] - (float(bb_std) * df['BB_STD'])
        
        change = df['close'].diff()
        gain = change.mask(change < 0, 0.0)
        loss = -change.mask(change > 0, 0.0)
        avg_gain = gain.ewm(com=int(rsi_period) - 1, min_periods=int(rsi_period)).mean()
        avg_loss = loss.ewm(com=int(rsi_period) - 1, min_periods=int(rsi_period)).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50)

        if "Scalper" in trading_style:
            df['Fast_Ind'] = df['close'].ewm(span=9, adjust=False).mean()
            df['Slow_Ind'] = df['close'].ewm(span=21, adjust=False).mean()
            ind_label_1, ind_label_2 = "9 EMA", "21 EMA"
        else:
            df['Fast_Ind'] = df['close'].rolling(window=10).mean()
            df['Slow_Ind'] = df['close'].rolling(window=30).mean()
            ind_label_1, ind_label_2 = "10 MA", "30 MA"
            
        active_atr_multiplier = float(atr_multiplier_input)

        # Update analytical framework indicators into persistent state tracking
        st.session_state['quant_df'] = df.copy()
        st.session_state['engine_used'] = engine_used
        st.session_state['ind_label_1'] = ind_label_1
        st.session_state['ind_label_2'] = ind_label_2
        st.session_state['active_atr_multiplier'] = active_atr_multiplier
        st.session_state['data_initialized'] = True

# ==========================================
# RENDER RETAINED ARTIFACTS
# ==========================================
# 🌟 FIXED: Moved outside the strict button conditional so it NEVER disappears on slider actions
if st.session_state.get('data_initialized'):
    df = st.session_state['quant_df'].copy()
    engine_used = st.session_state['engine_used']
    ind_label_1 = st.session_state['ind_label_1']
    ind_label_2 = st.session_state['ind_label_2']
    active_atr_multiplier = st.session_state['active_atr_multiplier']
    
    df_slice = df.tail(60)
    curr_price = df_slice['close'].iloc[-1]
    atr_val = df_slice['ATR'].iloc[-1]
    latest_rsi = df_slice['RSI'].iloc[-1]
    latest_upper_bb = df_slice['BB_Upper'].iloc[-1]
    latest_lower_bb = df_slice['BB_Lower'].iloc[-1]

    clean_price = f"${curr_price:,.2f}"
    clean_rsi = f"{latest_rsi:.1f}"
    clean_upper_bb = f"${latest_upper_bb:,.2f}"
    clean_lower_bb = f"${latest_lower_bb:,.2f}"

    if df_slice['Fast_Ind'].iloc[-1] > df_slice['Slow_Ind'].iloc[-1]:
        signal = "BUY"
        stop_loss = df_slice['high'].tail(14).max() - (active_atr_multiplier * atr_val)
        if stop_loss >= curr_price: stop_loss = curr_price - (active_atr_multiplier * atr_val)
        take_profit = curr_price + (active_atr_multiplier * 1.8 * atr_val)
    else:
        signal = "SELL"
        stop_loss = df_slice['low'].tail(14).min() + (active_atr_multiplier * atr_val)
        if stop_loss <= curr_price: stop_loss = curr_price + (active_atr_multiplier * atr_val)
        take_profit = curr_price - (active_atr_multiplier * 1.8 * atr_val)

    df_slice = df_slice.copy()
    df_slice['Trailing_SL'] = stop_loss

    sim_signals = df['Fast_Ind'] > df['Slow_Ind']
    win_count = (sim_signals == (df['close'].shift(-1) > df['close'])).tail(20).sum()
    win_rate = (win_count / 20) * 100

    # 10. MULTI-PANEL VISUALIZATION COMPLEX
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.15, 0.65])
    fig.add_trace(go.Candlestick(x=df_slice.index, open=df_slice['open'], high=df_slice['high'], low=df_slice['low'], close=df_slice['close'], name='Price Matrix', increasing_line_color='#00D084', decreasing_line_color='#FF1744'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Upper'], name='Upper BB', line=dict(color='rgba(0, 176, 255, 0.3)', width=1, dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Lower'], name='Lower BB', line=dict(color='rgba(0, 176, 255, 0.3)', width=1, dash='dash'), fill='tonexty', fillcolor='rgba(0, 176, 255, 0.02)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['Fast_Ind'], name=ind_label_1, line=dict(color='#00B0FF', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['Slow_Ind'], name=ind_label_2, line=dict(color='#FF6D00', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['Trailing_SL'], name='Volatility Stop', line=dict(color='#FFD600', width=1.5, dash='dot')), row=1, col=1)
    
    vol_colors = ['#00D084' if c >= o else '#FF1744' for c, o in zip(df_slice['close'], df_slice['open'])]
    fig.add_trace(go.Bar(x=df_slice.index, y=df_slice['volume'], name='Volume', marker_color=vol_colors, opacity=0.3), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['RSI'], name='RSI', line=dict(color='#E040FB', width=2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=[70]*len(df_slice), name='Overbought (70)', line=dict(color='rgba(255, 23, 68, 0.4)', width=1, dash='dash'), showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=[30]*len(df_slice), name='Oversold (30)', line=dict(color='rgba(0, 230, 118, 0.4)', width=1, dash='dash'), showlegend=False), row=3, col=1)
    
    fig.update_yaxes(range=[10, 90], row=3, col=1)
    fig.update_layout(xaxis_rangeslider_visible=False, height=700, template="plotly_dark", margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Pipeline Routing Vector: {engine_used}")
    
    # INDENTATION FIX CONFIRMED
    Shelton_c1, Shelton_c2, Shelton_c3, Shelton_c4 = st.columns(4)
    Shelton_c1.metric("Current Rate", f"${curr_price:,.4f}" if "Foreign" in asset_class else f"${curr_price:,.2f}")
    Shelton_c2.metric("Matrix Signal", signal, delta=signal if signal == "BUY" else f"-{signal}")
    Shelton_c3.metric("RSI Momentum", f"{latest_rsi:.1f}")
    Shelton_c4.metric("Win-Rate Tracker", f"{win_rate:.1f}%")

    # 🌟 FIXED: This layout box will now persist on slider changes
    st.markdown(f"""
        <div style="background: rgba(0, 102, 255, 0.03); border: 1px solid rgba(0, 102, 255, 0.2); border-radius: 12px; padding: 20px; margin-top: 20px;">
            <h4 style="color: #00B0FF; margin-top:0;">📋 Algorithmic Risk Blueprint ({trading_style.split(' ')[1]})</h4>
            <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                <p style="margin: 5px 15px 5px 0;">🎯 <b>Execution Entry:</b> {"${curr_price:,.4f}" if "Foreign" in asset_class else f"${curr_price:,.2f}"}</p>
                <p style="margin: 5px 15px 5px 0; color: #FF1744;">🛑 <b>ATR Volatility Trailing Stop:</b> ${stop_loss:,.2f}</p>
                <p style="margin: 5px 15px 5px 0; color: #00D084;">💰 <b>Take Profit Target:</b> ${take_profit:,.2f}</p>
                <p style="margin: 5px 15px 5px 0; color: #E040FB;">🌐 <b>Bollinger Bands Envelope:</b> [{clean_lower_bb} - {clean_upper_bb}]</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 11. AI COGNITIVE STRATEGIST FEED
    # ==========================================
    if run_clicked: 
        try:
            llm = LLM(model="groq/llama-3.3-70b-versatile")
            analyst = Agent(role='Strategic Quantitative Lead', goal='Draft technical summaries for structural traders', backstory='Elite systemic market analyst', llm=llm)
            task = Task(
                description=(f"Analyze {symbol} under the {trading_style} profile. The current operational action is {signal} at precisely {clean_price}. The momentum RSI is {clean_rsi} and the Bollinger envelope limits are defined from {clean_lower_bb} up to {clean_upper_bb}. The trailing stop loss is ${stop_loss:.2f}."),
                expected_output=("A sharp, professional 3-sentence risk management assessment brief factoring in the exact RSI and Bollinger values provided. Do not use any markdown bolding, stars, asterisks (*), or headers in the text."),
                agent=analyst
            )
            report = Crew(agents=[analyst], tasks=[task]).kickoff()
            st.session_state['cached_ai_report'] = str(report.raw).replace("*", "").replace("_", "").strip()
        except Exception as ai_err:
            st.session_state['cached_ai_report'] = f"Intelligence layer sync cycle bypass active. Diagnostic note: {str(ai_err)}"

    if 'cached_ai_report' in st.session_state:
        st.markdown("""<div style="background: rgba(0, 102, 255, 0.05); border: 1px solid rgba(0, 102, 255, 0.4); border-radius: 18px; padding: 25px; margin-top: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);"><h3 style="color: #00B0FF; margin-top: 0; text-shadow: 0 0 10px #00B0FF;">💡 Strategist Intelligence</h3><p style="color: rgba(255, 255, 255, 0.9); font-size: 1.05rem; line-height: 1.6;">""", unsafe_allow_html=True)
        st.write(st.session_state['cached_ai_report'])
        st.markdown("</p></div>", unsafe_allow_html=True)

    # ==========================================
    # 12. DETERMINISTIC BACKTESTING ENGINE
    # ==========================================
    st.markdown("---")
    st.markdown("## 📈 Dynamic Strategy Backtest Simulator")

    try:
        bt_core = df.copy()
        st.markdown("#### ⚙️ Strategy Entry / Exit Optimization")
        slider_col1, slider_col2 = st.columns(2)
        
        with slider_col1:
            bt_rsi_buy = st.slider("RSI Entry Target (Buy Signal Threshold)", min_value=15, max_value=50, value=40, step=1, key="strategy_rsi_entry_slider")
        with slider_col2:
            bt_rsi_sell = st.slider("RSI Profit Target (Sell Signal Threshold)", min_value=50, max_value=85, value=60, step=1, key="strategy_rsi_exit_slider")
        
        st.markdown("<br>", unsafe_allow_html=True)

        bt_core = bt_core.dropna(subset=['BB_MA', 'RSI'])

        bt_core['Buy_Signal'] = (bt_core['close'] <= bt_core['BB_MA']) & (bt_core['RSI'] < float(bt_rsi_buy))
        bt_core['Sell_Signal'] = (bt_core['close'] >= bt_core['BB_MA']) | (bt_core['RSI'] > float(bt_rsi_sell))
        
        backtest_df = bt_core.copy()
        
        position = False
        entry_p = 0.0
        trades_logged = []
        
        for idx, row in backtest_df.iterrows():
            if not position and bool(row['Buy_Signal']):
                position = True
                entry_p = float(row['close'])
            elif position and bool(row['Sell_Signal']) and entry_p > 0:
                exit_p = float(row['close'])
                pct_return = ((exit_p - entry_p) / entry_p) * 100
                trades_logged.append(pct_return)
                position = False
                
        total_trades = len(trades_logged)
        if total_trades > 0:
            winning_trades = len([t for t in trades_logged if t > 0])
            win_rate_calc = (winning_trades / total_trades) * 100
            gross_return = sum(trades_logged)
            avg_gain = gross_return / total_trades
        else:
            total_trades = 0
            win_rate_calc = 0.0
            gross_return = 0.0
            avg_gain = 0.0
            
        b1, b2, b3, b4 = st.columns(4)
        perf_color = "#00E676" if gross_return >= 0 else "#FF1744"
        
        b1.markdown(f"<div style='background:rgba(10,14,23,0.6); border:1px solid rgba(0,102,255,0.2); padding:15px; border-radius:12px; text-align:center;'><h5 style='margin:0; color:rgba(255,255,255,0.6); font-size:0.85rem;'>SIMULATED TRADES</h5><h2 style='margin:10px 0 0 0; font-family:\"JetBrains Mono\"; color:#00B0FF;'>{total_trades}</h2></div>", unsafe_allow_html=True)
        b2.markdown(f"<div style='background:rgba(10,14,23,0.6); border:1px solid rgba(0,102,255,0.2); padding:15px; border-radius:12px; text-align:center;'><h5 style='margin:0; color:rgba(255,255,255,0.6); font-size:0.85rem;'>BACKTEST WIN-RATE</h5><h2 style='margin:10px 0 0 0; font-family:\"JetBrains Mono\"; color:#00E676;'>{win_rate_calc:.1f}%</h2></div>", unsafe_allow_html=True)
        b3.markdown(f"<div style='background:rgba(10,14,23,0.6); border:1px solid rgba(0,102,255,0.2); padding:15px; border-radius:12px; text-align:center;'><h5 style='margin:0; color:rgba(255,255,255,0.6); font-size:0.85rem;'>GROSS METRIC RETURN</h5><h2 style='margin:10px 0 0 0; font-family:\"JetBrains Mono\"; color:{perf_color};'>{gross_return:+.2f}%</h2></div>", unsafe_allow_html=True)
        b4.markdown(f"<div style='background:rgba(10,14,23,0.6); border:1px solid rgba(0,102,255,0.2); padding:15px; border-radius:12px; text-align:center;'><h5 style='margin:0; color:rgba(255,255,255,0.6); font-size:0.85rem;'>EXPECTANCY / TRADE</h5><h2 style='margin:10px 0 0 0; font-family:\"JetBrains Mono\"; color:{perf_color};'>{avg_gain:+.2f}%</h2></div>", unsafe_allow_html=True)
        
    except Exception as backtest_err:
        st.warning(f"Backtester performance engine failure: {backtest_err}")