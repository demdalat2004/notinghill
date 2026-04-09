"""
NotingHill — services/extractors/docx_extractor.py
"""
from pathlib import Path
from .base import BaseExtractor, ExtractionResult


class DocxExtractor(BaseExtractor):
    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in {".docx", ".doc"}

    def extract(self, path: Path) -> ExtractionResult:
        if self._too_large(path):
            return ExtractionResult(warnings=["File too large"])
        try:
            from docx import Document
            doc = Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            props = doc.core_properties
            r = ExtractionResult(
                text=text,
                metadata={
                    "title": props.title or "",
                    "author": props.author or "",
                    "created": str(props.created) if props.created else "",
                    "modified": str(props.modified) if props.modified else "",
                }
            )
            r.make_preview()
            return r
        except ImportError:
            return ExtractionResult(warnings=["python-docx not installed"])
        except Exception as e:
            return ExtractionResult(warnings=[str(e)])
