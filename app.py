import streamlit as st
import pandas as pd
import os
import re
import plotly.express as px
from sqlalchemy import create_engine

st.set_page_config(page_title="Dashboard Karhutla Real-Time", layout="wide", page_icon="🔥")

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
    pattern = r'\bPT\.?\s+[A-Z][a-zA-Z0-9\.\&\-]+(?:\s+[A-Z][a-zA-Z0-9\.\&\-]+)*'
    matches = re.findall(pattern, text)
    if matches:
        return ", ".join(list(set(matches)))
    return "Tidak Terdeteksi"

@st.cache_data(ttl=180)
def load_data_from_db():
    engine = get_db_engine()
    try:
        df = pd.read_sql('tren_karhutla', engine)
        df['waktu_terbit'] = pd.to_datetime(df['waktu_terbit'], errors='coerce')
        if 'perusahaan' not in df.columns:
            df['perusahaan'] = df['judul'].apply(extract_companies)
        return df
    except Exception as e:
        st.error(f"Gagal membaca data dari database: {e}")
        return pd.DataFrame(columns=['judul', 'sumber', 'waktu_terbit', 'link', 'perusahaan'])

# --- TAMPILAN DASHBOARD ---
st.title("🔥 Dashboard Monitoring Karhutla Real-Time")
st.caption("Monitoring berita Karhutla, indikasi keterlibatan perusahaan, dan otomatisasi alert Telegram.")

if st.sidebar.button("🔄 Refresh Tampilan", use_container_width=True):
    st.cache_data.clear()

df = load_data_from_db()

if df.empty:
    st.warning("Data belum tersedia di database. Menunggu pipeline otomatis GitHub Actions berjalan...")
    st.stop()

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
    st.info("Belum ada nama perusahaan (PT) yang terdeteksi spesifik di dalam judul berita database.")

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
