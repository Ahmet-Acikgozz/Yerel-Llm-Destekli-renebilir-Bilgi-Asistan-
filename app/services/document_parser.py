import re
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DocumentChunk:
    text: str
    source: str
    chunk_index: int
    metadata: dict

class DocumentParser:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def parse(self, file_path: str | Path) -> list[DocumentChunk]:
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
            raise ValueError(f"Desteklenmeyen dosya formatı: {suffix}")

        clean_text = self._clean_text(raw_text)

        chunks = self._split_into_chunks(clean_text, source=path.name)

        return chunks

    def _read_pdf(self, path: Path) -> str:
        import fitz

        text_parts = []
        with fitz.open(str(path)) as doc:
            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text("text")
                if page_text.strip():
                    text_parts.append(f"[Sayfa {page_num}]\n{page_text}")

        return "\n\n".join(text_parts)

    def _read_docx(self, path: Path) -> str:
        from docx import Document

        doc = Document(str(path))
        paragraphs = []

        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)

        return "\n\n".join(paragraphs)

    def _read_txt(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")

    def _read_markdown(self, path: Path) -> str:
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

    def _clean_text(self, text: str) -> str:

        text = re.sub(r"\n{3,}", "\n\n", text)

        text = re.sub(r" {3,}", " ", text)

        text = text.replace("\t", " ")
        return text.strip()

    def _split_into_chunks(self, text: str, source: str) -> list[DocumentChunk]:
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size

            if end < len(text):

                last_space = text.rfind(" ", start, end)
                if last_space > start + (self.chunk_size // 2):
                    end = last_space

            chunk_text = text[start:end].strip()

            if len(chunk_text) > 50:
                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        source=source,
                        chunk_index=chunk_index,
                        metadata={
                            "source": source,
                            "chunk_index": chunk_index,
                            "start_char": start,
                            "end_char": end,
                        },
                    )
                )
                chunk_index += 1

            start = end - self.chunk_overlap

        return chunks

# Global parser instance
parser = DocumentParser(chunk_size=1000, chunk_overlap=150)
