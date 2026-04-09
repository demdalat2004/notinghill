"""
NotingHill — services/extractors/image_extractor.py
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BaseExtractor, ExtractionResult

IMG_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".heic", ".heif", ".raw", ".cr2", ".nef",
}


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, tuple) and len(value) == 2:
            num, den = value
            den = float(den)
            if den == 0:
                return None
            return float(num) / den
        return float(value)
    except Exception:
        return None


def _parse_gps_coord(values: Any, ref: Any) -> float | None:
    try:
        if not values or len(values) < 3:
            return None
        deg = _to_float(values[0])
        mins = _to_float(values[1])
        secs = _to_float(values[2])
        if deg is None or mins is None or secs is None:
            return None
        dec = deg + (mins / 60.0) + (secs / 3600.0)
        ref_str = str(ref or "").upper()
        if ref_str in ("S", "W"):
            dec = -dec
        return round(dec, 7)
    except Exception:
        return None


class ImageExtractor(BaseExtractor):
    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in IMG_EXTS

    def extract(self, path: Path) -> ExtractionResult:
        meta: dict[str, Any] = {}
        warnings: list[str] = []

        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS

            with Image.open(str(path)) as img:
                meta["width"] = img.width
                meta["height"] = img.height
                meta["mode"] = img.mode
                meta["format"] = img.format

                try:
                    exif_data = img.getexif()
                    if exif_data:
                        gps_meta: dict[str, Any] = {}
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == "GPSInfo" and isinstance(value, dict):
                                for gps_tag_id, gps_value in value.items():
                                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                    gps_meta[str(gps_tag)] = gps_value
                            elif tag in (
                                "Make", "Model", "DateTime", "DateTimeOriginal",
                                "ImageDescription", "Artist", "Copyright", "Software",
                                "ExposureTime", "FNumber", "ISOSpeedRatings",
                                "LensModel", "FocalLength", "Orientation",
                            ):
                                try:
                                    meta[str(tag)] = str(value)
                                except Exception:
                                    pass

                        if gps_meta:
                            lat = _parse_gps_coord(
                                gps_meta.get("GPSLatitude"),
                                gps_meta.get("GPSLatitudeRef"),
                            )
                            lon = _parse_gps_coord(
                                gps_meta.get("GPSLongitude"),
                                gps_meta.get("GPSLongitudeRef"),
                            )
                            if lat is not None:
                                meta["gps_lat"] = lat
                            if lon is not None:
                                meta["gps_lon"] = lon
                            if lat is not None and lon is not None:
                                meta["gps_text"] = f"{lat:.6f}, {lon:.6f}"

                        if meta.get("Model") and not meta.get("camera_model"):
                            meta["camera_model"] = meta.get("Model")

                        if "DateTimeOriginal" in meta:
                            try:
                                dt = datetime.strptime(meta["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
                                meta["taken_ts"] = int(dt.timestamp())
                            except Exception:
                                pass
                except Exception:
                    pass
        except ImportError:
            warnings.append("Pillow not installed")
        except Exception as e:
            warnings.append(str(e))

        text = f"Image {meta.get('width', '?')}x{meta.get('height', '?')} {meta.get('format', '')}".strip()
        if meta.get("Model"):
            text += f" | Camera: {meta['Model']}"
        if meta.get("DateTimeOriginal"):
            text += f" | Taken: {meta['DateTimeOriginal']}"
        if meta.get("gps_text"):
            text += f" | GPS: {meta['gps_text']}"

        return ExtractionResult(text=text, preview=text, metadata=meta, warnings=warnings)
