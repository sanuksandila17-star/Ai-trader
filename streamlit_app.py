import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
import concurrent.futures # වේගවත් ස්කෑන් කිරීම සඳහා

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Apex Void Sovereign E-Wave", page_icon="🔱")

st.markdown("""
    <style>
    .stApp { background-color: #010203; color: #e0e6ed; }
    .wave-signal { 
        background: rgba(13, 17, 23, 0.9); border: 1px solid #30363d; 
        border-radius: 12px; padding: 15px; margin-bottom: 10px; border-left: 5px solid #f0b90b;
    }
    .super-signal { border-left: 5px solid #00ff7f !important; box-shadow: 0px 0px 15px rgba(0, 255, 127, 0.2); }
    </style>
""", unsafe_allow_html=True)

class ElliottBrain:
    @staticmethod
    def get_waves(df):
        df['ewo'] = df['close'].ewm(span=5).mean() - df['close'].ewm(span=35).mean()
        df['vol_ma'] = df['volume'].rolling(window=20, min_periods=1).mean()
        return df

    @staticmethod
    def identify_wave_stage(df):
        if len(df) < 10: return None, None, 0
        last, prev = df.iloc[-1], df.iloc[-2]
        avg_vol = df['vol_ma'].iloc[-1]
        
        score = 75
        is_wave_3_bull = (last['ewo'] > prev['ewo']) and (last['ewo'] > 0)
        is_wave_3_bear = (last['ewo'] < prev['ewo']) and (last['ewo'] < 0)
        
        if is_wave_3_bull or is_wave_3_bear:
            side = "BUY" if is_wave_3_bull else "SELL"
            stage = "WAVE 3"
            if last['volume'] > avg_vol: score += 15
            if abs(last['close'] - last['open']) > (last['high'] - last['low']) * 0.5: score += 10
            return stage, side, min(score, 100)
        return None, None, 0

# --- 2. ENGINE ---
exchange = ccxt.binance({'options': {'defaultType': 'swap'}, 'enableRateLimit': True})

if 'signals' not in st.session_state: st.session_state.signals = {}
if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"

def check_coin(sym):
    """ තනි කොයින් එකක් පරීක්ෂා කරන Function එක """
    try:
        bars = exchange.fetch_ohlcv(sym, timeframe='5m', limit=40)
        df = pd.DataFrame(bars, columns=['time','open','high','low','close','volume'])
        df = ElliottBrain.get_waves(df)
        stage, side, score = ElliottBrain.identify_wave_stage(df)
        if stage and score >= 80:
            return sym, {
                'stage': stage, 'side': side, 'price': df['close'].iloc[-1],
                'tp': df['close'].iloc[-1] * (1.02 if side == "BUY" else 0.98),
                'sl': df['close'].iloc[-1] * (0.995 if side == "BUY" else 1.005),
                'score': score, 'time': datetime.now().strftime("%H:%M:%S")
            }
    except: return None

def fast_scan():
    try:
        markets = exchange.load_markets()
        pairs = [m for m in markets if markets[m].get('linear') and markets[m].get('quote') == 'USDT' and not any(x in m for x in ['UP/', 'DOWN/'])]
        
        # එකවර කොයින් 50ක් ස්කෑන් කරයි (Multi-threading)
        selected_pairs = random.sample(pairs, min(len(pairs), 60))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(check_coin, selected_pairs))
            
        for res in results:
            if res:
                sym, data = res
                st.session_state.signals[sym] = data
    except Exception as e:
        st.error(f"Scan Error: {e}")

# --- 3. UI ---
st.title("🔱 APEX VOID: SOVEREIGN")

col_a, col_b = st.columns([1, 2.3])

with col_a:
    if st.button("⚡ FORCE SCAN"): fast_scan()
    
    # සිග්නල් ලිස්ට් එක පෙන්වීම
    if not st.session_state.signals:
        st.info("Scanning for Impulse Waves... Please wait.")
    
    for sym, sig in list(st.session_state.signals.items())[::-1]:
        card_class = "wave-signal super-signal" if sig['score'] >= 90 else "wave-signal"
        st.markdown(f"""
        <div class="{card_class}">
            <h3 style="margin:0; color:#f0b90b;">{sym} <span style="float:right; font-size:14px;">{sig['score']}%</span></h3>
            <b style="color:{'#00ff7f' if sig['side'] == 'BUY' else '#ff4b4b'}">{sig['side']} | {sig['stage']}</b><br>
            <small>Price: {sig['price']} | {sig['time']}</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"View {sym}", key=f"btn_{sym}"):
            st.session_state.active_coin = sym

with col_b:
    st.subheader(f"Analysis: {st.session_state.active_coin}")
    try:
        bars = exchange.fetch_ohlcv(st.session_state.active_coin, timeframe='5m', limit=100)
        df_plot = pd.DataFrame(bars, columns=['time','open','high','low','close','volume'])
        df_plot['time'] = pd.to_datetime(df_plot['time'], unit='ms')
        df_plot = ElliottBrain.get_waves(df_plot)
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_plot['time'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close']), row=1, col=1)
        fig.add_trace(go.Bar(x=df_plot['time'], y=df_plot['ewo'], marker_color=['#00ff7f' if v > 0 else '#ff4b4b' for v in df_plot['ewo']]), row=2, col=1)
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except: pass

# ස්වයංක්‍රීයව ස්කෑන් කිරීම
fast_scan()
time.sleep(5)
st.rerun()
        
