import os
import feedparser
import pandas as pd
import requests
from sqlalchemy import create_engine

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5141661421")
DB_URL = os.getenv("DATABASE_URL", "sqlite:///karhutla_trends.db")

def send_telegram_alert(judul, link):
    if not TELEGRAM_TOKEN:
        return
    message = f"⚠️ *PERINGATAN KARHUTLA DARURAT!*\n\n📰 *Judul:* {judul}\n🔗 *Baca:* {link}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Gagal kirim alert: {e}")

def run_etl():
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
    if df_new.empty:
        return

    df_new['waktu_terbit'] = pd.to_datetime(df_new['waktu_terbit'])
    engine = create_engine(DB_URL)

    try:
        df_old = pd.read_sql('tren_karhutla', engine)
        df_old['waktu_terbit'] = pd.to_datetime(df_old['waktu_terbit'])
        df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=['link'], keep='first')
    except Exception:
        df_combined = df_new

    df_combined.to_sql('tren_karhutla', engine, if_exists='replace', index=False)
    print(f"ETL Berhasil: Total {len(df_combined)} berita terkumpul.")

if __name__ == "__main__":
    run_etl()
