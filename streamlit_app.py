import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
import random

# --- 1. CONFIG & SYSTEM INTERFACE ---
st.set_page_config(layout="wide", page_title="Apex Void Sovereign E-Wave", page_icon="🔱")

# UI එක පිරිසිදු කිරීමට සහ HTML code පෙනීම වැලැක්වීමට CSS
st.markdown("""
    <style>
    .stApp { background-color: #010203; color: #e0e6ed; }
    [data-testid="stVerticalBlock"] > div:contains("Detected at") {
        display: none;
    }
    .wave-signal { 
        background: rgba(13, 17, 23, 0.9); 
        border: 1px solid #30363d; border-radius: 12px; padding: 15px;
        margin-bottom: 10px; border-left: 5px solid #f0b90b;
    }
    .super-signal { 
        border-left: 5px solid #00ff7f !important;
        background: linear-gradient(135deg, #051a10 0%, #0d1117 100%) !important;
        box-shadow: 0px 0px 15px rgba(0, 255, 127, 0.2);
    }
    .status-pulse { color: #00ff00; font-weight: bold; animation: blink 2s infinite; }
    @keyframes blink { 0% { opacity: 0.2; } 50% { opacity: 1; } 100% { opacity: 0.2; } }
    </style>
""", unsafe_allow_html=True)

# --- 2. ELLIOTT WAVE INTELLIGENCE CLASS ---
class ElliottBrain:
    @staticmethod
    def get_waves(df):
        df['ewo'] = df['close'].ewm(span=5).mean() - df['close'].ewm(span=35).mean()
        df['vol_ma'] = df['volume'].rolling(window=20, min_periods=1).mean()
        return df

    @staticmethod
    def identify_wave_stage(df):
        if len(df) < 5: return None, None, 0
        last = df.iloc[-1]
        prev = df.iloc[-2]
        avg_vol = df['vol_ma'].iloc[-1]
        
        score = 70
        is_wave_3_bull = (last['ewo'] > prev['ewo']) and (last['ewo'] > 0) and (last['close'] > prev['high'])
        is_wave_3_bear = (last['ewo'] < prev['ewo']) and (last['ewo'] < 0) and (last['close'] < prev['low'])
        
        if is_wave_3_bull or is_wave_3_bear:
            side = "BUY" if is_wave_3_bull else "SELL"
            stage = f"WAVE 3 (IMPULSE) {'🚀' if side == 'BUY' else '📉'}"
            if last['volume'] > avg_vol: score += 20
            if abs(last['close'] - last['open']) > (last['high'] - last['low']) * 0.6: score += 10
            return stage, side, min(score, 100)
        return None, None, 0

# --- 3. CORE ENGINE INITIALIZATION ---
exchange = ccxt.binance({'options': {'defaultType': 'swap'}, 'enableRateLimit': True})

if 'signals' not in st.session_state: st.session_state.signals = {}
if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"

def fast_scan():
    try:
        markets = exchange.load_markets()
        pairs = [m for m in markets if markets[m].get('linear') and markets[m].get('quote') == 'USDT' and not any(x in m for x in ['UP/', 'DOWN/', 'BEAR/', 'BULL/'])]
        selected = random.sample(pairs, min(len(pairs), 20))
        
        for sym in selected:
            bars = exchange.fetch_ohlcv(sym, timeframe='5m', limit=50)
            if not bars: continue
            df = pd.DataFrame(bars, columns=['time','open','high','low','close','volume'])
            df = ElliottBrain.get_waves(df)
            stage, side, score = ElliottBrain.identify_wave_stage(df)
            
            if stage and score >= 85:
                st.session_state.signals[sym] = {
                    'stage': stage, 'side': side, 'price': df['close'].iloc[-1],
                    'tp': df['close'].iloc[-1] * (1.025 if side == "BUY" else 0.975),
                    'sl': df['close'].iloc[-1] * (0.993 if side == "BUY" else 1.007),
                    'score': score, 'time': datetime.now().strftime("%H:%M:%S")
                }
    except: pass

# --- 4. UI RENDER ---
st.title("🔱 APEX VOID: ELLIOTT WAVE SOVEREIGN")
st.markdown(f"System Status: <span class='status-pulse'>🧬 ANALYZING FUTURES FRACTALS...</span>", unsafe_allow_html=True)

col_a, col_b = st.columns([1, 2.3])

with col_a:
    st.subheader("📡 Fractal Wave Radar")
    if st.button("⚡ FORCE GLOBAL SCAN"):
        fast_scan()
    
    # HTML Rendering Fix: f-string එක ඇතුලේ කෙලින්ම div එක render කිරීම
    for sym, sig in list(st.session_state.signals.items())[::-1]:
        is_super = sig['score'] >= 90
        card_class = "wave-signal super-signal" if is_super else "wave-signal"
        
        # HTML එක Markdown එකක් ලෙස වෙනමම render කිරීම
        st.markdown(f"""
        <div class="{card_class}">
            <h3 style="margin:0; color:#f0b90b;">{sym} <span style="float:right; font-size:12px; color:#00ff7f;">{sig['score']}%</span></h3>
            <p style="margin:5px 0; font-weight:bold; color:{'#00ff7f' if sig['side'] == 'BUY' else '#ff4b4b'}">{sig['stage']}</p>
            <div style="font-size:14px; line-height:1.6;">
                <b>Price:</b> {sig['price']:.4f} | <b>Side:</b> {sig['side']}<br>
                <span style="color:#00ff7f;">TP: {sig['tp']:.4f}</span> | <span style="color:#ff4b4b;">SL: {sig['sl']:.4f}</span><br>
                <small style="color:#666;">Detected: {sig['time']}</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"Analyze {sym.split('/')[0]}", key=f"btn_{sym}"):
            st.session_state.active_coin = sym

with col_b:
    st.subheader(f"📈 Wave Projection: {st.session_state.active_coin}")
    try:
        bars = exchange.fetch_ohlcv(st.session_state.active_coin, timeframe='5m', limit=100)
        df_plot = pd.DataFrame(bars, columns=['time','open','high','low','close','volume'])
        df_plot['time'] = pd.to_datetime(df_plot['time'], unit='ms')
        df_plot = ElliottBrain.get_waves(df_plot)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df_plot['time'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], name="Price"), row=1, col=1)
        colors = ['#00ff7f' if v > 0 else '#ff4b4b' for v in df_plot['ewo']]
        fig.add_trace(go.Bar(x=df_plot['time'], y=df_plot['ewo'], marker_color=colors, name="EWO"), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.info("Waiting for data...")

# Background Auto-Scan
fast_scan()
time.sleep(10)
st.rerun()
      
