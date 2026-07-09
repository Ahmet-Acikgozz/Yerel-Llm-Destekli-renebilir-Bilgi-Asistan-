"""
llm_service.py

Ollama üzerinden yerel LLM ile iletişimi yönetir.

Temel prensipler:
  - Model YALNIZCA verilen bağlamı (context) kullanarak cevap üretir
  - Bağlamda cevap yoksa "Bilgi bulunamadı." döndürür
  - Cevap JSON formatında gelir → kolay parse edilir
  - Tahmin yapmaz, uydurmaz

Ollama API:
  POST http://localhost:11434/api/generate
  Body: { model, prompt, stream }
"""

import json
import httpx

from app.core.config import settings


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
# Bu metin her istekte modele "kimliğini" ve "kurallarını" tanımlar.
# Ne kadar net yazılırsa model o kadar iyi uyar.

SYSTEM_PROMPT = """Sen bir kurumsal bilgi asistanısın. Görevin, sana verilen BAĞLAM bilgisini kullanarak kullanıcı sorularını yanıtlamaktır.

ZORUNLU KURALLAR:
1. Yalnızca sana verilen BAĞLAM içindeki bilgileri kullan. Kendi genel bilgini KULLANMA.
2. Bağlamda cevap bulamazsan kesinlikle tahmin yapma veya uydurma.
3. Kullanıcının sorusu, bağlamdaki soruyla farklı kelimelerle ifade edilmiş olsa bile (eşanlamlıysa) cevabı kullanmaktan çekinme.
4. Cevabını MUTLAKA JSON formatında ver. Eğer cevabı bulduysan {"answer": "Gerçek cevap cümlesi", "found": true} döndür. Bulamadıysan {"answer": "Bilgi bulunamadi.", "found": false} döndür.

ÖNEMLİ: JSON dışında HİÇBİR şey yazma."""


class LLMService:
    """
    Ollama HTTP API'si ile iletişimi yöneten sınıf.

    Ollama, yerel makinede çalışan bir LLM sunucusudur.
    REST API üzerinden modele istek atılır, cevap alınır.
    """

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        # Ollama bazen yavaş olabilir, yüksek timeout şart
        self.timeout = httpx.Timeout(120.0)

    async def generate(self, question: str, context_chunks: list[str]) -> dict:
        """
        Soruyu ve bağlamı LLM'e gönderir, JSON cevap alır.

        Parametreler:
          question       : Kullanıcının sorusu
          context_chunks : ChromaDB'den bulunan ilgili metin parçaları

        Döndürür:
          {
            "answer": "Cevap metni",
            "found": True/False,
            "raw_response": "LLM'in ham çıktısı"
          }
        """
        # ── 1. Bağlamı birleştir ──
        # Birden fazla chunk varsa numaralandırarak birleştir
        if context_chunks:
            context_text = "\n\n".join(
                f"[Kaynak {i+1}]: {chunk}"
                for i, chunk in enumerate(context_chunks)
            )
        else:
            context_text = "Bu konuyla ilgili bilgi tabanında içerik bulunamadı."

        # ── 2. Prompt oluştur ──
        # System prompt + bağlam + soru birleşimi
        full_prompt = f"""{SYSTEM_PROMPT}

---
BAĞLAM:
{context_text}

---
SORU: {question}

CEVAP (sadece JSON):"""

        # ── 3. Ollama'ya HTTP isteği at ──
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,        # Tek seferde tüm cevabı al
                        "options": {
                            "temperature": 0.1, # Düşük = tutarlı, az yaratıcı
                            "top_p": 0.9,
                        },
                    },
                )
                response.raise_for_status()
        except httpx.ConnectError:
            return {
                "answer": "Hata: Ollama baglantisi kurulamadi. 'ollama serve' komutunu calistirdin mi?",
                "found": False,
                "raw_response": "",
            }
        except httpx.TimeoutException:
            return {
                "answer": "Hata: LLM cevap uretmek icin cok uzun sure bekledi.",
                "found": False,
                "raw_response": "",
            }

        # ── 4. Cevabı parse et ──
        raw_text = response.json().get("response", "")
        return self._parse_response(raw_text)

    def _parse_response(self, raw_text: str) -> dict:
        """
        LLM'in ham metin çıktısından JSON'u çıkarır.

        LLM bazen JSON'un etrafına açıklama yazabilir.
        Bu metod önce tam JSON'u dener, başarısız olursa
        metindeki JSON bloğunu bulmaya çalışır.
        """
        raw_text = raw_text.strip()

        # Deneme 1: Direkt JSON parse
        try:
            data = json.loads(raw_text)
            return {
                "answer": data.get("answer", "Bilgi bulunamadi."),
                "found": data.get("found", False),
                "raw_response": raw_text,
            }
        except json.JSONDecodeError:
            pass

        # Deneme 2: Metin içindeki { } bloğunu bul
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(raw_text[start:end])
                return {
                    "answer": data.get("answer", "Bilgi bulunamadi."),
                    "found": data.get("found", False),
                    "raw_response": raw_text,
                }
            except json.JSONDecodeError:
                pass

        # Deneme 3: JSON parse tamamen başarısız — metni olduğu gibi kullan
        # Bu genellikle model system prompt'u tam uymadığında olur
        return {
            "answer": raw_text if raw_text else "Bilgi bulunamadi.",
            "found": bool(raw_text),
            "raw_response": raw_text,
        }

    async def check_connection(self) -> bool:
        """Ollama sunucusuna bağlantıyı test eder."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


# ─────────────────────────────────────────────
# Global singleton instance
# ─────────────────────────────────────────────
llm_service = LLMService()
