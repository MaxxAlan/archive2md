# ============================================================================
# markdown — Markdown document builders. Ported from markdownBuilder.ts:
# ascii tree, TOC, stats tables, combined master doc, individual .md files.
# ============================================================================
from datetime import datetime
import io
from pathlib import Path
from typing import Callable, Optional, TextIO, Union

from .classify import format_bytes
from .types import ExtractionStats, ExtractedFile

CATEGORY_LABELS = {
    'code': '💻 Mã nguồn & Scripts',
    'database': '🗄️ CSDL & SQL',
    'document': '📄 Tài liệu (PDF, Word, Docx)',
    'spreadsheet': '📊 Bảng tính & Dữ liệu (Excel, CSV)',
    'config': '⚙️ Cấu hình & Thiết lập',
    'archive': '📦 File nén lồng nhau',
    'media': '🎨 Ảnh & Đồ họa',
    'other': '📁 Khác',
}

CATEGORY_ICONS = {
    'code': '💻', 'database': '🗄️', 'spreadsheet': '📊',
    'document': '📄', 'config': '⚙️', 'archive': '📦',
    'media': '🎨', 'other': '📁',
}


def file_body_markdown(file: ExtractedFile) -> str:
    """Content body for one file, formatted by category."""
    if file.category in ('spreadsheet',) or (file.category == 'document' and file.extension != 'txt'):
        body = file.markdown_content or file.raw_content
    elif file.category in ('code', 'database', 'config') or file.extension == 'txt':
        lang = file.language or ''
        content = file.raw_content or file.markdown_content or ''
        return f'```{lang}\n{content}\n```'
    elif file.category == 'media':
        if file.ocr_status == 'success':
            return '> 🖼️ **Nội dung nhận diện từ hình ảnh (AI Multimodal OCR):**\n\n' + (file.markdown_content or file.raw_content or '*(Không có nội dung OCR)*')
        return file.markdown_content or file.raw_content or '*(Hình ảnh chưa quét OCR)*'
    else:
        body = file.markdown_content or file.raw_content
    return body or '*(Không có nội dung văn bản khả dụng)*'


def create_anchor_slug(path: str) -> str:
    slug = ''.join(c.lower() if c.isalnum() or c in '_-' else '-' for c in path.lower())
    while '--' in slug:
        slug = slug.replace('--', '-')
    return 'file-' + slug.strip('-')


def build_ascii_tree(paths: list[str], max_entries: int = 500) -> str:
    root: dict = {}
    for p in paths:
        node = root
        for part in p.replace('\\', '/').split('/'):
            if part:
                node = node.setdefault(part, {})
    # Sort: dirs first, then files; case-insensitive
    def sorted_keys(node: dict) -> list[str]:
        return sorted(node.keys(), key=lambda k: (len(node[k]) == 0, k.lower()))
    lines: list[str] = []
    capped = False

    def print_node(node: dict, prefix: str = '') -> None:
        nonlocal capped
        if capped:
            return
        keys = sorted_keys(node)
        for i, key in enumerate(keys):
            if len(lines) >= max_entries:
                capped = True
                lines.append(f'{prefix}└── ... (còn {len(paths) - len(lines):,} tệp/thư mục khác — xem Mục lục bên dưới)')
                return
            is_last = i == len(keys) - 1
            marker = '└── ' if is_last else '├── '
            is_dir = len(node[key]) > 0
            lines.append(f'{prefix}{marker}{key}{" /" if is_dir else ""}')
            if is_dir:
                print_node(node[key], prefix + ('    ' if is_last else '│   '))

    print_node(root)
    return '\n'.join(lines) if lines else '(Chưa có tệp nào)'


def build_individual_markdown(file: ExtractedFile, include_metadata: bool = True) -> str:
    parts: list[str] = []
    if include_metadata:
        parts.append('<!-- File converted by Archive2MD -->')
        parts.append(f'# 📄 `{file.path}`')
        parts.append('')
        parts.append('| Thuộc tính | Giá trị |')
        parts.append('| :--- | :--- |')
        parts.append(f'| **Đường dẫn gốc** | `{file.path}` |')
        parts.append(f'| **Loại tệp** | `{file.category.upper()}` ({file.language}) |')
        parts.append(f'| **Kích thước** | {format_bytes(file.size)} |')
        parts.append(f'| **Số dòng** | {file.lines_count:,} dòng |')
        parts.append(f'| **Ước tính token LLM** | ~{file.token_estimate:,} tokens |')
        if file.archive_origin:
            parts.append(f'| **Tệp nén gốc** | `{file.archive_origin}` |')
        parts.append('')
        parts.append('---')
        parts.append('')
    parts.append(file_body_markdown(file))
    return '\n'.join(parts)


def stream_write_combined_markdown(
    dest: Union[Path, str, TextIO],
    files: list[ExtractedFile],
    stats: ExtractionStats,
    archive_name: str = 'archive',
    include_toc: bool = True,
    include_tree: bool = True,
    include_stats: bool = True,
    include_metadata: bool = True,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    release_content: bool = False,
) -> int:
    """Stream combined markdown directly to disk in buffered chunks.
    Eliminates MemoryError by avoiding multi-gigabyte in-memory string concatenations.
    If release_content is True, clears file.raw_content & file.markdown_content after writing.
    Returns bytes written.
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_files = len(files)

    def _write_content(f: TextIO) -> int:
        written = 0

        def w(text: str) -> None:
            nonlocal written
            written += f.write(text)

        w('<a id="top"></a>\n')
        w(f'# 📦 Tổng hợp dữ liệu: `{archive_name}`\n\n')
        w(f'> Tài liệu được tạo tự động bởi **Archive2MD** vào lúc **{now}**.\n\n')

        if include_stats:
            w('## 📊 Thống kê tổng quan\n\n')
            w('| Chỉ số | Chi tiết |\n')
            w('| :--- | :--- |\n')
            w(f'| **Tổng số tệp chuyển đổi** | **{stats.selected_count:,}** tệp (trên tổng {stats.total_files:,}) |\n')
            w(f'| **Tổng dung lượng văn bản** | **{format_bytes(stats.selected_size)}** |\n')
            w(f'| **Tổng số dòng mã / văn bản** | **{stats.selected_lines:,}** dòng |\n')
            w(f'| **Ước tính ngữ cảnh LLM** | **~{stats.selected_tokens:,}** tokens |\n\n')
            w('### Phân loại theo định dạng\n\n')
            w('| Danh mục | Số lượng | Tỷ lệ |\n')
            w('| :--- | :--- | :--- |\n')
            total = stats.selected_count or 1
            for cat, count in stats.category_counts.items():
                pct = count / total * 100
                w(f'| {CATEGORY_LABELS.get(cat, cat)} | {count} | {pct:.1f}% |\n')
            w('\n')

        if include_tree:
            w('## 🌲 Sơ đồ cây thư mục\n\n```text\n')
            w(build_ascii_tree([f.path for f in files]))
            w('\n```\n\n')

        if include_toc:
            w('<a id="table-of-contents"></a>\n## 📑 Mục lục tài liệu\n\n')
            for idx, item in enumerate(files, 1):
                icon = CATEGORY_ICONS.get(item.category, '⚙️')
                w(f'{idx}. [{icon} `{item.path}`](#{create_anchor_slug(item.path)}) '
                  f'*({format_bytes(item.size)}, {item.lines_count:,} dòng, ~{item.token_estimate:,} tokens)*\n')
            w('\n---\n\n')

        w('## 📂 Nội dung chi tiết các tệp\n\n')

        for index, item in enumerate(files, 1):
            anchor = create_anchor_slug(item.path)
            w(f'<a id="{anchor}"></a>\n')
            w(f'### {index}. `{item.path}`\n\n')
            if include_metadata:
                ocr_badge = ' · ✨ **Đã quét OCR AI**' if item.ocr_status == 'success' else ''
                origin = f' · **Nguồn:** `{item.archive_origin}`' if item.archive_origin else ''
                w(
                    f'> **Loại:** `{item.category.upper()}` ({item.language}) · **Dung lượng:** '
                    f'{format_bytes(item.size)} · **Số dòng:** {item.lines_count:,} · '
                    f'**Tokens:** ~{item.token_estimate:,}{origin}{ocr_badge}\n\n'
                )
            w(file_body_markdown(item))
            w('\n\n[⬆ Về đầu trang](#top) · [📑 Mục lục](#table-of-contents)\n\n---\n\n')

            if release_content:
                item.raw_content = ""
                item.markdown_content = ""

            if progress_cb:
                progress_cb(index, total_files, item.name)

        return written

    if hasattr(dest, 'write'):
        return _write_content(dest)
    target_path = Path(dest)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, 'w', encoding='utf-8', buffering=1024*1024) as f:
        return _write_content(f)


def build_combined_markdown(files: list[ExtractedFile], stats: ExtractionStats,
                            archive_name: str = 'archive',
                            include_toc: bool = True,
                            include_tree: bool = True,
                            include_stats: bool = True,
                            include_metadata: bool = True) -> str:
    buf = io.StringIO()
    stream_write_combined_markdown(
        buf, files, stats, archive_name=archive_name,
        include_toc=include_toc, include_tree=include_tree,
        include_stats=include_stats, include_metadata=include_metadata,
        release_content=False,
    )
    return buf.getvalue()
