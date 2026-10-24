import streamlit as st
import feedparser
import pandas as pd
import sqlite3

st.set_page_config(page_title="Dashboard Karhutla Real-Time", layout="wide")

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

    conn = sqlite3.connect('karhutla_trends.db')
    df.to_sql('tren_karhutla', conn, if_exists='replace', index=False)
    conn.close()

    return df

st.title("🔥 Dashboard Monitoring Karhutla (Real-Time)")
st.caption("Data diperbarui otomatis langsung dari sumber berita terkini.")

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
