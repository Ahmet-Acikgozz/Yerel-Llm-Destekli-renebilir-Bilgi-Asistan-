"""
document_parser.py  (2. Hafta — Modül 4)

Yüklenen dokümanları okur ve anlamlı chunk'lara böler.

1. Hafta: Sabit karakter bölme (basit)
2. Hafta: Recursive splitter → paragraf ve anlam sınırlarını korur
           DOCX tablo desteği → Markdown formatına çevirir
           Metadata genişletme → upload_date, category eklendi

Desteklenen formatlar: PDF, DOCX, TXT, Markdown
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class DocumentChunk:
    """
    Bir doküman parçasını temsil eder.
    ChromaDB'ye eklenirken bu yapı kullanılır.
    """
    text: str
    source: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class RecursiveTextSplitter:
    """
    2. Hafta: Recursive Character Text Splitter.

    Sabit karakter kesmesi yerine anlam sınırlarına (paragraf, cümle, boşluk)
    göre böler. Sıradaki ayraçlardan ilk uygun olanı kullanır.

    Ayraç sırası: paragraf sonu → satır sonu → cümle sonu → boşluk → karakter
    """

    SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> list[str]:
        """Metni recursive olarak anlamlı chunk'lara böler."""
        return self._recursive_split(text, self.SEPARATORS)

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """
        Verilen ayraç listesinden ilk uygun olanı kullanarak metni böler.
        Parça hâlâ çok büyükse bir sonraki ayraçla tekrar böler.
        """
        if not text.strip():
            return []

        # Kısa metin — direkt döndür
        if len(text) <= self.chunk_size:
            return [text.strip()]

        # Hiç ayraç kalmadıysa zorla kes
        if not separators:
            return self._hard_split(text)

        sep = separators[0]
        remaining_seps = separators[1:]

        # Bu ayraç metinde yoksa bir sonrakini dene
        if sep and sep not in text:
            return self._recursive_split(text, remaining_seps)

        # Metni ayraçla böl, parçaları biriktirerek chunk'lara topla
        parts = text.split(sep) if sep else list(text)
        return self._merge_parts(parts, sep, remaining_seps)

    def _merge_parts(
        self, parts: list[str], sep: str, remaining_seps: list[str]
    ) -> list[str]:
        """
        Küçük parçaları biriktirerek chunk_size sınırına ulaştığında yeni chunk başlatır.
        chunk_overlap kadar önceki metni yeni chunk'a ekler (bağlam koruması).
        """
        chunks = []
        current = ""

        for part in parts:
            candidate = (current + sep + part).strip() if current else part.strip()

            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                # Mevcut birikimi kaydet
                if current.strip() and len(current.strip()) > 30:
                    chunks.append(current.strip())

                # Parça tek başına chunk_size'dan büyükse recursive böl
                if len(part) > self.chunk_size:
                    sub_chunks = self._recursive_split(part, remaining_seps)
                    chunks.extend(sub_chunks)
                    current = ""
                else:
                    # Overlap: bir önceki chunk'ın sonundan başla
                    overlap_text = self._get_overlap(current)
                    current = (overlap_text + sep + part).strip() if overlap_text else part.strip()

        if current.strip() and len(current.strip()) > 30:
            chunks.append(current.strip())

        return chunks

    def _get_overlap(self, text: str) -> str:
        """Son chunk'tan overlap kadar metin alır (bağlam sürekliliği için)."""
        if len(text) <= self.chunk_overlap:
            return text
        # Kelime sınırından kes
        overlap_start = len(text) - self.chunk_overlap
        space_pos = text.find(" ", overlap_start)
        if space_pos != -1:
            return text[space_pos:].strip()
        return text[-self.chunk_overlap:].strip()

    def _hard_split(self, text: str) -> list[str]:
        """Son çare: sabit karakter kesimi."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.chunk_overlap
            if start >= end:
                break
        return chunks


class DocumentParser:
    """
    Farklı formatlardaki dosyaları okuyup chunk'lara bölen sınıf.

    2. Hafta değişiklikleri:
    - RecursiveTextSplitter kullanıyor (anlam bütünlüğü koruması)
    - chunk_size: 1000, chunk_overlap: 200 (artırıldı)
    - DOCX tabloları Markdown formatına çevriliyor
    - Metadata: upload_date ve category alanları eklendi
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveTextSplitter(chunk_size, chunk_overlap)

    def parse(
        self,
        file_path: str | Path,
        category: str = "genel",
    ) -> list[DocumentChunk]:
        """
        Dosyayı okur ve chunk listesi döndürür.

        Parametreler:
          file_path : Yüklenecek dosyanın yolu
          category  : Doküman kategorisi (ör: "ik", "finans", "teknik")
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            raw_text = self._read_pdf(path)
        elif suffix == ".docx":
            raw_text = self._read_docx(path)
        elif suffix == ".txt":
            raw_text = self._read_txt(path)
        elif suffix in (".md", ".markdown"):
            raw_text = self._read_markdown(path)
        else:
            raise ValueError(f"Desteklenmeyen dosya formati: {suffix}")

        clean_text = self._clean_text(raw_text)
        chunks = self._split_into_chunks(clean_text, source=path.name, category=category)

        return chunks

    # ─── OKUYUCULAR ───────────────────────────────────────────

    def _read_pdf(self, path: Path) -> str:
        """PyMuPDF ile PDF'den metin çıkarır."""
        import fitz

        text_parts = []
        with fitz.open(str(path)) as doc:
            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text("text")
                if page_text.strip():
                    text_parts.append(f"[Sayfa {page_num}]\n{page_text}")

        return "\n\n".join(text_parts)

    def _read_docx(self, path: Path) -> str:
        """
        python-docx ile Word dosyasından metin çıkarır.
        2. Hafta: Tablolar Markdown formatına dönüştürülür.
        """
        from docx import Document

        doc = Document(str(path))
        parts = []

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                # Normal paragraf
                para_text = element.text_content() if hasattr(element, "text_content") else ""
                # python-docx'un kendi paragraph nesnelerini bul
                for para in doc.paragraphs:
                    if para._element is element and para.text.strip():
                        parts.append(para.text)
                        break

            elif tag == "tbl":
                # Tablo → Markdown formatına çevir
                md_table = self._table_to_markdown(element, doc)
                if md_table:
                    parts.append(md_table)

        # Fallback: Eğer element traversal boş kaldıysa standart yöntem
        if not parts:
            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)
            for table in doc.tables:
                md = self._docx_table_to_markdown(table)
                if md:
                    parts.append(md)

        return "\n\n".join(parts)

    def _docx_table_to_markdown(self, table) -> str:
        """python-docx Table nesnesini Markdown tablo metnine çevirir."""
        if not table.rows:
            return ""

        rows = []
        for i, row in enumerate(table.rows):
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                # Başlık satırından sonra ayraç ekle
                separator = "| " + " | ".join(["---"] * len(cells)) + " |"
                rows.append(separator)

        return "\n".join(rows)

    def _table_to_markdown(self, tbl_element, doc) -> str:
        """XML element üzerinden tablo Markdown'a çevirir."""
        try:
            from docx.table import Table
            table = Table(tbl_element, doc)
            return self._docx_table_to_markdown(table)
        except Exception:
            return ""

    def _read_txt(self, path: Path) -> str:
        """Düz metin dosyasını okur."""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")

    def _read_markdown(self, path: Path) -> str:
        """Markdown dosyasını düz metin olarak okur."""
        import markdown
        from html.parser import HTMLParser

        md_content = path.read_text(encoding="utf-8")
        html_content = markdown.markdown(md_content)

        class HTMLStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text_parts = []

            def handle_data(self, data):
                self.text_parts.append(data)

        stripper = HTMLStripper()
        stripper.feed(html_content)
        return " ".join(stripper.text_parts)

    # ─── METİN TEMİZLEME ──────────────────────────────────────

    def _clean_text(self, text: str) -> str:
        """Ham metinden gereksiz boşlukları, tekrar eden satırları temizler."""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {3,}", " ", text)
        text = text.replace("\t", " ")
        return text.strip()

    # ─── CHUNK'LARA BÖLME ─────────────────────────────────────

    def _split_into_chunks(
        self,
        text: str,
        source: str,
        category: str = "genel",
    ) -> list[DocumentChunk]:
        """
        Metni RecursiveTextSplitter ile chunk'lara böler.
        Her chunk'a genişletilmiş metadata (upload_date, category) ekler.
        """
        raw_chunks = self.splitter.split(text)

        upload_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        chunks = []

        for i, chunk_text in enumerate(raw_chunks):
            chunks.append(
                DocumentChunk(
                    text=chunk_text,
                    source=source,
                    chunk_index=i,
                    metadata={
                        "source": source,
                        "chunk_index": i,
                        "category": category,
                        "upload_date": upload_date,
                        "char_count": len(chunk_text),
                    },
                )
            )

        return chunks


# Global parser instance (chunk_size=1000, overlap=200)
parser = DocumentParser(chunk_size=1000, chunk_overlap=200)
