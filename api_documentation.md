# SoSmart Bilgi Asistanı — API Dokümantasyonu / API Documentation

> **Türkçe ve İngilizce / Turkish and English**
>
> Base URL: `http://localhost:8000`
> İnteraktif Arayüz / Interactive UI: `http://localhost:8000/docs`

---

## İçindekiler / Table of Contents

| # | Grup / Group | Endpoint |
|---|---|---|
| 1 | Genel / General | `GET /health` |
| 2 | Kimlik Doğrulama / Auth | `POST /auth/login` |
| 3 | Kimlik Doğrulama / Auth | `GET /auth/me` |
| 4 | Sorgulama / Query | `POST /query/` |
| 5 | Sorgulama / Query | `GET /query/sources` |
| 6 | Doküman Yönetimi / Documents | `POST /documents/upload` |
| 7 | Doküman Yönetimi / Documents | `GET /documents/stats` |
| 8 | Manuel Bilgi / Knowledge | `POST /knowledge/add` |
| 9 | Yönetici / Admin | `GET /admin/pending-questions` |
| 10 | Yönetici / Admin | `POST /admin/answer/{question_id}` |
| 11 | Yönetici / Admin | `GET /admin/stats` |
| 12 | Yönetici / Admin | `GET /admin/knowledge-base` |
| 13 | Yönetici / Admin | `DELETE /admin/reset-all` |

---

## Kimlik Doğrulama / Authentication

Korumalı endpoint'ler JWT Bearer Token gerektirir.
Protected endpoints require a JWT Bearer Token.

```
Authorization: Bearer <token>
```

Token almak için `POST /auth/login` kullanın.
Use `POST /auth/login` to obtain a token.

**Test Kullanıcıları / Test Users:**
| Kullanıcı / User | Şifre / Password | Rol / Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `user` | `user123` | User |

---

## 1. Sistem Sağlık Kontrolü / System Health Check

### `GET /health`

**TR:** Sistemin ve Ollama bağlantısının çalışma durumunu döndürür. Token gerektirmez.

**EN:** Returns system and Ollama connection status. No token required.

**Yetki / Auth:** ❌ Gerekmez / Not required

#### Yanıt / Response `200 OK`
```json
{
  "status": "✅ çalışıyor",
  "app_name": "SoSmart Bilgi Asistanı",
  "version": "2.0.0",
  "ollama": "✅ bağlı (qwen2.5:3b)",
  "docs": "http://localhost:8000/docs"
}
```

| Alan / Field | Tür / Type | Açıklama / Description |
|---|---|---|
| `status` | `string` | TR: Uygulama durumu / EN: App status |
| `app_name` | `string` | TR: Uygulama adı / EN: App name |
| `version` | `string` | TR: Sürüm / EN: Version |
| `ollama` | `string` | TR: Ollama LLM bağlantı durumu / EN: Ollama connection status |
| `docs` | `string` | TR: Swagger UI adresi / EN: Swagger UI URL |

---

## 2. Kimlik Doğrulama / Authentication

### `POST /auth/login`

**TR:** Kullanıcı adı ve şifre ile giriş yapın, JWT erişim tokeni alın.

**EN:** Login with username and password, receive a JWT access token.

**Yetki / Auth:** ❌ Gerekmez / Not required

**Content-Type:** `application/x-www-form-urlencoded`

#### İstek / Request (Form Data)
| Alan / Field | Tür / Type | Zorunlu / Required | Açıklama / Description |
|---|---|---|---|
| `username` | `string` | ✅ Evet/Yes | TR: Kullanıcı adı / EN: Username |
| `password` | `string` | ✅ Evet/Yes | TR: Şifre / EN: Password |

#### Örnek İstek / Example Request
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

#### Yanıt / Response `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "admin",
  "role": "admin"
}
```

| Alan / Field | Tür / Type | Açıklama / Description |
|---|---|---|
| `access_token` | `string` | TR: JWT token — diğer isteklerde kullanın / EN: JWT token — use in subsequent requests |
| `token_type` | `string` | TR: Her zaman "bearer" / EN: Always "bearer" |
| `username` | `string` | TR: Giriş yapan kullanıcı adı / EN: Logged-in username |
| `role` | `string` | TR: Kullanıcı rolü (`admin` veya `user`) / EN: User role (`admin` or `user`) |

#### Hata Yanıtları / Error Responses
| Kod / Code | Açıklama / Description |
|---|---|
| `401` | TR: Hatalı kullanıcı adı veya şifre / EN: Invalid username or password |

---

### `GET /auth/me`

**TR:** Geçerli JWT tokenından mevcut kullanıcı bilgilerini döndürür.

**EN:** Returns current user information from the valid JWT token.

**Yetki / Auth:** ✅ Bearer Token (herhangi bir rol / any role)

#### Örnek İstek / Example Request
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer <token>"
```

#### Yanıt / Response `200 OK`
```json
{
  "username": "admin",
  "role": "admin",
  "yetki": "Admin paneline erisim var"
}
```

---

## 3. Sorgulama (RAG) / Query (RAG)

### `POST /query/`

**TR:** Kullanıcının sorusunu alır, RAG pipeline'ından geçirir ve cevap döndürür. Sistem sırasıyla şunları yapar:
1. Soruyu ChromaDB'de arar (10 sonuç)
2. Cross-Encoder Re-ranker ile en alakalı 4 chunk'ı seçer
3. Seçilen chunk'ları Ollama LLM'e bağlam olarak gönderir
4. LLM cevap üretir; bulamazsa soru yönetici incelemesine alınır

**EN:** Accepts a user question, runs it through the RAG pipeline, and returns an answer. The system:
1. Searches ChromaDB (10 results)
2. Selects top 4 chunks using Cross-Encoder Re-ranker
3. Sends selected chunks as context to Ollama LLM
4. LLM generates an answer; if not found, the question is queued for admin review

**Yetki / Auth:** ❌ Gerekmez / Not required

**Content-Type:** `application/json`

#### İstek Gövdesi / Request Body
```json
{
  "question": "Laboratuvar numunesi nasıl teslim edilir?",
  "user": "ahmet",
  "source_filter": "lab_rehberi.pdf"
}
```

| Alan / Field | Tür / Type | Zorunlu / Required | Varsayılan / Default | Açıklama / Description |
|---|---|---|---|---|
| `question` | `string` | ✅ Evet/Yes | — | TR: Kullanıcının sorusu (min: 3, max: 1000 karakter) / EN: User's question (min: 3, max: 1000 chars) |
| `user` | `string` | ❌ Hayır/No | `"anonymous"` | TR: Kullanıcı adı (soruyu kimin sorduğu) / EN: Username (who asked the question) |
| `source_filter` | `string` | ❌ Hayır/No | `null` | TR: Sadece bu dokümanı tara / EN: Search only in this document |

#### Örnek İstek / Example Request
```bash
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"question": "Şirket tatil politikası nedir?", "user": "ahmet"}'
```

#### Yanıt — Cevap Bulundu / Response — Answer Found `200 OK`
```json
{
  "question": "Şirket tatil politikası nedir?",
  "answer": "Çalışanlar yılda 14 gün ücretli izin hakkına sahiptir...",
  "confidence_score": 0.89,
  "rerank_score": 0.97,
  "sources": [
    "[ik_rehberi.pdf] Yıllık izin politikası: Çalışanlar yılda 14 gün..."
  ],
  "answered": true
}
```

#### Yanıt — Cevap Bulunamadı / Response — Answer Not Found `200 OK`
```json
{
  "question": "Mars'ın atmosferi nedir?",
  "answer": "Bu konu hakkında bilgi tabanında yeterli bilgi bulunamadı. Sorunuz yönetici incelemesine alındı.",
  "confidence_score": 0.12,
  "rerank_score": 0.0,
  "sources": [],
  "answered": false
}
```

| Alan / Field | Tür / Type | Açıklama / Description |
|---|---|---|
| `question` | `string` | TR: Sorulan soru / EN: The asked question |
| `answer` | `string` | TR: Üretilen cevap / EN: Generated answer |
| `confidence_score` | `float` | TR: Embedding benzerlik skoru (0-1) / EN: Embedding similarity score (0-1) |
| `rerank_score` | `float` | TR: Cross-Encoder re-rank skoru (0-1) / EN: Cross-Encoder re-rank score (0-1) |
| `sources` | `string[]` | TR: Cevabın dayandığı kaynak metinler / EN: Source texts the answer is based on |
| `answered` | `boolean` | TR: `true` = cevap bulundu, `false` = bilgi tabanında yok / EN: `true` = answered, `false` = not in knowledge base |

---

### `GET /query/sources`

**TR:** ChromaDB'de kayıtlı tüm doküman isimlerini döndürür. Gradio arayüzündeki filtre menüsü bu endpoint'i kullanır.

**EN:** Returns all document names registered in ChromaDB. The Gradio UI filter menu uses this endpoint.

**Yetki / Auth:** ❌ Gerekmez / Not required

#### Yanıt / Response `200 OK`
```json
["Tümü", "ik_rehberi.pdf", "lab_prosedur.docx", "admin_cevap"]
```

---

## 4. Doküman Yönetimi / Document Management

### `POST /documents/upload`

**TR:** Kurumsal doküman yükler, metni chunk'lara böler ve ChromaDB'ye vektör olarak kaydeder.

**EN:** Uploads a corporate document, splits the text into chunks, and stores them as vectors in ChromaDB.

**Yetki / Auth:** ✅ Bearer Token — **Admin rolü gerekli / Admin role required**

**Content-Type:** `multipart/form-data`

**Desteklenen Formatlar / Supported Formats:** `.pdf`, `.docx`, `.txt`, `.md`, `.markdown`

#### İstek / Request (Form Data)
| Alan / Field | Tür / Type | Zorunlu / Required | Varsayılan / Default | Açıklama / Description |
|---|---|---|---|---|
| `file` | `file` | ✅ Evet/Yes | — | TR: Yüklenecek dosya / EN: File to upload |
| `category` | `string` | ❌ Hayır/No | `"genel"` | TR: Doküman kategorisi / EN: Document category |

**Kategori Seçenekleri / Category Options:** `genel`, `ik`, `finans`, `teknik`, `hukuk`

#### Örnek İstek / Example Request
```bash
curl -X POST "http://localhost:8000/documents/upload?category=ik" \
  -H "Authorization: Bearer <token>" \
  -F "file=@ik_rehberi.pdf"
```

#### Yanıt / Response `200 OK`
```json
{
  "filename": "ik_rehberi.pdf",
  "chunks_created": 42,
  "message": "'ik_rehberi.pdf' basariyla yuklendi ve 42 chunk olusturuldu."
}
```

#### Hata Yanıtları / Error Responses
| Kod / Code | Açıklama / Description |
|---|---|
| `400` | TR: Desteklenmeyen dosya formatı / EN: Unsupported file format |
| `401` | TR: Token yok veya geçersiz / EN: Missing or invalid token |
| `403` | TR: Admin yetkisi gerekli / EN: Admin role required |
| `422` | TR: Doküman işlenirken hata oluştu / EN: Error while processing document |

---

### `GET /documents/stats`

**TR:** ChromaDB'deki toplam chunk sayısını döndürür.

**EN:** Returns the total number of chunks in ChromaDB.

**Yetki / Auth:** ❌ Gerekmez / Not required

#### Yanıt / Response `200 OK`
```json
{
  "total_chunks": 156,
  "message": "Bilgi tabaninda toplam 156 chunk mevcut."
}
```

---

## 5. Manuel Bilgi Girişi / Manual Knowledge Entry

### `POST /knowledge/add`

**TR:** Doküman yüklemeden, metin olarak doğrudan bilgi tabanına bilgi ekler.

**EN:** Adds knowledge directly to the knowledge base as text without uploading a document.

**Yetki / Auth:** ✅ Bearer Token — **Admin rolü gerekli / Admin role required**

**Content-Type:** `application/json`

#### İstek Gövdesi / Request Body
```json
{
  "title": "Ofis Çalışma Saatleri",
  "content": "Ofisimiz hafta içi 09:00-18:00 saatleri arasında açıktır. Cumartesi 10:00-14:00 arasında açıktır.",
  "source": "manuel_giris"
}
```

| Alan / Field | Tür / Type | Zorunlu / Required | Varsayılan / Default | Açıklama / Description |
|---|---|---|---|---|
| `title` | `string` | ✅ Evet/Yes | — | TR: Bilgi başlığı (min: 2, max: 200 karakter) / EN: Knowledge title (min: 2, max: 200 chars) |
| `content` | `string` | ✅ Evet/Yes | — | TR: Eklenecek bilgi içeriği (min: 10 karakter) / EN: Knowledge content (min: 10 chars) |
| `source` | `string` | ❌ Hayır/No | `"manuel_giris"` | TR: Kaynak etiketi / EN: Source label |

#### Yanıt / Response `200 OK`
```json
{
  "title": "Ofis Çalışma Saatleri",
  "chunks_created": 1,
  "message": "Bilgi basariyla eklendi."
}
```

---

## 6. Yönetici İşlemleri / Admin Operations

### `GET /admin/pending-questions`

**TR:** Bilgi tabanında cevaplanamayan ve yönetici incelemesini bekleyen soruları listeler. Varsayılan olarak sadece bekleyen (`Bekliyor`) sorular gösterilir.

**EN:** Lists questions that could not be answered and are waiting for admin review. By default, only pending questions are shown.

**Yetki / Auth:** ✅ Bearer Token — **Admin rolü gerekli / Admin role required**

#### Sorgu Parametresi / Query Parameter
| Parametre / Param | Tür / Type | Zorunlu / Required | Açıklama / Description |
|---|---|---|---|
| `status` | `string` | ❌ Hayır/No | TR: `"Cevaplandi"` yazılırsa sadece cevaplanmış sorular gelir / EN: Pass `"Cevaplandi"` to get answered questions only |

#### Örnek İstek / Example Request
```bash
curl -X GET "http://localhost:8000/admin/pending-questions" \
  -H "Authorization: Bearer <token>"
```

#### Yanıt / Response `200 OK`
```json
[
  {
    "id": 5,
    "question": "Yıllık izin kaç gündür?",
    "asked_by": "gradio_user",
    "asked_at": "2026-08-11T15:30:00Z",
    "status": "Bekliyor",
    "admin_answer": null,
    "answered_at": null
  }
]
```

| Alan / Field | Tür / Type | Açıklama / Description |
|---|---|---|
| `id` | `integer` | TR: Soru ID'si (cevap verirken kullanılır) / EN: Question ID (used when answering) |
| `question` | `string` | TR: Kullanıcının sorduğu soru / EN: The question asked by the user |
| `asked_by` | `string` | TR: Soruyu soran kullanıcı / EN: User who asked |
| `asked_at` | `datetime` | TR: Soru zamanı (ISO 8601) / EN: Time asked (ISO 8601) |
| `status` | `string` | TR: `"Bekliyor"` veya `"Cevaplandı"` / EN: `"Bekliyor"` (pending) or `"Cevaplandı"` (answered) |
| `admin_answer` | `string\|null` | TR: Yönetici cevabı / EN: Admin's answer |
| `answered_at` | `datetime\|null` | TR: Cevap zamanı / EN: Time answered |

---

### `POST /admin/answer/{question_id}`

**TR:** Bekleyen bir soruya cevap verir. Cevap hem SQLite'ta `Cevaplandı` olarak işaretlenir hem de ChromaDB'ye yeni bilgi olarak eklenir. Böylece sistem bu soruyu öğrenmiş olur.

**EN:** Answers a pending question. The answer is both marked as `Answered` in SQLite and added as new knowledge to ChromaDB. This way the system learns the answer.

**Yetki / Auth:** ✅ Bearer Token — **Admin rolü gerekli / Admin role required**

**Content-Type:** `application/json`

#### URL Parametresi / URL Parameter
| Parametre / Param | Tür / Type | Açıklama / Description |
|---|---|---|
| `question_id` | `integer` | TR: Cevaplanacak sorunun ID'si / EN: ID of the question to answer |

#### İstek Gövdesi / Request Body
```json
{
  "answer": "Yıllık izin süresi 14 iş günüdür. Kullanılmayan izinler ertesi yıla devredilmez."
}
```

| Alan / Field | Tür / Type | Zorunlu / Required | Açıklama / Description |
|---|---|---|---|
| `answer` | `string` | ✅ Evet/Yes | TR: Soruya verilecek cevap (min: 5 karakter) / EN: Answer to the question (min: 5 chars) |

#### Örnek İstek / Example Request
```bash
curl -X POST "http://localhost:8000/admin/answer/5" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"answer": "Yıllık izin süresi 14 iş günüdür."}'
```

#### Yanıt / Response `200 OK`
```json
{
  "question_id": 5,
  "question": "Yıllık izin kaç gündür?",
  "answer": "Yıllık izin süresi 14 iş günüdür.",
  "chunks_created": 1,
  "message": "Cevap bilgi tabanina eklendi ve soru listeden kaldirildi."
}
```

#### Hata Yanıtları / Error Responses
| Kod / Code | Açıklama / Description |
|---|---|
| `404` | TR: Belirtilen ID'li soru bulunamadı / EN: Question with given ID not found |
| `400` | TR: Bu soru zaten cevaplandı / EN: This question is already answered |

---

### `GET /admin/stats`

**TR:** Sistemin genel istatistiklerini döndürür.

**EN:** Returns general system statistics.

**Yetki / Auth:** ❌ Gerekmez / Not required

#### Yanıt / Response `200 OK`
```json
{
  "bilgi_tabani": {
    "toplam_chunk": 156
  },
  "sorular": {
    "toplam": 15,
    "bekleyen": 3,
    "cevaplanan": 12
  },
  "ozet": "156 bilgi parcasi mevcut. 3 soru bekliyor."
}
```

---

### `GET /admin/knowledge-base`

**TR:** ChromaDB'deki kayıtlı bilgileri görüntüler. Debug ve doğrulama amaçlıdır.

**EN:** Displays registered knowledge entries in ChromaDB. For debugging and verification purposes.

**Yetki / Auth:** ❌ Gerekmez / Not required

#### Sorgu Parametresi / Query Parameter
| Parametre / Param | Tür / Type | Varsayılan / Default | Açıklama / Description |
|---|---|---|---|
| `limit` | `integer` | `50` | TR: Gösterilecek maksimum kayıt sayısı / EN: Maximum records to show |

#### Yanıt / Response `200 OK`
```json
{
  "toplam_kayit": 156,
  "gosterilen": 50,
  "kayitlar": [
    {
      "id": "a1b2c3d4...",
      "source": "ik_rehberi.pdf",
      "chunk_index": 0,
      "preview": "Çalışanlara sağlanan haklar kapsamında yıllık 14 gün ücretli izin...",
      "karakter_sayisi": 342
    }
  ]
}
```

---

### `DELETE /admin/reset-all`

**TR:** ⚠️ **DİKKAT! Geri alınamaz işlem.** ChromaDB'deki tüm verileri ve SQLite'taki tüm bekleyen soruları kalıcı olarak siler. Sadece test ortamlarında kullanın.

**EN:** ⚠️ **WARNING! Irreversible operation.** Permanently deletes all data in ChromaDB and all pending questions in SQLite. Use only in test environments.

**Yetki / Auth:** ❌ Gerekmez / Not required *(Dikkat: Prod ortamında admin koruması eklemeniz önerilir / Note: Recommend adding admin protection in production)*

#### Yanıt / Response `200 OK`
```json
{
  "message": "Sistem tamamen sifirlandi! ChromaDB ve bekleyen sorular silindi."
}
```

---

## Hata Kodları Referansı / Error Code Reference

| HTTP Kodu / Code | Anlam / Meaning | Olası Neden / Possible Cause |
|---|---|---|
| `400` | Bad Request | TR: Geçersiz parametre veya istek / EN: Invalid parameter or request |
| `401` | Unauthorized | TR: Token eksik veya süresi dolmuş / EN: Token missing or expired |
| `403` | Forbidden | TR: Yetersiz yetki (admin gerekli) / EN: Insufficient permissions (admin required) |
| `404` | Not Found | TR: Kaynak bulunamadı / EN: Resource not found |
| `422` | Unprocessable Entity | TR: İstek gövdesi doğrulama hatası / EN: Request body validation error |
| `500` | Internal Server Error | TR: Sunucu hatası / EN: Server error |

---

## Hızlı Başlangıç / Quick Start

### TR: Tam akış örneği (5 adım)

```bash
# 1. Sistem sağlık kontrolü
curl http://localhost:8000/health

# 2. Admin girişi, token al
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. PDF yükle
curl -X POST "http://localhost:8000/documents/upload?category=ik" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@ik_rehberi.pdf"

# 4. Soru sor
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Yıllık izin kaç gündür?", "user": "ahmet"}'

# 5. Cevaplanamayan soruları gör ve cevapla
curl http://localhost:8000/admin/pending-questions \
  -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8000/admin/answer/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"answer": "Yıllık izin 14 iş günüdür."}'
```

### EN: Full workflow example (5 steps)

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Admin login, get token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Upload PDF
curl -X POST "http://localhost:8000/documents/upload?category=hr" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@hr_guide.pdf"

# 4. Ask a question
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "How many days of annual leave do employees get?", "user": "john"}'

# 5. View and answer pending questions
curl http://localhost:8000/admin/pending-questions \
  -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8000/admin/answer/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"answer": "Employees receive 14 working days of annual leave."}'
```

---

*Bu doküman SoSmart staj projesi kapsamında hazırlanmıştır. / This document was prepared as part of the SoSmart internship project.*

*Son güncelleme / Last updated: Ağustos 2026 / August 2026*
