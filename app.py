import time
import tempfile
import base64
from datetime import datetime

import pandas as pd
import yfinance as yf
from gtts import gTTS
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="株価読み上げ（MVP）", page_icon="📈", layout="centered")
st.title("📈 株価読み上げ（MVP）")

# --- セッション状態 ---
ss = st.session_state
ss.setdefault("interval_sec", 60)

# --- 入力UI ---
tickers_text = st.text_input("ティッカー（例：BTC-USD, NVDA, 7203.T）", value="BTC-USD, NVDA")
interval_label = st.selectbox("自動更新間隔", ["手動のみ", "1分", "3分", "5分"], index=1)
interval_map = {"手動のみ": 0, "1分": 60, "3分": 180, "5分": 300}
ss.interval_sec = interval_map[interval_label]

manual_btn = st.button("最新価格を取得")

# --- 株価取得 ---
def fetch_many(text: str) -> pd.DataFrame:
    rows = []
    for t in [s.strip().upper() for s in text.split(",") if s.strip()]:
        try:
            info = yf.Ticker(t).info
            rows.append({
                "ticker": t,
                "name": info.get("shortName") or t,
                "price": info.get("regularMarketPrice"),
                "currency": info.get("currency"),
            })
        except Exception:
            rows.append({"ticker": t, "name": "取得失敗", "price": None, "currency": ""})
    return pd.DataFrame(rows)

def summarize_simple(df: pd.DataFrame) -> str:
    now = datetime.now().strftime("%H時%M分")
    parts = [f"{now}。"]
    for _, r in df.iterrows():
        if pd.isna(r["price"]):
            parts.append(f"{r['ticker']} 取得失敗。")
            continue
        parts.append(f"{r['name']} {r['price']:.2f} {r['currency']}。")
    return " ".join(parts)

# --- 音声合成 ---
def synth_mp3(text: str, lang="ja") -> tuple[str, str]:
    uid = str(int(time.time() * 1000))
    tmp = tempfile.NamedTemporaryFile(delete=False, prefix=f"tts_{uid}_", suffix=".mp3")
    # 無音を最後に追加することでブラウザが確実に再生扱いする
    tts = gTTS(text=text + " 。", lang=lang)  
    tts.save(tmp.name)
    return tmp.name, uid

def audio_autoplay_html(mp3_path: str, uid: str, play_rate: float = 1.2) -> str:
    with open(mp3_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    audio_id = f"auto_audio_{uid}"
    return f"""
    <audio id="{audio_id}" autoplay>
      <source src="data:audio/mp3;base64,{b64}" type="audio/mpeg">
    </audio>
    <script>
      (function() {{
        const a = document.getElementById("{audio_id}");
        if (!a) return;
        a.playbackRate = {play_rate};
        const tryPlay = () => a.play().catch(()=>{{}});
        a.addEventListener('canplaythrough', tryPlay);
        a.addEventListener('loadeddata', tryPlay);
        document.addEventListener('click', tryPlay, {{ once: true }});
        tryPlay();
      }})();
    </script>
    """

def do_fetch_and_speak():
    df = fetch_many(tickers_text)
    text = summarize_simple(df)
    mp3_path, uid = synth_mp3(text)
    st.dataframe(df, use_container_width=True)
    st.write("🗣️", text)
    st.markdown(audio_autoplay_html(mp3_path, uid), unsafe_allow_html=True)

# --- 手動 ---
if manual_btn:
    do_fetch_and_speak()

# --- 自動 ---
if ss.interval_sec > 0:
    count = st_autorefresh(interval=ss.interval_sec * 1000, key="auto_refresh")
    if count > 0:
        do_fetch_and_speak()