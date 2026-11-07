# ============================================================================
# markdown — Markdown document builders. Ported from markdownBuilder.ts:
# ascii tree, TOC, stats tables, combined master doc, individual .md files.
# ============================================================================
from datetime import datetime

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


def build_ascii_tree(paths: list[str]) -> str:
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

    def print_node(node: dict, prefix: str = '') -> None:
        keys = sorted_keys(node)
        for i, key in enumerate(keys):
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


def build_combined_markdown(files: list[ExtractedFile], stats: ExtractionStats,
                            archive_name: str = 'archive',
                            include_toc: bool = True,
                            include_tree: bool = True,
                            include_stats: bool = True,
                            include_metadata: bool = True) -> str:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    out: list[str] = []

    out.append(f'# 📦 Tổng hợp dữ liệu: `{archive_name}`')
    out.append('')
    out.append(f'> Tài liệu được tạo tự động bởi **Archive2MD** vào lúc **{now}**.')
    out.append('')

    if include_stats:
        out.append('## 📊 Thống kê tổng quan')
        out.append('')
        out.append('| Chỉ số | Chi tiết |')
        out.append('| :--- | :--- |')
        out.append(f'| **Tổng số tệp chuyển đổi** | **{stats.selected_count:,}** tệp (trên tổng {stats.total_files:,}) |')
        out.append(f'| **Tổng dung lượng văn bản** | **{format_bytes(stats.selected_size)}** |')
        out.append(f'| **Tổng số dòng mã / văn bản** | **{stats.selected_lines:,}** dòng |')
        out.append(f'| **Ước tính ngữ cảnh LLM** | **~{stats.selected_tokens:,}** tokens |')
        out.append('')
        out.append('### Phân loại theo định dạng')
        out.append('')
        out.append('| Danh mục | Số lượng | Tỷ lệ |')
        out.append('| :--- | :--- | :--- |')
        total = stats.selected_count or 1
        for cat, count in stats.category_counts.items():
            pct = count / total * 100
            out.append(f'| {CATEGORY_LABELS.get(cat, cat)} | {count} | {pct:.1f}% |')
        out.append('')

    if include_tree:
        out.append('## 🌲 Sơ đồ cây thư mục')
        out.append('')
        out.append('```text')
        out.append(build_ascii_tree([f.path for f in files]))
        out.append('```')
        out.append('')

    if include_toc:
        out.append('## 📑 Mục lục tài liệu')
        out.append('')
        for idx, f in enumerate(files, 1):
            icon = CATEGORY_ICONS.get(f.category, '⚙️')
            out.append(
                f'{idx}. [{icon} `{f.path}`](#{create_anchor_slug(f.path)}) '
                f'*({format_bytes(f.size)}, {f.lines_count:,} dòng, ~{f.token_estimate:,} tokens)*'
            )
        out.append('')
        out.append('---')
        out.append('')

    out.append('## 📂 Nội dung chi tiết các tệp')
    out.append('')

    for index, file in enumerate(files, 1):
        anchor = create_anchor_slug(file.path)
        out.append(f'<a id="{anchor}"></a>')
        out.append(f'### {index}. `{file.path}`')
        out.append('')
        if include_metadata:
            ocr_badge = ' · ✨ **Đã quét OCR AI**' if file.ocr_status == 'success' else ''
            origin = f' · **Nguồn:** `{file.archive_origin}`' if file.archive_origin else ''
            out.append(
                f'> **Loại:** `{file.category.upper()}` ({file.language}) · **Dung lượng:** '
                f'{format_bytes(file.size)} · **Số dòng:** {file.lines_count:,} · '
                f'**Tokens:** ~{file.token_estimate:,}{origin}{ocr_badge}'
            )
            out.append('')
        out.append(file_body_markdown(file))
        out.append('')
        out.append('[⬆ Về đầu trang](#-tổng-hợp-dữ-liệu-archive) · [📑 Mục lục](#-mục-lục-tài-liệu)')
        out.append('')
        out.append('---')
        out.append('')

    return '\n'.join(out)
