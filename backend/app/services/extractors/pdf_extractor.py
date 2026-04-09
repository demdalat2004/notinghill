"""
NotingHill — services/extractors/pdf_extractor.py
"""
from pathlib import Path
from .base import BaseExtractor, ExtractionResult


class PdfExtractor(BaseExtractor):
    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def extract(self, path: Path) -> ExtractionResult:
        if self._too_large(path):
            return ExtractionResult(warnings=["File too large"])
        try:
            import pdfplumber
            pages_text = []
            meta = {}
            with pdfplumber.open(str(path)) as pdf:
                meta = pdf.metadata or {}
                for page in pdf.pages[:50]:  # cap at 50 pages
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
            text = "\n".join(pages_text)
            r = ExtractionResult(
                text=text,
                metadata={
                    "title": meta.get("Title", ""),
                    "author": meta.get("Author", ""),
                    "page_count": len(pages_text),
                }
            )
            r.make_preview()
            return r
        except ImportError:
            return ExtractionResult(warnings=["pdfplumber not installed"])
        except Exception as e:
            return ExtractionResult(warnings=[str(e)])
