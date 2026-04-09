"""
NotingHill — services/extractors/text_extractor.py
"""
from pathlib import Path
from .base import BaseExtractor, ExtractionResult

SUPPORTED = {".txt", ".md", ".markdown", ".log", ".csv", ".ini", ".cfg",
             ".yaml", ".yml", ".json", ".xml", ".rst", ".toml"}


class TextExtractor(BaseExtractor):
    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in SUPPORTED

    def extract(self, path: Path) -> ExtractionResult:
        if self._too_large(path):
            return ExtractionResult(warnings=["File too large"])
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            r = ExtractionResult(text=text)
            r.make_preview()
            return r
        except Exception as e:
            return ExtractionResult(warnings=[str(e)])
