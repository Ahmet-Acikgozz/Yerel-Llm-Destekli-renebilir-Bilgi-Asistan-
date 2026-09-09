# SoSmart Bilgi Asistanı - Video Sunum Senaryosu

*Bu belge, 30-60 dakikalık sunum videonu çekerken hangi ekranda ne söylemen gerektiğini adım adım planlar.*

---

## 1. BÖLÜM: Proje Tanıtımı (Yüzün veya Sadece Ana Ekran Açıkken)
**(Süre: ~3 Dakika)**

**Söyleyeceklerin:**
"Merhaba, ben Ahmet Açıkgöz. SoSmart staj programı kapsamında geliştirdiğim 'Yerel LLM Destekli Öğrenebilir Bilgi Asistanı' projesinin  sunumuna hoş geldiniz.
Bu projenin temel amacı; şirketlerin kendi iç dokümanlarını (örneğin İK kılavuzları, kurumsal prosedürler) yapay zekaya okutarak, çalışanların sorularına anında ve sadece bu dokümanlara dayanarak cevap verebilen bir asistan yaratmaktır. 
Sistemin en büyük özelliği 'Yerel (Lokal)' çalışmasıdır. Yani veriler ChatGPT gibi dış servislere gitmez, şirket içinde güvende kalır. Sistem; kullanıcıların sohbet edebildiği bir Frontend (Gradio), işlemlerin yapıldığı bir Backend (FastAPI) ve verilerin tutulduğu veritabanlarından (ChromaDB ve SQLite) oluşmaktadır."

---

## 2. BÖLÜM: Canlı Demo Gösterimi (Gradio Arayüzü Açıkken)
**(Süre: ~5-10 Dakika)**

**Ekranda Yapılacaklar:**
1. Tarayıcıda `http://localhost:7860` adresini aç.
2. "Sohbet" sekmesinde asistana bir soru sor (Örn: "Şirket kuralları nelerdir?"). Asistanın cevap verdiğini ve altında "Kaynak" gösterdiğini izleyicilere sun.
3. Yönetici Paneli sekmesine geç. `admin` / `admin123` ile giriş yap.
4. "Doküman Yükleme" bölümünden bir PDF dosyası yükle.
5. "Bekleyen Sorular" sekmesini aç. Bilgi tabanında olmayan bir sorunun buraya nasıl düştüğünü göster ve panele bir cevap girerek soruyu veritabanına kaydet.

**Söyleyeceklerin:**
"Şimdi sistemin son kullanıcıya nasıl yansıdığına bakalım. Arayüzümüz için Gradio kullandık. Kullanıcı buradan sorusunu soruyor ve sistem doğrudan PDF içindeki ilgili metni bularak cevap üretiyor. Alt kısımda 'Benzerlik Skoru' ve 'Re-rank Skoru' görüyoruz.
Eğer sistem cevabı bilmiyorsa halüsinasyon görüp yalan uydurmaz. Soruyu 'Yönetici Paneline' atar. Şimdi yönetici olarak giriş yapıyorum. Burada JWT Token ile güvenli bir giriş sağlıyoruz. Gördüğünüz gibi sisteme yeni belgeler yükleyebiliyor veya cevapsız kalan soruları sistemin öğrenmesi için manuel olarak cevaplayabiliyoruz."

---

## 3. BÖLÜM: Proje Dosya Yapısının İncelenmesi (VS Code Açıkken)
**(Süre: ~5 Dakika)**

**Ekranda Yapılacaklar:**
VS Code sol paneli açık olsun. Klasörleri teker teker açarak göster.

**Söyleyeceklerin:**
"Projeyi sürdürülebilir olması adına temiz bir mimari ile kurduk:
- **`app/api/` (Controller Katmanı):** Dışarıdan gelen HTTP isteklerini karşılar. (Burada `query.py`, `admin.py`, `documents.py` dosyalarını göster).
- **`app/services/` (Business Katmanı):** İş kurallarının olduğu yerdir. Yapay zeka entegrasyonu, PDF'lerin parçalanması (chunking) burada yapılır.
- **`app/core/` (Core Katmanı):** Veritabanı bağlantısı, JWT şifreleme ve ayarlar bulunur.
- **`frontend/`:** Gradio ile yazdığımız web arayüzümüz.
- **`data/`:** SQLite ve ChromaDB'nin verilerini tuttuğu yerel klasör."

---

## 4. BÖLÜM: Backend ve Kodların Anlatılması (Kodlar Açıkken)
**(Süre: ~25-30 Dakika)**

> 💡 **İPUCU:** Her dosyayı VS Code'da açtıktan sonra kodu kaydır, satırları göster. Ekranı büyütmek için `CTRL + SHIFT + P` → "Zen Mode" yazabilirsin.

---

### 4.1 — `main.py` → Uygulamanın Giriş Kapısı
**(~2 dakika)**

**Ekranda Yapılacak:** `main.py` dosyasını aç, en üstten aşağı doğru kaydır.

**Söyleyeceklerin:**
"Sistemin her şeyi buradan başlıyor. `main.py` dosyası FastAPI uygulamamızın ana giriş noktasıdır. Burada önce FastAPI uygulaması oluşturuluyor. Ardından `@app.on_event('startup')` ile uygulama başlarken veritabanı tabloları oluşturuluyor ve embedding modeli hafızaya yükleniyor — bunu startup event olarak tanımladık ki sunucu her açıldığında hazır olsun.

En önemli kısım şu: Her API grubunu ayrı bir dosyada yazdık ve burada `app.include_router(...)` ile birleştirdik. Bu pattern'e 'Router' denir ve kodun bakımını kolaylaştırır. Örneğin `/auth/login` isteği geldiğinde FastAPI bunu `auth.router`'a yönlendirir. `/query/` isteği geldiğinde `query.router`'a yönlendirir."

---

### 4.2 — `app/core/config.py` → Yapılandırma Merkezi
**(~2 dakika)**

**Ekranda Yapılacak:** `app/core/config.py` dosyasını aç.

**Söyleyeceklerin:**
"Bu dosya tüm yapılandırma değerlerini tek bir noktada toplar. `Settings` sınıfı `pydantic-settings` kütüphanesi ile yazılmış. Özelliği şu: uygulama başladığında `.env` dosyasını otomatik olarak okuyup bu class'ın içine dolduruyor. Örneğin `OLLAMA_MODEL`, `JWT_SECRET_KEY`, `CONFIDENCE_THRESHOLD` gibi değişkenler buradan okunuyor.

Bu yaklaşımın avantajı; siz kodu değiştirmeden sadece `.env` dosyasını düzenleyerek sistemin davranışını değiştirebilirsiniz. Örneğin modeli `qwen2.5:3b`'den farklı bir Ollama modeline geçmek istesek sadece `.env` dosyasındaki bir satırı değiştirmek yeterli."

---

### 4.3 — `app/schemas/schemas.py` → Veri Kontrakları (Pydantic)
**(~2 dakika)**

**Ekranda Yapılacak:** `app/schemas/schemas.py` dosyasını aç.

**Söyleyeceklerin:**
"Bu dosya API'mize gelen ve API'den çıkan verilerin şablonlarını tanımlar. Buna 'şema' veya 'kontrakt' diyoruz. `QueryRequest` class'ına bakın: kullanıcının bize göndereceği JSON'ın mutlaka `question` alanı içermesi gerekiyor; `user` ve `source_filter` alanları ise isteğe bağlı.

`QueryResponse` ise API'den kullanıcıya dönen cevabın şablonu: `question`, `answer`, `confidence_score`, `rerank_score`, `sources` ve `answered` alanlarından oluşuyor. Pydantic bu şemalar sayesinde gelen veriyi otomatik doğrular; yanlış formatta veri gelirse 422 Unprocessable Entity hatası döner ve biz bunu handle etmek zorunda kalmayız."

---

### 4.4 — `app/api/query.py` → Soru-Cevap Controller'ı
**(~3 dakika)**

**Ekranda Yapılacak:** `app/api/query.py` dosyasını aç.

**Söyleyeceklerin:**
"Bu dosya `POST /query/` endpoint'ini barındırıyor. Kullanıcı sohbet ekranından bir soru gönderdiğinde bu fonksiyon tetikleniyor. Dikkat ederseniz içinde hiç iş mantığı yok — sadece gelen isteği `rag_service.answer(...)` metoduna iletip dönen sonucu kullanıcıya gönderiyor. Bu, Controller katmanının görevi; iş yapmaz, yönlendirir.

Ayrıca `GET /query/sources` endpoint'imiz de burada. Bu endpoint Gradio'daki 'Doküman Filtresi' açılır menüsünü dolduruyor. ChromaDB'de kayıtlı olan tüm doküman isimlerini listeliyor."

---

### 4.5 — `app/api/auth.py` → Kimlik Doğrulama Controller'ı
**(~3 dakika)**

**Ekranda Yapılacak:** `app/api/auth.py` dosyasını aç.

**Söyleyeceklerin:**
"`POST /auth/login` endpoint'imiz burada. Kullanıcı Gradio panelinde kullanıcı adı ve şifresiyle giriş yapmak istediğinde bu endpoint tetikleniyor. OAuth2 standardını kullandığımız için form verisi (`username`, `password`) alıyor.

`authenticate_user` fonksiyonunu çağırarak kullanıcıyı doğruluyor. Doğrulama başarılıysa `create_access_token` ile bir JWT token üretiyor ve kullanıcıya gönderiyor. Bu token, her sonraki istekte `Authorization: Bearer <token>` header'ı ile gönderilmek zorunda. Yoksa korumalı endpoint'lere erişim sağlanamaz.

`GET /auth/me` endpoint'i ise token sahibinin kim olduğunu döndürüyor — test amaçlı bir endpoint."

---

### 4.6 — `app/core/auth.py` → JWT ve Güvenlik Motoru
**(~3 dakika)**

**Ekranda Yapılacak:** `app/core/auth.py` dosyasını aç.

**Söyleyeceklerin:**
"Bu dosya güvenlik sistemimizin kalbidir. `_hash_password` fonksiyonu, `.env`'deki düz metin şifreleri `bcrypt` algoritmasıyla şifreler. Bcrypt'in özelliği şu: aynı şifreyi iki kez hash'leseniz bile farklı sonuçlar üretir çünkü içine 'salt' ekler. Bu sayede veritabanı ele geçirilse bile şifreler kırılamaz.

`create_access_token` fonksiyonu JWT token üretiyor. Token içine kullanıcı adını (`sub`) ve rolünü (`role`) gömdük. Token imzalanıyor, değiştirilemiyor. Süresi dolduğunda geçersiz oluyor.

En kritik kısım `require_admin` fonksiyonu — bu bir FastAPI Dependency'si. Admin endpoint'lerine `Depends(require_admin)` yazarak bu fonksiyonu bağladık. Eğer gelen token'ın rolü `admin` değilse otomatik olarak `403 Forbidden` hatası dönüyor. Kod içinde tek tek kontrol yazmak zorunda kalmıyoruz."

---

### 4.7 — `app/services/rag_service.py` → RAG Pipeline Orkestratörü ⭐
**(~5 dakika — En Önemli Dosya)**

**Ekranda Yapılacak:** `app/services/rag_service.py` dosyasını aç. Adımları tek tek göster.

**Söyleyeceklerin:**
"Bu, projenin en kritik dosyası. Tüm yapay zeka akışının yönetildiği Business katmanıdır. Adım adım göstereyim:

**Adım 1 — Geniş Arama:** `vector_store.search(n_results=10)` ile ChromaDB'de geniş bir ağ atıyoruz. 10 sonuç alıyoruz çünkü vektör benzerliği tek başına her zaman en alakalı içeriği bulamayabilir.

**Adım 2 — Re-ranking:** `reranker_service.rerank(top_k=4)` ile bu 10 sonucu Cross-Encoder modeline veriyoruz. Bu model 'Bu soru ile bu metin gerçekten alakalı mı?' diye sorarak 0-1 arası puan veriyor ve en iyi 4'ü seçiyor.

**Adım 3 — Eşik Kontrolü (Threshold):** En iyi re-rank skoru `0.30`'un altındaysa LLM'e hiç gitmiyoruz. Direkt 'Cevap bulunamadı' diyoruz. Bu sayede yapay zeka uydurma cevap üretemiyor.

**Adım 4 — LLM'e Gönder:** Kalan 4 chunk'ı `llm_service.generate()` ile Ollama'ya gönderiyoruz.

**Adım 5 — Kaydet:** Eğer LLM de cevap bulamazsa `_save_pending_question` ile SQLite'a kaydediyoruz. Böylece yönetici görebilir ve cevaplayabilir."

---

### 4.8 — `app/services/reranker_service.py` → Cross-Encoder Re-ranker
**(~2 dakika)**

**Ekranda Yapılacak:** `app/services/reranker_service.py` dosyasını aç.

**Söyleyeceklerin:**
"Re-ranker servisimiz `cross-encoder/ms-marco-MiniLM-L-6-v2` modelini kullanıyor. Bu model `sentence-transformers` kütüphanesinden geliyor. Normal embedding modellerinden farklı olarak bu model iki metni aynı anda görüyor — soru ve aday metni yan yana koyuyor ve birebir alaka puanı üretiyor. Bu çok daha doğru bir benzerlik ölçüm yöntemi.

`rerank` metodu adayları puanlıyor, yüksekten düşüğe sıralıyor ve sadece ilk `top_k` tanesini döndürüyor."

---

### 4.9 — `app/services/document_parser.py` → Akıllı Doküman Parçalayıcı
**(~3 dakika)**

**Ekranda Yapılacak:** `app/services/document_parser.py` dosyasını aç, `_split_into_chunks` ve `_docx_table_to_markdown` metodlarını göster.

**Söyleyeceklerin:**
"Bir doküman yüklendiğinde önce `parse` metodu dosya türüne bakıyor: PDF için PyMuPDF, DOCX için python-docx, metin dosyaları için doğrudan okuma kullanıyor.

Okunan metin `_split_into_chunks` metoduna giriyor. Burada `RecursiveCharacterTextSplitter` kullandık. Bu splitter'ın sıradanlıktan farkı şu: önce çift satır sonu (`\n\n`) olan yerlerden bölmeye çalışıyor yani paragraf sınırlarına saygı gösteriyor. Paragraf yeterince küçükse bırakıyor, büyükse tek satır sonu (`\n`) olan yerden kesiyor. Hâlâ büyükse noktalı yerden kesiyor ve son çare olarak karakter sayısından kesiyor. Bu sayede anlam bütünlüğü mümkün olduğunca korunuyor.

DOCX dosyalarındaki tablolar için özel bir metot yazdık: `_docx_table_to_markdown`. Bu metot tablodaki satır ve hücreleri gezerek standart Markdown tablo formatına (`| Sütun | Sütun |`) dönüştürüyor. Böylece tablo içindeki veriler de kayıp olmadan sisteme aktarılabiliyor."

---

### 4.10 — `app/services/vector_store.py` → ChromaDB Yöneticisi
**(~2 dakika)**

**Ekranda Yapılacak:** `app/services/vector_store.py` dosyasını aç, `add_chunks` ve `search` metodlarını göster.

**Söyleyeceklerin:**
"`add_chunks` metodu, document_parser'dan gelen chunk listesini alıyor ve her birini ChromaDB'ye kaydediyor. Her chunk için önce embedding oluşturuluyor yani metin bir sayı dizisine çevriliyor, ardından bu sayı dizisi ChromaDB'ye yazılıyor.

`search` metodu ise sorgu zamanında devreye giriyor. Kullanıcının sorusu da embedding'e çevriliyor ve ChromaDB bu sayı dizisine matematiksel olarak en yakın olan chunk'ları buluyor. Burada isteğe bağlı `source_filter` parametresi de var — eğer kullanıcı 'sadece bu PDF içinde ara' derse `where` filtresi devreye giriyor ve ChromaDB yalnızca o dokümanın chunk'larını tarıyor."

---

### 4.11 — `app/core/models.py` ve `app/core/database.py` → Veritabanı Katmanı
**(~2 dakika)**

**Ekranda Yapılacak:** Önce `models.py`, sonra `database.py` dosyasını aç.

**Söyleyeceklerin:**
"`models.py` dosyasında SQLAlchemy ORM ile veritabanı tablolarımızı Python sınıfı olarak tanımladık. `PendingQuestion` tablomuza bakın: `id`, `question`, `asked_by`, `asked_at`, `status` ve `answer` sütunları var. `QuestionStatus` ise bir `Enum` — yani sorunun durumu sadece `Bekliyor` veya `Cevaplandi` olabilir, başka bir değer girilemez.

`database.py` dosyasında ise veritabanı bağlantısını asenkron olarak kuruyoruz. `AsyncSession` kullanmamızın nedeni şu: LLM'den cevap beklerken sunucu kilitlenmesin, başka istekleri karşılayabilsin. `get_db` fonksiyonu bir FastAPI Dependency'si — her request geldiğinde çağrılıyor, işlem bitince bağlantıyı kapatıyor."

---


## 5. BÖLÜM: Veritabanı Yapısı (VS Code / SQLite)
**(Süre: ~5 Dakika)**

**Söyleyeceklerin:**
"Projede iki tip veritabanı kullandık:
1. **ChromaDB (Vektör Veritabanı):** PDF'lerden elde edilen veriler `sentence-transformers` modeli ile vektörlere çevrilip burada tutuluyor. Anlamsal arama yapmamızı sağlayan yer burası.
2. **SQLite (İlişkisel Veritabanı):** `PendingQuestions` (Bekleyen Sorular) adında bir tablomuz var. `models.py` dosyasında (dosyayı aç ve göster) SQLAlchemy ORM kullanarak bu tabloyu modelledik. Soru, soran kişi, tarih ve durum statüsü burada tutuluyor."

---

## 6. BÖLÜM: Teknolojiler ve Kapanış
**(Süre: ~2 Dakika)**

**Söyleyeceklerin:**
"Son olarak projemizin tamamını Docker ile konteynerleştirdik. `docker-compose.yml` (dosyayı açıp göster) dosyamızda frontend ve backend olmak üzere 2 servisimiz var. Ortam değişkenlerini (Environment Variables) buradan yönetiyoruz.
Geliştirme sürecinde;
- LLM olarak **Ollama (Qwen2.5:3b)**
- Backend framework'ü olarak **FastAPI**
- Arayüz için **Gradio**
- Vektör işlemleri için **ChromaDB ve Sentence Transformers** kullandık.

Beni dinlediğiniz için teşekkür ederim."
