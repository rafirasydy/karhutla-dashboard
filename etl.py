import os
import re
import feedparser
import pandas as pd
import requests
from sqlalchemy import create_engine

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5141661421")
DB_URL = os.getenv("DATABASE_URL", "sqlite:///karhutla_trends.db")

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
    if not TELEGRAM_TOKEN:
        return
    message = f"⚠️ *PERINGATAN KARHUTLA DARURAT BARU!*\n\n📰 *Judul:* {judul}\n🔗 *Baca:* {link}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Gagal kirim alert: {e}")

def run_etl():
    engine = create_engine(DB_URL)
    existing_links = set()
    try:
        df_old = pd.read_sql('tren_karhutla', engine)
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

    if not data:
        return

    df_new = pd.DataFrame(data)
    df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=['link'], keep='first')
    df_combined.to_sql('tren_karhutla', engine, if_exists='replace', index=False)

if __name__ == "__main__":
    run_etl()
