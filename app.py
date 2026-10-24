import streamlit as st
import feedparser
import pandas as pd
import os
import requests
from sqlalchemy import create_engine

st.set_page_config(page_title="Dashboard Karhutla (+ Telegram Alert)", layout="wide")

try:
    TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception:
    TELEGRAM_TOKEN = "TOKEN_BOT_KAMU"
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

    df_new = pd.DataFrame(data)
    df_new['waktu_terbit'] = pd.to_datetime(df_new['waktu_terbit'])

    try:
        engine = get_db_engine()
        
        # Baca data lama dari DB kalau ada
        try:
            df_old = pd.read_sql('tren_karhutla', engine)
            # Gabungkan data lama & baru, lalu hapus duplikat berdasarkan link
            df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=['link'], keep='first')
        except Exception:
            df_combined = df_new

        # Simpan kembali akumulasi data secara utuh
        df_combined.to_sql('tren_karhutla', engine, if_exists='replace', index=False)
        return df_combined

    except Exception as e:
        print(f"Gagal simpan ke DB: {e}")
        return df_new

st.title("🔥 Dashboard Monitoring Karhutla (+ Telegram Alert)")
st.caption("Aplikasi ini otomatis akumulasi data berita dan ngirim alert Telegram.")

if st.sidebar.button("🔄 Refresh Data Sekarang"):
    st.cache_data.clear()

with st.spinner('Narik data terbaru...'):
    df = run_etl_realtime()

col1, col2 = st.columns(2)
col1.metric("Total Berita Terkumpul (Akumulatif)", len(df))
col2.metric("Jumlah Media Terlibat", df['sumber'].nunique())

st.divider()

st.subheader("📊 5 Media Paling Aktif Mengabarkan Karhutla")
media_counts = df['sumber'].value_counts().head(5)
st.bar_chart(media_counts)

st.subheader("📰 Daftar Berita Terbaru")
st.dataframe(df[['sumber', 'judul', 'waktu_terbit', 'link']], height=300)
