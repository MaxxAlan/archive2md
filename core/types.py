# ============================================================================
# Core data contracts — single source of truth for every pipeline stage.
# ============================================================================
from dataclasses import dataclass, field
from typing import Optional

FileCategory = str  # code | database | document | spreadsheet | config | archive | media | other


@dataclass
class ExtractedFile:
    """One file produced by intake + enriched by later stages."""
    path: str                      # normalized 'a/b/c.ext', forward slashes
    name: str                      # basename
    extension: str                 # lowercase without dot
    category: FileCategory
    language: str
    size: int
    lines_count: int = 0
    word_count: int = 0
    token_estimate: int = 0
    raw_content: str = ""          # text/code content (or converted markdown)
    markdown_content: str = ""     # converter/OCR output; '' for plain text files
    mime_type: Optional[str] = None
    media_bytes: Optional[bytes] = None  # raw bytes for OCR candidates (media/pdf)
    archive_origin: Optional[str] = None # 'a.zip > nested.rar' chain
    is_binary: bool = False
    is_auxiliary: bool = False
    auxiliary_reason: Optional[str] = None
    is_junk: bool = False
    selected: bool = True
    ocr_status: str = "idle"       # idle | pending | success | failed | skipped
    ocr_error: Optional[str] = None
    converter_id: Optional[str] = None

    @property
    def display_content(self) -> str:
        return self.raw_content or self.markdown_content


@dataclass
class ExtractionStats:
    total_files: int = 0
    total_size: int = 0
    total_lines: int = 0
    total_words: int = 0
    total_tokens: int = 0
    selected_count: int = 0
    selected_size: int = 0
    selected_lines: int = 0
    selected_tokens: int = 0
    auxiliary_count: int = 0
    junk_count: int = 0
    ocr_candidate_count: int = 0
    ocr_completed_count: int = 0
    converted_count: int = 0
    category_counts: dict = field(default_factory=dict)
