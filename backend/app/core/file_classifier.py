"""
NotingHill — core/file_classifier.py
Classify files into type groups.
"""
from pathlib import Path

TYPE_MAP = {
    "text":   {".txt",".md",".markdown",".log",".csv",".rst",".toml",".ini",".cfg"},
    "code":   {".py",".js",".ts",".jsx",".tsx",".java",".c",".cpp",".h",".cs",
               ".go",".rs",".rb",".php",".swift",".kt",".sh",".bat",".ps1",
               ".html",".css",".scss",".sql",".xml",".yaml",".yml",".json"},
    "pdf":    {".pdf"},
    "office": {".docx",".doc",".xlsx",".xls",".xlsm",".pptx",".ppt",".odt",".ods"},
    "image":  {".jpg",".jpeg",".png",".gif",".bmp",".tiff",".tif",
               ".webp",".heic",".heif",".raw",".cr2",".nef",".svg",".ico"},
    "audio":  {".mp3",".flac",".ogg",".m4a",".aac",".wav",".wma",".opus"},
    "video":  {".mp4",".mkv",".avi",".mov",".wmv",".flv",".webm",".m4v"},
    "archive":{".zip",".tar",".gz",".bz2",".xz",".7z",".rar"},
}

_EXT_TO_GROUP: dict[str, str] = {}
for _group, _exts in TYPE_MAP.items():
    for _ext in _exts:
        _EXT_TO_GROUP[_ext] = _group


def classify(path: Path) -> str:
    return _EXT_TO_GROUP.get(path.suffix.lower(), "other")


IGNORED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__",
    ".mypy_cache", ".tox", "venv", ".venv", "env",
    "$RECYCLE.BIN", "System Volume Information",
}

IGNORED_EXTENSIONS = {".tmp", ".lock", ".DS_Store", ".Thumbs.db"}


def should_ignore(path: Path) -> bool:
    if path.name.startswith(".") and path.suffix not in {".md", ".env"}:
        return True
    if path.suffix.lower() in IGNORED_EXTENSIONS:
        return True
    for part in path.parts:
        if part in IGNORED_DIRS:
            return True
    return False
