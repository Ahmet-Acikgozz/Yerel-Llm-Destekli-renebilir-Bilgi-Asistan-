# SoSmart Yerel LLM Destekli Bilgi Asistani

Kurumsal dokumanlari okuyarak ogrenebilen, yerel calisan ve internet gerektirmeyen bir yapay zeka bilgi asistani.

---

## Mimari Ozet

```
[Kullanici Sorusu]
       |
[Embedding] -- all-MiniLM-L6-v2 (sentence-transformers)
       |
[ChromaDB Arama] -- Benzer chunk'lari bul
       |
  Guven skoru >= 0.5?
      /         \
    EVET         HAYIR
     |               |
[Ollama LLM]   [PendingQuestions DB'ye kaydet]
     |               |
[Cevap]        ["Bilgi bulunamadi" + Yonetici bildirimi]
```

---

## Teknoloji Stack

| Katman         | Teknoloji                     |
|----------------|-------------------------------|
| API            | FastAPI + Uvicorn             |
| LLM            | Ollama (qwen2.5:3b)           |
| Embedding      | sentence-transformers (MiniLM)|
| Vektor DB      | ChromaDB (kalici)             |
| Iliskisel DB   | SQLite + SQLAlchemy (async)   |
| Dokuman Parse  | PyMuPDF, python-docx, markdown|

---

## Kurulum

### Onkosullar

- Python 3.11 veya uzeri
- [Ollama](https://ollama.com) kurulu olmali

### 1. Modeli Indir

```bash
ollama pull qwen2.5:3b
```

### 2. Virtual Environment Olustur

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 3. Bagimliliklari Kur

```bash
pip install -r requirements.txt
```

### 4. Ayarlari Yapilandir

`.env` dosyasini acip gerekirse duzenle:

```env
OLLAMA_MODEL=qwen2.5:3b        # Kullanilacak model
CONFIDENCE_THRESHOLD=0.5       # Guven skoru esigi (0.0 - 1.0)
```

---

## Calistirma

### 1. Ollama'yi Baslat

Ayri bir terminal/CMD penceresinde:

```bash
ollama serve
```

### 2. API Sunucusunu Baslat

```bash
# Gelistirme modu (degisiklikleri otomatik algilir)
venv\Scripts\uvicorn.exe main:app --reload --port 8000

# Normal mod
venv\Scripts\uvicorn.exe main:app --port 8000
```

### 3. Swagger UI'i Ac

Tarayicida: `http://localhost:8000/docs`

---

## API Endpoint Rehberi

### Sistem Kontrolu

```
GET /health
```
Sistem saglik durumunu ve Ollama baglantisini kontrol eder.

---

### Dokuman Yukleme

```
POST /documents/upload
```
- **Body:** multipart/form-data ile dosya
- **Desteklenen:** `.pdf`, `.docx`, `.txt`, `.md`
- **Islem:** Dosyayi okur -> chunk'lara boler -> embedding olusturur -> ChromaDB'ye kaydeder

**Ornek (curl):**
```bash
curl -X POST http://localhost:8000/documents/upload \
     -F "file=@kurumsal_kilavuz.pdf"
```

---

### Soru Sorma (RAG)

```
POST /query/
```

**Request Body:**
```json
{
  "question": "Laboratuvar numunesi nasil teslim edilir?",
  "user": "ahmet"
}
```

**Response:**
```json
{
  "question": "Laboratuvar numunesi nasil teslim edilir?",
  "answer": "Barkod okutulduktan sonra Laboratuvar Kabul Birimine teslim edilir.",
  "confidence_score": 0.72,
  "sources": ["...ilgili metin parcasi..."],
  "answered": true
}
```

- `answered: true`  → Cevap bulundu
- `answered: false` → Bilgi tabani yetersiz, soru yoneticiye iletildi

---

### Manuel Bilgi Ekleme

```
POST /knowledge/add
```

**Request Body:**
```json
{
  "title": "Izin Proseduru",
  "content": "Yillik izin talepleri en az 5 is gunu oncesinden sisteme girilmeli...",
  "source": "ik_kilavuzu"
}
```

---

### Yonetici Islemleri

| Endpoint | Aciklama |
|----------|----------|
| `GET /admin/pending-questions` | Cevaplanamayan sorulari listele |
| `POST /admin/answer/{id}` | Bekleyen soruya cevap ver |
| `GET /admin/stats` | Sistem istatistikleri |
| `GET /admin/knowledge-base` | ChromaDB kayitlarini goruntule |

**Cevap Ekleme Ornegi:**
```json
POST /admin/answer/3
{
  "answer": "Numuneler barkod okutulduktan sonra Kabul Birimine teslim edilir."
}
```
Bu islem gerceklestikten sonra ayni soru tekrar geldiginde sistem artik dogru cevap uretir.

---

## Ogrenme Dongusu

Sistemin bilgi kazanmasi icin asagidaki donguyu tekrarla:

```
1. Kullanici bilgi tabaninda olmayan bir soru sorar
        |
2. Sistem "Bilgi bulunamadi" der, soruyu PendingQuestions'a kaydeder
        |
3. Yonetici GET /admin/pending-questions ile soruyu gorur
        |
4. Yonetici POST /admin/answer/{id} ile cevap ekler
        |
5. Sistem cevabi ChromaDB'ye embedding olarak kaydeder
        |
6. Ayni soru tekrar geldiginde sistem dogru cevabi verir
```

---

## Proje Klasor Yapisi

```
sosmart-ai-assistant/
|-- main.py                    # FastAPI uygulamasi
|-- requirements.txt           # Bagimliliklar
|-- .env                       # Yapilandirma
|
|-- app/
|   |-- api/
|   |   |-- query.py           # POST /query/
|   |   |-- documents.py       # POST /documents/upload
|   |   |-- knowledge.py       # POST /knowledge/add
|   |   `-- admin.py           # /admin/* endpointleri
|   |
|   |-- core/
|   |   |-- config.py          # Ayarlar (Settings sinifi)
|   |   |-- database.py        # SQLAlchemy async engine
|   |   `-- models.py          # PendingQuestions tablosu
|   |
|   |-- services/
|   |   |-- document_parser.py # PDF/DOCX/TXT/MD okuma + chunking
|   |   |-- embedding_service.py # Metin -> vektor donusumu
|   |   |-- vector_store.py    # ChromaDB islemleri
|   |   |-- llm_service.py     # Ollama ile iletisim
|   |   `-- rag_service.py     # Tam RAG pipeline
|   |
|   `-- schemas/
|       `-- schemas.py         # Pydantic request/response modelleri
|
|-- data/
|   |-- chroma_db/             # ChromaDB veritabani dosyalari
|   |-- uploads/               # Yuklenen dokumanlar
|   `-- sosmart.db             # SQLite veritabani
|
|-- inspect_chroma.py          # ChromaDB iceri goruntuleme
|-- test_dongu.py              # Tam ogrenme dongusu testi
`-- edge_case_tests.py         # Hata durumu testleri
```

---

## Guven Skoru Hakkinda

Sistem, ChromaDB'den gelen benzerlik skorunu su sekilde kullanir:

| Skor Araligi | Anlam | Sistem Davranisi |
|:---:|---|---|
| 0.8 - 1.0 | Mukemmel eslesme | Guvenerek cevap uretir |
| 0.5 - 0.8 | Iyi eslesme | Cevap uretir |
| 0.0 - 0.5 | Yetersiz eslesme | "Bilgi bulunamadi" + Pending kaydeder |

Esigi `.env` dosyasindaki `CONFIDENCE_THRESHOLD` ile ayarlayabilirsin.

---

## Olasi Hatalar ve Cozumler

| Hata | Cozum |
|------|-------|
| `ollama: baglanti kurulamadi` | `ollama serve` komutunu calistir |
| `Model yukleniyor` uzun surerse | Ilk calistirmada ~80MB indirir, normal |
| ChromaDB bos gorunuyorsa | `POST /documents/upload` ile dokuman yukle |
| 500 Internal Server Error | Sunucu log'una bak (terminalde) |

---

*Gelistirici: Sosmart Staj Projesi — 2026*
