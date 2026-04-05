# AI Destekli LMS Projesi

Bu proje uçtan uca çalıştırılabilir, API entegreli bir **Öğrenme Yönetim Sistemi (LMS)** vizyon projesidir. Frontend için `Streamlit`, Backend için `FastAPI` ve veritabanı için `SQLite` kullanmaktadır. Ayrıca `Gemini` ve `Groq` API'leri üzerinden yapay zeka özellikleri sunar.

## Kurulum ve Çalıştırma

### 1. Gerekli Kütüphanelerin Yüklenmesi
```bash
pip install -r requirements.txt
```

### 2. Ortam Değişkenlerinin (API Key'ler) Eklenmesi
`.env` dosyasını düzenleyin ve kendi API key'lerinizi yerleştirin.
```bash
GEMINI_API_KEY="sizin_gemini_keyiniz"
GROQ_API_KEY="sizin_groq_keyiniz"
```

### 3. Backend'i Ayağa Kaldırma (FastAPI)
FastAPI servisi varsayılan olarak `8000` portunda çalışacaktır.
Terminalde şu komutu çalıştırın:
```bash
uvicorn ai_service:app --reload
```

### 4. Frontend Arayüzünü Ayağa Kaldırma (Streamlit)
Başka bir terminal penceresinde Streamlit uygulamasını çalıştırın (varsayılan port: `8501`):
```bash
streamlit run app.py
```

Artık `http://localhost:8501` üzerinden LMS sisteminizi deneyimleyebilirsiniz!
