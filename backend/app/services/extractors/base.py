"""
NotingHill — services/extractors/base.py
Base class for all file extractors.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractionResult:
    text: str = ""
    preview: str = ""
    metadata: dict = field(default_factory=dict)
    language: str = ""
    warnings: list[str] = field(default_factory=list)

    def make_preview(self, chars: int = 400) -> str:
        if not self.preview and self.text:
            self.preview = self.text[:chars].strip()
        return self.preview


class BaseExtractor(ABC):
    MAX_SIZE_MB = 50

    @abstractmethod
    def supports(self, path: Path) -> bool: ...

    @abstractmethod
    def extract(self, path: Path) -> ExtractionResult: ...

    def _too_large(self, path: Path) -> bool:
        try:
            return path.stat().st_size > self.MAX_SIZE_MB * 1024 * 1024
        except OSError:
            return True
