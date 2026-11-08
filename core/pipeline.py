# ============================================================================
# pipeline — orchestrates the full flow:
#   intake → classify → convert → ocr → markdown → output files
# Also collects stats. This is the single entry the CLI calls.
# ============================================================================
import gc
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# Globally silence unraisable exceptions on Windows
sys.unraisablehook = lambda u: None

from services import registry

from .classify import (
    check_is_auxiliary,
    classify_file,
    detect_mime,
    estimate_tokens,
    get_extension,
    is_ocr_candidate,
)
from .convert import convert_or_placeholder, is_convert_candidate, run_conversion
from .intake import ARCHIVE_EXTS, iter_directory, iter_archive_files
from .markdown import (
    build_combined_markdown,
    build_individual_markdown,
    stream_write_combined_markdown,
)
from .ocr import run_ocr
from .types import ExtractionStats, ExtractedFile
from .ui import ANSI, ProgressBar, format_bytes, print_stage, truncate_middle

# OCR giữ nguyên bytes media — không giới hạn dung lượng (yêu cầu: chạy với
# mọi kích thước file / số lượng). Llama server tự quyết định kết nạp hay lỗi.
LogFn = Callable[[str], None]


MAX_TEXT_PREVIEW_BYTES = 5 * 1024 * 1024  # 5MB safety cap per file to prevent single giant file OOM


def _new_extracted_file(raw_path: str, data: bytes, origin: Optional[str],
                        log: Optional[LogFn] = None,
                        skip_junk: bool = True,
                        skip_auxiliary: bool = True) -> ExtractedFile:
    norm_path = raw_path.replace('\\', '/').lstrip('/')
    name = norm_path.rsplit('/', 1)[-1] or norm_path
    ext = get_extension(norm_path)
    meta = classify_file(norm_path)

    is_aux, aux_reason = check_is_auxiliary(norm_path, ext)
    f = ExtractedFile(
        path=norm_path, name=name, extension=ext,
        category=meta['category'], language=meta['language'],
        size=len(data), mime_type=detect_mime(ext),
        archive_origin=origin,
        is_binary=meta['is_binary'], is_junk=meta['is_junk'],
        is_auxiliary=is_aux, auxiliary_reason=aux_reason,
    )

    # Early discard for junk/auxiliary: zero memory retention (no text decoding, no media bytes)
    if (f.is_junk and skip_junk) or (f.is_auxiliary and skip_auxiliary):
        f.selected = False
        f.media_bytes = None
        f.raw_content = ""
        f.markdown_content = ""
        f.lines_count = 0
        f.word_count = 0
        f.token_estimate = 0
        return f

    # Retain candidate bytes for document conversion & OCR only for selected files
    if is_convert_candidate(ext) or f.category == 'media' or ext == 'pdf':
        f.media_bytes = data

    # --- content stage ----------------------------------------------------
    try:
        if is_convert_candidate(ext):
            # Defer conversion to Stage 2 for progress tracking & ETA!
            f.raw_content = ""
            f.markdown_content = ""
        elif f.category == 'media':
            if ext == 'svg':
                f.raw_content = data.decode('utf-8', errors='replace')
                f.markdown_content = f'```xml\n{f.raw_content}\n```'
            else:
                f.markdown_content = (
                    f'> 🖼️ **Hình ảnh:** `{name}` ({ext.upper()}) · '
                    f'Dung lượng: {len(data) / 1024:.1f} KB'
                )
                f.raw_content = f.markdown_content
        elif f.is_binary:
            f.is_auxiliary = True
            f.auxiliary_reason = f.auxiliary_reason or 'Tập tin nhị phân'
            f.raw_content = ''
            f.markdown_content = (
                f'> ⚙️ **Tập tin nhị phân:** `{name}` ({ext.upper()})\n> '
                f'Kích thước: {len(data) / 1024:.1f} KB *(Đã bỏ qua nội dung thô)*'
            )
        else:
            if len(data) > MAX_TEXT_PREVIEW_BYTES:
                preview = data[:MAX_TEXT_PREVIEW_BYTES].decode('utf-8', errors='replace')
                f.raw_content = preview + f'\n\n> ⚠️ *Tập tin rất lớn ({format_bytes(len(data))}). Đã trích xuất {format_bytes(MAX_TEXT_PREVIEW_BYTES)} đầu.*'
            else:
                f.raw_content = data.decode('utf-8', errors='strict')
            f.markdown_content = ''
    except UnicodeDecodeError:
        # Strict decode failed → treat as binary junk content
        f.is_binary = True
        f.is_auxiliary = True
        f.auxiliary_reason = f.auxiliary_reason or 'Nội dung nhị phân (không decode UTF-8 được)'
        f.raw_content = ''
        f.markdown_content = (
            f'> ⚙️ **Tập tin nhị phân:** `{name}` ({ext.upper()})\n> '
            f'Kích thước: {len(data) / 1024:.1f} KB *(Đã bỏ qua nội dung thô)*'
        )
    except Exception as e:  # noqa: BLE001 — single file never kills the run
        f.markdown_content = f'*(Lỗi khi xử lý nội dung: {e})*'

    measured = f.raw_content or f.markdown_content
    f.lines_count = measured.count('\n') + 1 if measured else 0
    f.word_count = len(measured.split()) if measured else 0
    f.token_estimate = estimate_tokens(measured)
    return f


def _compute_stats(files: list[ExtractedFile]) -> ExtractionStats:
    sel = [f for f in files if f.selected]
    stats = ExtractionStats(
        total_files=len(files),
        total_size=sum(f.size for f in files),
        total_lines=sum(f.lines_count for f in files),
        total_words=sum(f.word_count for f in files),
        total_tokens=sum(f.token_estimate for f in files),
        selected_count=len(sel),
        selected_size=sum(f.size for f in sel),
        selected_lines=sum(f.lines_count for f in sel),
        selected_tokens=sum(f.token_estimate for f in sel),
        auxiliary_count=sum(f.is_auxiliary for f in files),
        junk_count=sum(f.is_junk for f in files),
        converted_count=sum(f.converter_id is not None for f in sel),
        category_counts={},
    )
    for f in sel:
        stats.category_counts[f.category] = stats.category_counts.get(f.category, 0) + 1
    return stats


def build_files(input_path: Path, max_depth: int = 5,
                skip_junk: bool = True,
                skip_auxiliary: bool = True,
                progress_cb: Optional[Callable[[int, str], None]] = None,
                log: Optional[LogFn] = None) -> list[ExtractedFile]:
    """Intake + classify for every leaf file of the input."""
    files: list[ExtractedFile] = []
    if input_path.is_dir():
        source = iter_directory(input_path, max_depth=max_depth, log=log)
        default_origin = None
    else:
        ext = get_extension(input_path.name)
        if ext in ARCHIVE_EXTS:
            default_origin = input_path.name
            source = iter_archive_files(ext, input_path, input_path.name, 0, max_depth, log=log)
        else:
            source = iter_one_file(input_path)
            default_origin = None
    for raw_path, data, origin in source:
        if log:
            log(f'[intake] {origin + " > " + raw_path if origin else raw_path}')
        f = _new_extracted_file(
            raw_path, data, origin or default_origin, log,
            skip_junk=skip_junk, skip_auxiliary=skip_auxiliary,
        )
        files.append(f)
        if progress_cb:
            progress_cb(len(files), f.name)
    return files


def iter_one_file(path: Path):
    yield path.name, path.read_bytes(), None


@dataclass
class RunResult:
    files: list
    stats: ExtractionStats
    output_dir: Path
    combined_path: Optional[Path] = None
    individual_dir: Optional[Path] = None
    archive_name: str = ''


def run(input_path: Path, output_dir: Path, *,
        mode: str = 'combined',          # combined | individual | both
        ocr: bool = True,                # Default True: Auto-OCR images & visual docs
        ocr_prompt: Optional[str] = None,
        ocr_limit: int = 0,
        skip_junk: bool = True,
        skip_auxiliary: bool = True,
        max_depth: int = 5,
        log: Optional[LogFn] = None,
        show_ui: bool = True,
        interactive_ocr: bool = False) -> RunResult:
    """Full pipeline. Returns the run summary including the file list."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Cache hygiene: aged intermediate entries under <root>/cache/tmp die here
    try:
        from services.base import purge_stale_cache
        n = purge_stale_cache()
        if n and log:
            log(f'[cache] Da don {n} cache entry cũ (>24h).')
    except Exception:
        pass

    total_stages = 4

    # ── Stage 1: Intake & Bóc tách ──────────────────────────────────────────
    if show_ui:
        print_stage(1, total_stages, "📦", "Giải nén & Bóc tách kho lưu trữ", f"Quét nguồn: {input_path.name}")
    elif log:
        log(f'[pipeline] Input: {input_path}')

    t0 = time.time()
    last_update = 0.0

    def intake_cb(count: int, name: str) -> None:
        if not sys.stdout.isatty():
            return
        nonlocal last_update
        now = time.time()
        if now - last_update < 0.06:
            return
        last_update = now
        elapsed = max(0.001, now - t0)
        speed = count / elapsed
        trunc_name = truncate_middle(name, 28)
        sys.stdout.write(f"\r  {ANSI.YELLOW}⚡ Đang bóc tách:{ANSI.RESET} {ANSI.BOLD}{ANSI.B_WHITE}{count:,}{ANSI.RESET} tệp {ANSI.GRAY}({speed:.0f} tệp/s) │ {trunc_name}{ANSI.RESET}{ANSI.CLEAR_TO_END}")
        sys.stdout.flush()

    files = build_files(
        input_path, max_depth=max_depth,
        skip_junk=skip_junk, skip_auxiliary=skip_auxiliary,
        progress_cb=intake_cb if show_ui else None,
        log=log if not show_ui else None,
    )

    if show_ui:
        if sys.stdout.isatty():
            sys.stdout.write(f"\r{ANSI.CLEAR_LINE}")
            sys.stdout.flush()

    # Selection filtering
    for f in files:
        if f.is_junk and skip_junk:
            f.selected = False
        elif f.is_auxiliary and skip_auxiliary:
            f.selected = False

    selected_initial = [f for f in files if f.selected]
    junk_aux_count = sum(f.is_junk or f.is_auxiliary for f in files)
    if show_ui:
        print(f"  {ANSI.B_GREEN}✓{ANSI.RESET} Đã bóc tách {ANSI.BOLD}{len(files):,}{ANSI.RESET} tệp tin "
              f"({len(selected_initial):,} hợp lệ, lọc {junk_aux_count:,} rác/phụ trợ) "
              f"{ANSI.GRAY}({time.time() - t0:.2f}s){ANSI.RESET}")
    elif log:
        log(f'[pipeline] Intake xong: {len(files)} file.')

    gc.collect()

    # ── Stage 2: Document Conversion (MarkItDown / Docling) ─────────────────
    if show_ui:
        print_stage(2, total_stages, "📄", "Chuyển đổi tài liệu văn phòng", "Word, Excel, PowerPoint, PDF, HTML...")

    conv_candidates = [
        f for f in files
        if f.selected and is_convert_candidate(f.extension) and f.media_bytes is not None
    ]
    if conv_candidates:
        if show_ui:
            bar = ProgressBar(total=len(conv_candidates), label="Chuyển đổi", unit="tệp")
            conv_ok = run_conversion(
                files,
                progress_cb=lambda curr, tot, name, st: bar.update(curr, item_name=name, status=st)
            )
            bar.finish(f"Đã chuyển đổi thành công {conv_ok}/{len(conv_candidates)} tài liệu văn phòng.")
        else:
            conv_ok = run_conversion(files)
            if log:
                log(f'[pipeline] Converted {conv_ok}/{len(conv_candidates)} tài liệu.')
    else:
        if show_ui:
            print(f"  {ANSI.GRAY}✓ Không có tài liệu văn phòng cần chuyển đổi (Bỏ qua){ANSI.RESET}")

    gc.collect()

    # ── Stage 3: GPU Vision OCR (Qwen2.5-VL-3B) ──────────────────────────────
    if show_ui:
        print_stage(3, total_stages, "👁️", "Nhận diện thị giác Vision AI / OCR", "Qwen2.5-VL-3B trên NVIDIA GPU")

    ocr_candidates = [
        f for f in files
        if f.selected and f.ocr_status == 'idle' and f.media_bytes is not None
        and (f.category == 'media' or (f.extension == 'pdf' and not f.converter_id))
    ]
    if ocr_limit > 0:
        ocr_candidates = ocr_candidates[:ocr_limit]

    # In interactive mode, ask user if they want to OCR detected visual files
    if interactive_ocr and ocr_candidates:
        print()
        print(f"  {ANSI.BOLD}{ANSI.B_YELLOW}💡 Phát hiện {len(ocr_candidates)} tệp hình ảnh / tài liệu trực quan (PNG, JPG, PDF...).{ANSI.RESET}")
        try:
            ans = input(
                f"  {ANSI.BOLD}{ANSI.B_CYAN}[?] Bạn có muốn dùng AI Vision OCR (Qwen2.5-VL GPU) để nhận diện chữ trong các tệp này không? [Y/n]: {ANSI.RESET}"
            ).strip().lower()
            ocr = (ans == '' or ans.startswith('y') or ans == 'c' or ans.startswith('co'))
        except (EOFError, KeyboardInterrupt):
            ocr = False
        print()

    if ocr and ocr_candidates:
        if show_ui:
            bar = ProgressBar(total=len(ocr_candidates), label="Vision OCR", unit="ảnh")
            ocr_ok = run_ocr(
                files, prompt=ocr_prompt, limit=ocr_limit,
                progress_cb=lambda curr, tot, name, st: bar.update(curr, item_name=name, status=st)
            )
            if ocr_ok > 0:
                bar.finish(f"Đã nhận diện OCR thành công {ocr_ok}/{len(ocr_candidates)} hình ảnh.")
            else:
                bar.finish_warn(f"0/{len(ocr_candidates)} hình ảnh có văn bản nhận diện được.")
        else:
            ocr_ok = run_ocr(files, prompt=ocr_prompt, limit=ocr_limit, log=log)
    else:
        if show_ui:
            if not ocr and ocr_candidates and interactive_ocr:
                msg = f"Đã bỏ qua nhận diện OCR cho {len(ocr_candidates)} tệp theo lựa chọn của bạn."
            elif not ocr:
                msg = "Đã tắt OCR (--no-ocr)"
            else:
                msg = "Không phát hiện hình ảnh cần nhận diện OCR (Bỏ qua)"
            print(f"  {ANSI.GRAY}✓ {msg}{ANSI.RESET}")

    # Free all retained media_bytes across all files to minimize memory before Stage 4
    for f in files:
        f.media_bytes = None
    gc.collect()

    # ── Stage 4: Markdown Assembly & Output ──────────────────────────────────
    if show_ui:
        print_stage(4, total_stages, "📑", "Tổng hợp cấu trúc & Xuất Markdown", f"Chế độ: {mode.upper()}")

    t0 = time.time()
    stats = _compute_stats(files)
    stats.ocr_candidate_count = sum(is_ocr_candidate(f.extension, f.category) for f in files)
    stats.ocr_completed_count = sum(f.ocr_status == 'success' for f in files)

    selected = [f for f in files if f.selected]
    archive_name = input_path.stem if input_path.suffix else input_path.name

    combined_path: Optional[Path] = None
    individual_dir: Optional[Path] = None

    if mode in ('combined', 'both'):
        combined_path = output_dir / f'{archive_name}_combined.md'

    if mode in ('individual', 'both'):
        individual_dir = output_dir / f'{archive_name}_markdown'
        individual_dir.mkdir(parents=True, exist_ok=True)

    bar = None
    if show_ui and selected:
        bar = ProgressBar(total=len(selected), label="Xuất Markdown", unit="tệp")

    if mode == 'both':
        def step_cb(curr: int, tot: int, name: str):
            f = selected[curr - 1]
            target = individual_dir / (f.path + '.md')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(build_individual_markdown(f), encoding='utf-8')
            if bar:
                bar.update(curr, item_name=name)

        stream_write_combined_markdown(
            combined_path, selected, stats, archive_name=archive_name,
            progress_cb=step_cb, release_content=True
        )

        index = (
            f'# 📂 Thư mục Markdown đã chuyển đổi: {archive_name}\n\n'
            f'Tạo bởi **Archive2MD**. Tổng số file .md: **{len(selected):,}**.\n\n'
            + '\n'.join(f'- [{f.name}.md](./{f.path}.md) *({f.category}, {f.lines_count:,} dòng)*'
                        for f in selected)
        )
        (individual_dir / 'README_INDEX.md').write_text(index, encoding='utf-8')

    elif mode == 'combined':
        stream_write_combined_markdown(
            combined_path, selected, stats, archive_name=archive_name,
            progress_cb=lambda curr, tot, name: bar.update(curr, item_name=name) if bar else None,
            release_content=True
        )

    elif mode == 'individual':
        for i, f in enumerate(selected, 1):
            target = individual_dir / (f.path + '.md')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(build_individual_markdown(f), encoding='utf-8')
            f.raw_content = ""
            f.markdown_content = ""
            if bar:
                bar.update(i, item_name=f.name)

        index = (
            f'# 📂 Thư mục Markdown đã chuyển đổi: {archive_name}\n\n'
            f'Tạo bởi **Archive2MD**. Tổng số file .md: **{len(selected):,}**.\n\n'
            + '\n'.join(f'- [{f.name}.md](./{f.path}.md) *({f.category}, {f.lines_count:,} dòng)*'
                        for f in selected)
        )
        (individual_dir / 'README_INDEX.md').write_text(index, encoding='utf-8')

    if bar:
        if combined_path and combined_path.exists():
            out_sz = format_bytes(combined_path.stat().st_size)
            bar.finish(f"Đã xuất '{combined_path.name}' ({out_sz}, ~{stats.selected_tokens:,} tokens)")
        elif individual_dir:
            bar.finish(f"Đã xuất thư mục '{individual_dir.name}' ({len(selected):,} tệp .md)")
    elif show_ui:
        if combined_path and combined_path.exists():
            out_sz = format_bytes(combined_path.stat().st_size)
            print(f"  {ANSI.B_GREEN}✓{ANSI.RESET} Đã xuất '{combined_path.name}' ({out_sz}, ~{stats.selected_tokens:,} tokens) {ANSI.GRAY}({time.time() - t0:.2f}s){ANSI.RESET}")
        elif individual_dir:
            print(f"  {ANSI.B_GREEN}✓{ANSI.RESET} Đã xuất thư mục '{individual_dir.name}' ({len(selected):,} tệp .md) {ANSI.GRAY}({time.time() - t0:.2f}s){ANSI.RESET}")

    gc.collect()

    return RunResult(
        files=selected, stats=stats, output_dir=output_dir,
        combined_path=combined_path, individual_dir=individual_dir,
        archive_name=archive_name,
    )
