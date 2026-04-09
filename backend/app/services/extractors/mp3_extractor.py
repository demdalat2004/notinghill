"""
NotingHill — services/extractors/mp3_extractor.py
"""
from pathlib import Path
from .base import BaseExtractor, ExtractionResult

AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wav", ".wma", ".opus"}


class Mp3Extractor(BaseExtractor):
    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in AUDIO_EXTS

    def extract(self, path: Path) -> ExtractionResult:
        meta = {}
        warnings = []
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(str(path), easy=True)
            if audio:
                for tag in ("title", "artist", "album", "albumartist",
                            "date", "genre", "tracknumber", "discnumber", "comment"):
                    val = audio.get(tag)
                    if val:
                        meta[tag] = str(val[0]) if isinstance(val, list) else str(val)
                if hasattr(audio, "info") and audio.info:
                    meta["duration_seconds"] = round(audio.info.length, 2)
                    meta["bitrate"] = getattr(audio.info, "bitrate", None)
                    meta["sample_rate"] = getattr(audio.info, "sample_rate", None)
        except ImportError:
            warnings.append("mutagen not installed")
        except Exception as e:
            warnings.append(str(e))

        parts = []
        if meta.get("title"):
            parts.append(meta["title"])
        if meta.get("artist"):
            parts.append(meta["artist"])
        if meta.get("album"):
            parts.append(meta["album"])
        if meta.get("duration_seconds"):
            secs = int(meta["duration_seconds"])
            parts.append(f"{secs//60}:{secs%60:02d}")
        text = " — ".join(parts) if parts else path.stem
        meta["title"] = meta.get("title", path.stem)
        meta["artist"] = meta.get("artist", "")
        meta["album"] = meta.get("album", "")

        return ExtractionResult(text=text, preview=text, metadata=meta, warnings=warnings)
