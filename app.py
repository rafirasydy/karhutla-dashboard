import streamlit as st
import feedparser
import pandas as pd
import os
import requests
from sqlalchemy import create_engine

st.set_page_config(page_title="Dashboard Karhutla (+ Telegram Alert)", layout="wide")

# Gunakan try-except agar tidak crash saat running di Docker lokal
try:
    TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception:
    TELEGRAM_TOKEN = "8892672599:AAGN5qaTrPP1G3h4xOmV30VceyZBXKvQTUY"
    TELEGRAM_CHAT_ID = "5141661421"

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:mysecretpassword@localhost:5432/postgres")

def get_db_engine():
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            pass
        return engine
    except Exception:
        return create_engine("sqlite:///karhutla_trends.db")

def send_telegram_alert(judul, link):
    if TELEGRAM_TOKEN == "TOKEN_BOT_KAMU":
        return
    message = f"⚠️ *PERINGATAN KARHUTLA DARURAT!*\n\n📰 *Judul:* {judul}\n🔗 *Baca:* {link}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Gagal kirim notifikasi: {e}")

@st.cache_data(ttl=600)
def run_etl_realtime():
    url = "https://news.google.com/rss/search?q=karhutla&hl=id&gl=ID&ceid=ID:id"
    feed = feedparser.parse(url)

    data = []
    keywords_darurat = ['siaga', 'darurat', 'evakuasi', 'parah', 'kritis', 'hebat', 'kebakaran', 'riau', 'kalimantan']

    for entry in feed.entries:
        judul = entry.title
        sumber = entry.source.title if 'source' in entry else 'Unknown'
        waktu = entry.published
        link = entry.link

        if any(kw in judul.lower() for kw in keywords_darurat):
            send_telegram_alert(judul, link)

        data.append({
            'judul': judul,
            'sumber': sumber,
            'waktu_terbit': waktu,
            'link': link
        })

    df = pd.DataFrame(data)
    df['waktu_terbit'] = pd.to_datetime(df['waktu_terbit'])

    try:
        engine = get_db_engine()
        df.to_sql('tren_karhutla', engine, if_exists='replace', index=False)
    except Exception as e:
        print(f"Gagal simpan ke DB: {e}")

    return df

st.title("🔥 Dashboard Monitoring Karhutla (+ Telegram Alert)")
st.caption("Aplikasi ini otomatis ngirim pesan ke Telegram kalau nemu berita berstatus darurat.")

if st.sidebar.button("🔄 Refresh Data Sekarang"):
    st.cache_data.clear()

with st.spinner('Narik data terbaru...'):
    df = run_etl_realtime()

col1, col2 = st.columns(2)
col1.metric("Total Berita Terkumpul", len(df))
col2.metric("Jumlah Media Terlibat", df['sumber'].nunique())

st.divider()

st.subheader("📊 5 Media Paling Aktif Mengabarkan Karhutla")
media_counts = df['sumber'].value_counts().head(5)
st.bar_chart(media_counts)

st.subheader("📰 Daftar Berita Terbaru")
st.dataframe(df[['sumber', 'judul', 'waktu_terbit', 'link']], height=300)
