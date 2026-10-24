import streamlit as st
import feedparser
import pandas as pd
import os
from sqlalchemy import create_engine

st.set_page_config(page_title="Dashboard Karhutla (Docker Compose)", layout="wide")

# Baca DB_URL dari environment variable Docker, fallback ke localhost jika dijalankan manual
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:mysecretpassword@localhost:5432/postgres")

@st.cache_data(ttl=600)
def run_etl_realtime():
    url = "https://news.google.com/rss/search?q=karhutla&hl=id&gl=ID&ceid=ID:id"
    feed = feedparser.parse(url)

    data = []
    for entry in feed.entries:
        data.append({
            'judul': entry.title,
            'sumber': entry.source.title if 'source' in entry else 'Unknown',
            'waktu_terbit': entry.published,
            'link': entry.link
        })

    df = pd.DataFrame(data)
    df['waktu_terbit'] = pd.to_datetime(df['waktu_terbit'])

    engine = create_engine(DB_URL)
    df.to_sql('tren_karhutla', engine, if_exists='replace', index=False)

    return df

st.title("🔥 Dashboard Monitoring Karhutla (Multi-Container Docker)")
st.caption("Aplikasi Streamlit dan PostgreSQL berjalan bersamaan via Docker Compose.")

if st.sidebar.button("🔄 Refresh Data Sekarang"):
    st.cache_data.clear()

with st.spinner('Narik data terbaru ke PostgreSQL...'):
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
