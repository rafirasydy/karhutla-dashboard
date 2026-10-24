# 🔥 Real-time Karhutla Monitoring & Alert Dashboard

Dashboard monitoring berita Karhutla (Kebakaran Hutan dan Lahan) secara real-time yang dilengkapi dengan pipeline ETL otomatis, penyimpanan database PostgreSQL, kontainerisasi Docker Compose, serta sistem notifikasi darurat via Telegram Bot.

## 🏗️ Arsitektur & Tech Stack
* **Language & Framework:** Python, Streamlit
* **Database:** PostgreSQL (Docker) & SQLite (Fallback Cloud)
* **Containerization:** Docker & Docker Compose
* **Notification:** Telegram Bot API
* **Deployment:** Streamlit Community Cloud

## ✨ Fitur Utama
* **Real-time Ingestion:** Penarikan otomatis berita Karhutla via RSS Feed.
* **Storage Integration:** Penyimpanan data terstruktur ke database PostgreSQL/SQLite.
* **Interactive Dashboard:** Visualisasi statistik media dan daftar berita interaktif.
* **Emergency Alerts:** Kirim notifikasi otomatis ke Telegram untuk berita berkategori darurat/siaga.

## 🚀 Cara Menjalankan (Lokal via Docker)

1. **Clone Repositori**
   ```bash
   git clone [https://github.com/rafirasydy/karhutla-dashboard.git](https://github.com/rafirasydy/karhutla-dashboard.git)
   cd karhutla-dashboard
