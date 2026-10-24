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

def extract_companies(text):
    if not isinstance(text, str):
        return "Tidak Terdeteksi"
    
    clean_text = re.sub(r'<[^>]+>', '', text)
    pattern = r'\b(?:PT|CV)\.?\s*([A-Za-z0-9\.\&\-]+(?:\s+[A-Za-z0-9\.\&\-]+)*)'
    matches = re.findall(pattern, clean_text)
    
    stop_words = {'terkait', 'di', 'yang', 'karena', 'atas', 'dalam', 'disegel', 'tersangka', 'resmi', 'bakar', 'diduga', 'soal', 'akibat', 'hingga', 'jadi', 'kembali', 'milik', 'sanksi', 'kasus', 'kebakaran', 'lahan', 'hutan', 'oleh', 'ke'}
    
    found = []
    for match in matches:
        words = match.split()
        clean_words = []
        for w in words:
            clean_w = re.sub(r'[^\w\.\&\-]', '', w)
            if clean_w.lower() in stop_words:
                break
            clean_words.append(clean_w)
        if clean_words:
            comp_name = " ".join(clean_words).strip(' .-&')
            if len(comp_name) > 1:
                found.append(f"PT {comp_name.upper()}")
    
    if found:
        return ", ".join(list(set(found)))
    return "Tidak Terdeteksi"

def send_telegram_alert(judul, link):
    if TELEGRAM_TOKEN == "TOKEN_BOT_KAMU" or not TELEGRAM_TOKEN:
        return
    message = f"⚠️ *PERINGATAN KARHUTLA DARURAT BARU!*\n\n📰 *Judul:* {judul}\n🔗 *Baca:* {link}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Gagal kirim notifikasi: {e}")

def run_etl_realtime():
    engine = get_db_engine()
    
    existing_links = set()
    try:
        df_old = pd.read_sql('tren_karhutla', engine)
        df_old['waktu_terbit'] = pd.to_datetime(df_old['waktu_terbit'], errors='coerce')
        existing_links = set(df_old['link'].dropna().tolist())
    except Exception:
        df_old = pd.DataFrame()

    queries = [
        "https://news.google.com/rss/search?q=karhutla&hl=id&gl=ID&ceid=ID:id",
        "https://news.google.com/rss/search?q=karhutla+PT&hl=id&gl=ID&ceid=ID:id",
        "https://news.google.com/rss/search?q=kebakaran+hutan+PT&hl=id&gl=ID&ceid=ID:id",
        "https://news.google.com/rss/search?q=segel+lahan+PT+karhutla&hl=id&gl=ID&ceid=ID:id"
    ]

    data = []
    keywords_darurat = ['siaga', 'darurat', 'evakuasi', 'parah', 'kritis', 'hebat', 'kebakaran', 'riau', 'kalimantan', 'segel', 'sanksi', 'tersangka']

    for url in queries:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            link = entry.link
            
            if link in existing_links:
                continue

            judul = entry.title
            sumber = entry.source.title if 'source' in entry else 'Unknown'
            waktu = entry.published
            summary = entry.summary if 'summary' in entry else ''
            
            teks_lengkap = f"{judul} {summary}"
            perusahaan = extract_companies(teks_lengkap)

            if any(kw in judul.lower() for kw in keywords_darurat):
                send_telegram_alert(judul, link)

            existing_links.add(link)
            data.append({
                'judul': judul,
                'sumber': sumber,
                'waktu_terbit': waktu,
                'link': link,
                'perusahaan': perusahaan
            })

    if not data and not df_old.empty:
        return df_old

    df_new = pd.DataFrame(data)
    if not df_new.empty:
        df_new['waktu_terbit'] = pd.to_datetime(df_new['waktu_terbit'], errors='coerce')

    df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=['link'], keep='first')
    df_combined.to_sql('tren_karhutla', engine, if_exists='replace', index=False)
    return df_combined

@st.cache_data(ttl=300)
def load_data():
    engine = get_db_engine()
    try:
        df = pd.read_sql('tren_karhutla', engine)
        df['waktu_terbit'] = pd.to_datetime(df['waktu_terbit'], errors='coerce')
        return df
    except Exception:
        return run_etl_realtime()

# --- TAMPILAN DASHBOARD ---
st.title("🔥 Dashboard Monitoring Karhutla Real-Time")
st.caption("Monitoring berita Karhutla, indikasi keterlibatan perusahaan, dan otomatisasi alert Telegram.")

if st.sidebar.button("🔄 Tarik Data Terbaru", use_container_width=True):
    st.cache_data.clear()
    with st.spinner('Narik berita terbaru dari Google News...'):
        df = run_etl_realtime()
else:
    df = load_data()

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
    st.info("Belum ada nama perusahaan (PT) yang terdeteksi spesifik di dalam judul/ringkasan berita database saat ini.")

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
