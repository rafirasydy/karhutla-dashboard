import streamlit as st
import feedparser
import pandas as pd
import os
import requests
import re
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

def extract_companies(text):
    # Ekstraksi pola nama perusahaan (contoh: PT Sampoerna, PT. Mayawana Persada)
    pattern = r'\bPT\.?\s+[A-Z][a-zA-Z0-9\.\&\-]+(?:\s+[A-Z][a-zA-Z0-9\.\&\-]+)*'
    matches = re.findall(pattern, text)
    if matches:
        return ", ".join(list(set(matches)))
    return "Tidak Terdeteksi"

def send_telegram_alert(judul, link):
    if TELEGRAM_TOKEN == "TOKEN_BOT_KAMU" or not TELEGRAM_TOKEN:
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
        perusahaan = extract_companies(judul)

        if any(kw in judul.lower() for kw in keywords_darurat):
            send_telegram_alert(judul, link)

        data.append({
            'judul': judul,
            'sumber': sumber,
            'waktu_terbit': waktu,
            'link': link,
            'perusahaan': perusahaan
        })

    df_new = pd.DataFrame(data)
    if not df_new.empty:
        df_new['waktu_terbit'] = pd.to_datetime(df_new['waktu_terbit'], errors='coerce')

    try:
        engine = get_db_engine()
        try:
            df_old = pd.read_sql('tren_karhutla', engine)
            df_old['waktu_terbit'] = pd.to_datetime(df_old['waktu_terbit'], errors='coerce')
            if 'perusahaan' not in df_old.columns:
                df_old['perusahaan'] = df_old['judul'].apply(extract_companies)
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
st.caption("Monitoring berita Karhutla, indikasi keterlibatan perusahaan, dan otomatisasi alert Telegram.")

if st.sidebar.button("🔄 Refresh Data Sekarang", use_container_width=True):
    st.cache_data.clear()

with st.spinner('Narik data terbaru...'):
    df = run_etl_realtime()

df['waktu_terbit'] = pd.to_datetime(df['waktu_terbit'], errors='coerce')
if 'perusahaan' not in df.columns:
    df['perusahaan'] = df['judul'].apply(extract_companies)

# Hitung jumlah perusahaan terdeteksi
df_company_only = df[df['perusahaan'] != 'Tidak Terdeteksi']
total_companies_found = df_company_only['perusahaan'].nunique()

# Metric Section
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Berita Terkumpul", len(df))
m2.metric("Jumlah Media Terlibat", df['sumber'].nunique())
m3.metric("Perusahaan Terdeteksi", total_companies_found)

latest_time = df['waktu_terbit'].max()
if pd.notnull(latest_time):
    m4.metric("Berita Terbaru", latest_time.strftime('%d %b %Y %H:%M'))
else:
    m4.metric("Berita Terbaru", "-")

st.divider()

# Section Perusahaan
st.subheader("🏢 Perusahaan Terkait dalam Berita Karhutla")

if not df_company_only.empty:
    col_comp_chart, col_comp_list = st.columns([1, 1])
    
    with col_comp_chart:
        company_counts = df_company_only['perusahaan'].value_counts().reset_index()
        company_counts.columns = ['Perusahaan', 'Jumlah Berita']
        
        fig_company = px.bar(
            company_counts.head(10),
            x='Jumlah Berita',
            y='Perusahaan',
            orientation='h',
            color='Jumlah Berita',
            color_continuous_scale='Oranges',
            text='Jumlah Berita'
        )
        fig_company.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=350)
        st.plotly_chart(fig_company, use_container_width=True)
        
    with col_comp_list:
        st.write("📌 **Daftar Berita yang Menyebutkan Perusahaan:**")
        st.dataframe(
            df_company_only[['perusahaan', 'judul', 'sumber', 'link']].sort_values(by='perusahaan'),
            column_config={
                "perusahaan": "Nama Perusahaan",
                "judul": "Judul Berita",
                "sumber": "Media",
                "link": st.column_config.LinkColumn("Detail", display_text="Buka Artikel 🔗")
            },
            use_container_width=True,
            height=300,
            hide_index=True
        )
else:
    st.info("Belum ada nama perusahaan (PT) yang terdeteksi spesifik di dalam judul berita terbaru.")

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
    fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=350)
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
    fig_line.update_layout(height=350, xaxis_title="Tanggal", yaxis_title="Jumlah Berita")
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# Interactive Table Section
st.subheader("📰 Semua Daftar Berita")
st.dataframe(
    df[['waktu_terbit', 'sumber', 'perusahaan', 'judul', 'link']].sort_values(by='waktu_terbit', ascending=False),
    column_config={
        "waktu_terbit": st.column_config.DatetimeColumn("Waktu Terbit", format="DD MMM YYYY, HH:mm"),
        "sumber": "Sumber Media",
        "perusahaan": "Perusahaan Terdeteksi",
        "judul": "Judul Berita",
        "link": st.column_config.LinkColumn("Akses Berita", display_text="Buka Artikel 🔗")
    },
    use_container_width=True,
    height=350,
    hide_index=True
)
