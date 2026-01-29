from docx import Document


class DocxIngestService:
    def read_paragraphs(self, path: str) -> list[str]:
        document = Document(path)
        return [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
