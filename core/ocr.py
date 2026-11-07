# ============================================================================
# ocr — vision OCR orchestration over the services registry (Qwen local).
# Degrades per-file: an OCR failure marks the file failed, pipeline continues.
# ============================================================================
import time
from typing import Callable, Optional

from services.registry import registry

from .classify import estimate_tokens
from .types import ExtractedFile


LogFn = Callable[[str], None]


def run_ocr(files: list[ExtractedFile], prompt: Optional[str] = None,
            limit: int = 0, log: Optional[LogFn] = None,
            progress_cb: Optional[Callable[[int, int, str, str], None]] = None) -> int:
    """OCR every eligible selected file (media bytes were retained by intake).

    Returns the count of successful conversions. A missing provider is a
    single warning; per-file errors mark only that file as failed.
    """
    candidates = [
        f for f in files
        if f.selected and f.ocr_status == 'idle' and f.media_bytes is not None
        and (f.category == 'media' or (f.extension == 'pdf' and not f.converter_id))
    ]
    if limit > 0:
        candidates = candidates[:limit]
    if not candidates:
        return 0

    if registry.ocr_provider() is None:
        if log:
            log('[ocr] Không có OCR provider sẵn sàng — bỏ qua OCR.')
        for f in candidates:
            f.ocr_status = 'skipped'
        return 0

    total = len(candidates)
    if not progress_cb and log:
        log(f'[ocr] Phát hiện {total} file hình ảnh/tài liệu -> Tự động nhận diện OCR bằng GPU...')

    ok = 0
    for i, f in enumerate(candidates, 1):
        if progress_cb:
            progress_cb(i - 1, total, f.name, "GPU đang đọc...")
        elif log:
            log(f'[ocr] ({i}/{total}) {f.path}')

        t0 = time.time()
        try:
            markdown = registry.ocr(f.media_bytes, f.mime_type or 'image/png', f.name, prompt)
            took = time.time() - t0
            if markdown and not markdown.startswith('*('):
                f.ocr_status = 'success'
                f.markdown_content = markdown
                f.raw_content = markdown
                f.lines_count = markdown.count('\n') + 1
                f.word_count = len(markdown.split())
                f.token_estimate = estimate_tokens(markdown)
                ok += 1
                if progress_cb:
                    progress_cb(i, total, f.name, f"OK {took:.1f}s")
                elif log:
                    log(f'[ocr] OK {f.name} ({took:.1f}s)')
            else:
                f.ocr_status = 'failed'
                f.ocr_error = markdown or 'Provider trả về rỗng'
                f.markdown_content = markdown or f'*(Không có nội dung nhận diện từ {f.name})*'
                f.raw_content = f.markdown_content
                if progress_cb:
                    progress_cb(i, total, f.name, "Bỏ qua")
        except Exception as e:  # noqa: BLE001 — per-file failure only
            f.ocr_status = 'failed'
            f.ocr_error = str(e)
            took = time.time() - t0
            if progress_cb:
                progress_cb(i, total, f.name, f"Lỗi: {e}")
            elif log:
                log(f'[ocr] Lỗi {f.path} ({took:.1f}s): {e}')
        finally:
            f.media_bytes = None

    if not progress_cb and log:
        log(f'[ocr] Hoàn thành tự động OCR {ok}/{total} file.')
    return ok
