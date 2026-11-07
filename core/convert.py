# ============================================================================
# convert — route document files through the services registry.
# Fallback-friendly: converter errors degrade to a note in the markdown,
# never abort the whole pipeline.
# ============================================================================
from typing import Callable, Optional

from services.registry import registry
from .classify import estimate_tokens
from .types import ExtractedFile

# Document formats owned by the converter backends (docling / markitdown).
CONVERT_EXTENSIONS = frozenset({
    'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls', 'pdf',
    'html', 'htm', 'epub', 'msg', 'eml', 'rtf',
    'odt', 'ods', 'odp', 'csv', 'tsv', 'xml',
})


def is_convert_candidate(extension: str) -> bool:
    return extension.lower() in CONVERT_EXTENSIONS


def convert_file(file_name: str, data: bytes) -> tuple[Optional[str], Optional[str]]:
    """Try every matching converter in priority order.

    Returns (markdown, converter_id) or (None, None) when nothing claimed it.
    A backend error is returned as markdown placeholder text instead of raising.
    """
    result = registry.convert(file_name, data)
    if result is None:
        return None, None
    markdown, converter_id = result
    return markdown, converter_id


def convert_or_placeholder(file_name: str, data: bytes, extension: str) -> tuple[str, Optional[str]]:
    """Like convert_file but never returns None: on failure returns a note."""
    try:
        markdown, converter_id = convert_file(file_name, data)
    except Exception as e:  # noqa: BLE001 — degrade, don't abort
        return f'*(Loi khi chuyen doi {file_name}: {e})*', None
    if markdown is None:
        return f'*(Khong co converter san sang cho .{extension} — cai dat markitdown hoac docling)*', None
    return markdown, converter_id


def run_conversion(files: list[ExtractedFile],
                   progress_cb: Optional[Callable[[int, int, str, str], None]] = None) -> int:
    """Batch convert all eligible document files with progress reporting."""
    candidates = [
        f for f in files
        if f.selected and is_convert_candidate(f.extension) and f.media_bytes is not None
    ]
    if not candidates:
        return 0

    ok = 0
    total = len(candidates)
    for i, f in enumerate(candidates, 1):
        if progress_cb:
            progress_cb(i - 1, total, f.name, "Đang chuyển đổi...")
        try:
            markdown, converter_id = convert_or_placeholder(f.name, f.media_bytes, f.extension)
            f.markdown_content = markdown
            f.raw_content = markdown
            f.converter_id = converter_id
            measured = f.raw_content or f.markdown_content
            f.lines_count = measured.count('\n') + 1 if measured else 0
            f.word_count = len(measured.split()) if measured else 0
            f.token_estimate = estimate_tokens(measured)
            ok += 1
            if progress_cb:
                progress_cb(i, total, f.name, f"OK ({converter_id})")
        except Exception as e:
            f.markdown_content = f'*(Lỗi khi xử lý nội dung {f.name}: {e})*'
            if progress_cb:
                progress_cb(i, total, f.name, f"Lỗi: {e}")
        finally:
            # Reclaim memory if not needed for OCR
            if f.category != 'media' and f.extension != 'pdf':
                f.media_bytes = None
    return ok
