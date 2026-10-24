import feedparser
import pandas as pd
import sqlite3
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

# 2. TRANSFORM (Ubah ke DataFrame & Format Tanggal)
df = pd.DataFrame(data)
df['waktu_terbit'] = pd.to_datetime(df['waktu_terbit'])

# 3. LOAD (Simpan ke Database SQLite)
conn = sqlite3.connect('karhutla_trends.db')
df.to_sql('tren_karhutla', conn, if_exists='replace', index=False)
conn.close()

print(f"--- SUKSES! ---")
print(f"Berhasil menarik {len(df)} berita/update terbaru tentang Karhutla.\n")
print("--- 5 Update Terbaru Karhutla ---")
print(df[['sumber', 'judul', 'waktu_terbit']].head())
