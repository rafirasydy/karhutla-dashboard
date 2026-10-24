import streamlit as st
import feedparser
import pandas as pd
import os
import requests
import plotly.express as px
from sqlalchemy import create_engine

st.set_page_config(page_title="Dashboard Karhutla Real-Time", layout="wide", page_icon="🔥")

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
        try:
            df_old = pd.read_sql('tren_karhutla', engine)
            df_old['waktu_terbit'] = pd.to_datetime(df_old['waktu_terbit'])
            df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=['link'], keep='first')
        except Exception:
            df_combined = df_new

        df_combined.to_sql('tren_karhutla', engine, if_exists='replace', index=False)
        return df_combined

    except Exception as e:
        print(f"Gagal simpan ke DB: {e}")
        return df_new

# --- TAMPILAN DASHBOARD ---
st.title("🔥 Dashboard Monitoring Karhutla Real-Time")
st.caption("Monitoring publikasi media massa terkait Karhutla dan otomatisasi alert Telegram.")

if st.sidebar.button("🔄 Refresh Data Sekarang", use_container_width=True):
    st.cache_data.clear()

with st.spinner('Narik data terbaru...'):
    df = run_etl_realtime()

# Metric Section
m1, m2, m3 = st.columns(3)
m1.metric("Total Berita Terkumpul", len(df))
m2.metric("Jumlah Media Terlibat", df['sumber'].nunique())
m3.metric("Berita Terbaru", df['waktu_terbit'].max().strftime('%d %b %Y %H:%M'))

st.divider()

# Visualization Section
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📊 Top 10 Media Paling Aktif")
    media_counts = df['sumber'].value_counts().head(10).reset_index()
    media_counts.columns = ['Media', 'Jumlah Berita']
    
    fig_bar = px.bar(
        media_counts,
        x='Jumlah Berita',
        y='Media',
        orientation='h',
        color='Jumlah Berita',
        color_continuous_scale='Reds',
        text='Jumlah Berita'
    )
    fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.subheader("📈 Tren Publikasi Berita")
    df['tanggal'] = df['waktu_terbit'].dt.date
    trend_df = df.groupby('tanggal').size().reset_index(name='Jumlah Berita')
    
    fig_line = px.line(
        trend_df,
        x='tanggal',
        y='Jumlah Berita',
        markers=True,
        line_shape='spline',
        color_discrete_sequence=['#FF4B4B']
    )
    fig_line.update_layout(height=400, xaxis_title="Tanggal", yaxis_title="Jumlah Berita")
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# Interactive Table Section
st.subheader("📰 Daftar Berita Terbaru")
st.dataframe(
    df[['waktu_terbit', 'sumber', 'judul', 'link']].sort_values(by='waktu_terbit', ascending=False),
    column_config={
        "waktu_terbit": st.column_config.DatetimeColumn("Waktu Terbit", format="DD MMM YYYY, HH:mm"),
        "sumber": "Sumber Media",
        "judul": "Judul Berita",
        "link": st.column_config.LinkColumn("Akses Berita", display_text="Buka Artikel 🔗")
    },
    use_container_width=True,
    height=350,
    hide_index=True
)
