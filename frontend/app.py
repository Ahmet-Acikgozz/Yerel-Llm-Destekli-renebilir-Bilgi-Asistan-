"""
frontend/app.py  (2. Hafta -- Modul 2)
Gradio 6 uyumlu surum.

Sekmeler:
  1. Kullanici Sohbet Ekrani
  2. Yonetici Paneli (login + dokuman yukleme + bekleyen sorular)

Calistirma: venv/Scripts/python.exe frontend/app.py
Adres: http://localhost:7860
"""

import os
import requests
import gradio as gr

API_URL = os.environ.get("API_URL", "http://localhost:8000")


# ─── API YARDIMCI FONKSİYONLAR ─────────────────────────────────

def api_query(question: str, source_filter: str | None = None) -> dict:
    payload = {"question": question, "user": "gradio_user"}
    if source_filter and source_filter != "Tümü":
        payload["source_filter"] = source_filter
    try:
        r = requests.post(f"{API_URL}/query/", json=payload, timeout=120)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def api_login(username: str, password: str) -> str | None:
    try:
        r = requests.post(
            f"{API_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()["access_token"]
        return None
    except Exception:
        return None


def api_get_pending(token: str) -> list[dict]:
    try:
        r = requests.get(
            f"{API_URL}/admin/pending-questions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def api_answer_question(token: str, question_id: int, answer: str) -> str:
    try:
        r = requests.post(
            f"{API_URL}/admin/answer/{question_id}",
            json={"answer": answer},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if r.status_code == 200:
            return "✅ " + r.json().get("message", "Basarili!")
        return f"❌ Hata: {r.json().get('detail', 'Bilinmeyen hata')}"
    except Exception as e:
        return f"❌ Baglanti hatasi: {e}"


def api_upload_doc(token: str, file_path: str, category: str) -> str:
    try:
        with open(file_path, "rb") as f:
            filename = os.path.basename(file_path)
            r = requests.post(
                f"{API_URL}/documents/upload?category={category}",
                files={"file": (filename, f)},
                headers={"Authorization": f"Bearer {token}"},
                timeout=120,
            )
        if r.status_code == 200:
            data = r.json()
            return f"✅ Basarili! {data['chunks_created']} chunk olusturuldu. ({data['filename']})"
        return f"❌ Hata: {r.json().get('detail', 'Bilinmeyen hata')}"
    except Exception as e:
        return f"❌ Hata: {e}"


def api_get_sources() -> list[str]:
    try:
        r = requests.get(f"{API_URL}/query/sources", timeout=5)
        sources = r.json().get("kaynaklar", [])
        return ["Tümü"] + [s["source"] for s in sources]
    except Exception:
        return ["Tümü"]


# ─── SEKME 1: KULLANICI SOHBET ─────────────────────────────────

def chat_with_bot(message: str, history: list, source_filter: str):
    if not message.strip():
        return history, ""

    result = api_query(message, source_filter if source_filter != "Tümü" else None)

    if "error" in result:
        bot_reply = (
            f"⚠️ Baglanti hatasi: {result['error']}\n\n"
            "API sunucusu calisiyor mu? (http://localhost:8000)"
        )
    elif result.get("answered"):
        score = result.get("confidence_score", 0)
        rerank = result.get("rerank_score", 0)
        sources = result.get("sources", [])
        bot_reply = result["answer"]
        bot_reply += f"\n\n---\n📊 Benzerlik: `{score:.2f}` | Re-rank: `{rerank:.2f}`"
        if sources:
            bot_reply += "\n\n📄 **Kaynaklar:**"
            for s in sources[:2]:
                preview = s[:120].replace("\n", " ")
                bot_reply += f"\n> {preview}..."
    else:
        score = result.get("confidence_score", 0)
        bot_reply = (
            "ℹ️ Bu konu hakkinda bilgi tabaninda yeterli bilgi bulunamadi.\n"
            "Sorunuz yoneticiye iletildi.\n\n"
            f"📊 En yakin skor: `{score:.2f}`"
        )

    history.append((message, bot_reply))
    return history, ""


def refresh_sources():
    sources = api_get_sources()
    return gr.update(choices=sources, value="Tümü")


# ─── SEKME 2: YÖNETİCİ PANELİ ─────────────────────────────────

def do_login(username: str, password: str):
    token = api_login(username, password)
    if token:
        return (
            token,
            gr.update(visible=False),
            gr.update(visible=True),
            f"✅ Giris basarili! Hosgeldiniz, **{username}**",
        )
    return (
        None,
        gr.update(visible=True),
        gr.update(visible=False),
        "❌ Kullanici adi veya sifre yanlis.",
    )


def load_pending_questions(token: str):
    if not token:
        return [], "⚠️ Lutfen once giris yapin."
    questions = api_get_pending(token)
    pending = [q for q in questions if q["status"] == "Bekliyor"]
    rows = [
        [q["id"], q["question"][:80], q["asked_by"], q["asked_at"][:10]]
        for q in pending
    ]
    msg = f"📋 {len(rows)} bekleyen soru bulundu."
    return rows, msg


def submit_answer(token: str, question_id_text: str, answer_text: str):
    if not token:
        return "⚠️ Lutfen once giris yapin."
    if not question_id_text.strip():
        return "⚠️ Lutfen asagidan bir soru ID'si girin."
    if not answer_text.strip():
        return "⚠️ Cevap alani bos birakilamaz."
    try:
        qid = int(question_id_text.strip())
    except ValueError:
        return "❌ Gecersiz soru ID'si."
    return api_answer_question(token, qid, answer_text)


def upload_document(token: str, file, category: str):
    if not token:
        return "⚠️ Lutfen once giris yapin."
    if file is None:
        return "⚠️ Lutfen bir dosya secin."
    return api_upload_doc(token, file, category)


# ─── GRADIO ARAYÜZÜ ────────────────────────────────────────────

CSS = """
#header { text-align: center; padding: 10px 0 20px 0; }
.source-box { background: #f8f9fa; border-radius: 8px; padding: 8px; font-size: 0.85em; }
"""

with gr.Blocks(title="SoSmart Bilgi Asistani") as demo:

    gr.Markdown(
        """
        <div id="header">
        <h1>🧠 SoSmart Bilgi Asistanı</h1>
        <p>Yerel LLM Destekli Kurumsal Bilgi Sistemi &nbsp;•&nbsp; v2.0</p>
        </div>
        """
    )

    with gr.Tabs():

        # ── SEKME 1: KULLANICI SOHBET ──────────────────────────
        with gr.TabItem("💬 Sohbet"):
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        label="Bilgi Asistani",
                        height=450,
                    )
                    with gr.Row():
                        msg_input = gr.Textbox(
                            placeholder="Sorunuzu buraya yazin ve Enter'a basin...",
                            label="",
                            scale=5,
                            lines=1,
                            show_label=False,
                        )
                        send_btn = gr.Button("Gönder 📤", scale=1, variant="primary")

                with gr.Column(scale=1):
                    gr.Markdown("### ⚙️ Arama Seçenekleri")
                    source_dropdown = gr.Dropdown(
                        choices=["Tümü"],
                        value="Tümü",
                        label="📄 Doküman Filtresi",
                        info="Sadece seçili dokümanda ara",
                    )
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 Yenile", size="sm")
                        clear_btn = gr.Button("🗑️ Temizle", size="sm")

                    gr.Markdown("---")
                    gr.Markdown(
                        """
                        ### ℹ️ Nasıl Çalışır?
                        1. Sorunuzu yazın
                        2. ChromaDB'de **10 sonuç** aranır
                        3. **Re-ranker** en alakalı 4'ü seçer
                        4. LLM cevap üretir
                        5. Kaynak gösterilir
                        """
                    )

            send_btn.click(
                chat_with_bot,
                inputs=[msg_input, chatbot, source_dropdown],
                outputs=[chatbot, msg_input],
            )
            msg_input.submit(
                chat_with_bot,
                inputs=[msg_input, chatbot, source_dropdown],
                outputs=[chatbot, msg_input],
            )
            refresh_btn.click(refresh_sources, outputs=[source_dropdown])
            clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg_input])

        # ── SEKME 2: YÖNETİCİ PANELİ ──────────────────────────
        with gr.TabItem("⚙️ Yönetici Paneli"):

            token_state = gr.State(value=None)

            with gr.Group(visible=True) as login_group:
                gr.Markdown("### 🔐 Yönetici Girişi")
                gr.Markdown("**Test:** `admin` / `admin123`")
                with gr.Row():
                    login_user = gr.Textbox(label="Kullanıcı Adı", placeholder="admin", scale=1)
                    login_pass = gr.Textbox(label="Şifre", type="password", placeholder="admin123", scale=1)
                login_btn = gr.Button("Giriş Yap 🔑", variant="primary", size="lg")
                login_msg = gr.Markdown("")

            with gr.Group(visible=False) as admin_panel:

                with gr.Tabs():

                    # Bekleyen Sorular
                    with gr.TabItem("❓ Bekleyen Sorular"):
                        gr.Markdown(
                            "Bilgi tabanında cevap bulunamayan sorular. "
                            "ID'yi kopyalayıp aşağıdaki alana yapıştırın."
                        )
                        refresh_pending_btn = gr.Button("🔄 Listeyi Yenile", size="sm")
                        pending_status = gr.Markdown("")
                        pending_table = gr.Dataframe(
                            headers=["ID", "Soru", "Soran", "Tarih"],
                            datatype=["number", "str", "str", "str"],
                            interactive=False,
                            wrap=True,
                            label="Bekleyen Sorular",
                        )

                        gr.Markdown("### ✏️ Cevap Ver")
                        with gr.Row():
                            question_id_input = gr.Textbox(
                                label="Soru ID",
                                placeholder="Tablodan ID girin (ör: 3)",
                                scale=1,
                            )
                            answer_input = gr.Textbox(
                                label="Cevap",
                                placeholder="Sorunun cevabını buraya yazın...",
                                lines=3,
                                scale=4,
                            )
                        answer_btn = gr.Button("📚 Bilgi Tabanına Ekle", variant="primary")
                        answer_result = gr.Markdown("")

                    # Doküman Yükleme
                    with gr.TabItem("📂 Doküman Yükleme"):
                        gr.Markdown(
                            "PDF, DOCX, TXT veya Markdown dosyası yükleyin. "
                            "Yükleme sonrası otomatik olarak chunk'lanır ve vektöre çevrilir."
                        )
                        with gr.Row():
                            doc_file = gr.File(
                                label="Dosya Seç (PDF / DOCX / TXT / MD)",
                                file_types=[".pdf", ".docx", ".txt", ".md"],
                            )
                            with gr.Column():
                                doc_category = gr.Dropdown(
                                    choices=["genel", "ik", "finans", "teknik", "hukuk"],
                                    value="genel",
                                    label="Kategori",
                                )
                                upload_btn = gr.Button("⬆️ Yükle ve Ekle", variant="primary")
                        upload_result = gr.Markdown("")

            # ── EVENT HANDLERS ──
            login_btn.click(
                do_login,
                inputs=[login_user, login_pass],
                outputs=[token_state, login_group, admin_panel, login_msg],
            )
            login_pass.submit(
                do_login,
                inputs=[login_user, login_pass],
                outputs=[token_state, login_group, admin_panel, login_msg],
            )
            refresh_pending_btn.click(
                load_pending_questions,
                inputs=[token_state],
                outputs=[pending_table, pending_status],
            )
            answer_btn.click(
                submit_answer,
                inputs=[token_state, question_id_input, answer_input],
                outputs=[answer_result],
            )
            upload_btn.click(
                upload_document,
                inputs=[token_state, doc_file, doc_category],
                outputs=[upload_result],
            )


if __name__ == "__main__":
    print("[Gradio] Arayuz baslatiliyor: http://localhost:7860")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=CSS,
    )
