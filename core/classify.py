# ============================================================================
# Classification — file type mapping, junk detection, binary detection,
# auxiliary-file rules, token estimation. Ported from fileClassifier.ts.
# ============================================================================
import re
from typing import Optional

EXTENSION_MAP: dict[str, tuple[str, str, str]] = {
    # ext: (category, language, label)
    # --- Code & scripts ---
    'ts': ('code', 'typescript', 'TypeScript'),
    'tsx': ('code', 'tsx', 'React TypeScript'),
    'js': ('code', 'javascript', 'JavaScript'),
    'jsx': ('code', 'jsx', 'React JavaScript'),
    'mjs': ('code', 'javascript', 'JavaScript Module'),
    'cjs': ('code', 'javascript', 'CommonJS'),
    'py': ('code', 'python', 'Python'),
    'pyw': ('code', 'python', 'Python'),
    'java': ('code', 'java', 'Java'),
    'c': ('code', 'c', 'C'),
    'cpp': ('code', 'cpp', 'C++'),
    'cc': ('code', 'cpp', 'C++'),
    'cxx': ('code', 'cpp', 'C++'),
    'h': ('code', 'c', 'C Header'),
    'hpp': ('code', 'cpp', 'C++ Header'),
    'cs': ('code', 'csharp', 'C#'),
    'go': ('code', 'go', 'Go'),
    'rs': ('code', 'rust', 'Rust'),
    'php': ('code', 'php', 'PHP'),
    'rb': ('code', 'ruby', 'Ruby'),
    'swift': ('code', 'swift', 'Swift'),
    'kt': ('code', 'kotlin', 'Kotlin'),
    'kts': ('code', 'kotlin', 'Kotlin Script'),
    'sh': ('code', 'bash', 'Shell Script'),
    'bash': ('code', 'bash', 'Bash Script'),
    'zsh': ('code', 'bash', 'Zsh Script'),
    'ps1': ('code', 'powershell', 'PowerShell'),
    'bat': ('code', 'batch', 'Batch File'),
    'cmd': ('code', 'batch', 'Batch File'),
    'html': ('code', 'html', 'HTML'),
    'htm': ('code', 'html', 'HTML'),
    'css': ('code', 'css', 'CSS'),
    'scss': ('code', 'scss', 'Sass / SCSS'),
    'sass': ('code', 'sass', 'Sass'),
    'less': ('code', 'less', 'Less'),
    'vue': ('code', 'vue', 'Vue Component'),
    'svelte': ('code', 'svelte', 'Svelte Component'),
    'astro': ('code', 'astro', 'Astro Component'),
    'lua': ('code', 'lua', 'Lua'),
    'r': ('code', 'r', 'R Script'),
    'dart': ('code', 'dart', 'Dart'),
    'scala': ('code', 'scala', 'Scala'),
    'proto': ('code', 'protobuf', 'Protobuf'),
    'sol': ('code', 'solidity', 'Solidity'),
    'jsp': ('code', 'jsp', 'Java Server Page (JSP)'),
    'jspf': ('code', 'jsp', 'JSP Fragment'),

    # --- Database & SQL ---
    'sql': ('database', 'sql', 'SQL Script / Schema'),
    'ddl': ('database', 'sql', 'SQL DDL'),
    'dml': ('database', 'sql', 'SQL DML'),
    'dump': ('database', 'sql', 'Database Dump'),
    'prisma': ('database', 'prisma', 'Prisma Schema'),
    'graphql': ('database', 'graphql', 'GraphQL Schema'),
    'gql': ('database', 'graphql', 'GraphQL'),

    # --- Documents ---
    'pdf': ('document', 'markdown', 'Tài liệu PDF'),
    'docx': ('document', 'markdown', 'Tài liệu Word (DOCX)'),
    'doc': ('document', 'markdown', 'Tài liệu Word (DOC)'),
    'txt': ('document', 'text', 'Văn bản thuần'),
    'md': ('document', 'markdown', 'Tài liệu Markdown'),
    'markdown': ('document', 'markdown', 'Tài liệu Markdown'),
    'rtf': ('document', 'text', 'Rich Text Format'),
    'log': ('document', 'text', 'Nhật ký Log'),

    # --- Spreadsheets ---
    'xlsx': ('spreadsheet', 'markdown', 'Bảng tính Excel (XLSX)'),
    'xls': ('spreadsheet', 'markdown', 'Bảng tính Excel (XLS)'),
    'csv': ('spreadsheet', 'markdown', 'Dữ liệu CSV'),
    'tsv': ('spreadsheet', 'markdown', 'Dữ liệu TSV'),

    # --- Config & data ---
    'json': ('config', 'json', 'JSON Data'),
    'jsonc': ('config', 'json', 'JSON with Comments'),
    'yaml': ('config', 'yaml', 'YAML Config'),
    'yml': ('config', 'yaml', 'YAML Config'),
    'xml': ('config', 'xml', 'XML Document'),
    'toml': ('config', 'toml', 'TOML Config'),
    'ini': ('config', 'ini', 'INI Settings'),
    'env': ('config', 'bash', 'Environment Variables'),
    'properties': ('config', 'properties', 'Properties'),
    'conf': ('config', 'ini', 'Config File'),
    'gitignore': ('config', 'gitignore', 'Git Ignore'),
    'tld': ('config', 'xml', 'Tag Library Descriptor'),
    'xsd': ('config', 'xml', 'XML Schema'),

    # --- Archives (nested, unpacked by intake) ---
    'zip': ('archive', 'archive', 'File nén ZIP'),
    'war': ('archive', 'archive', 'File nén Web Archive (WAR)'),
    'jar': ('archive', 'archive', 'File nén Java Archive (JAR)'),
    'rar': ('archive', 'archive', 'File nén RAR'),
    '7z': ('archive', 'archive', 'File nén 7-Zip'),
    'tar': ('archive', 'archive', 'File nén TAR'),
    'gz': ('archive', 'archive', 'File nén GZIP'),
    'tgz': ('archive', 'archive', 'File nén TGZ'),
    'bz2': ('archive', 'archive', 'File nén BZIP2'),
    'xz': ('archive', 'archive', 'File nén XZ'),

    # --- Media ---
    'svg': ('media', 'xml', 'Ảnh SVG Vector'),
    'png': ('media', 'image', 'Ảnh PNG'),
    'jpg': ('media', 'image', 'Ảnh JPEG'),
    'jpeg': ('media', 'image', 'Ảnh JPEG'),
    'webp': ('media', 'image', 'Ảnh WebP'),
    'gif': ('media', 'image', 'Ảnh GIF'),
}

BINARY_EXTENSIONS = frozenset({
    'exe', 'dll', 'so', 'dylib', 'bin', 'dat', 'o', 'a', 'lib', 'class',
    'pyc', 'pyo', 'pyd', 'jar', 'war', 'ear', 'iso', 'img', 'dmg',
    'mp3', 'mp4', 'mov', 'avi', 'mkv', 'flac', 'wav', 'woff', 'woff2',
    'ttf', 'otf', 'eot', 'ico', 'cur', 'pak', 'apk', 'ipa', 'pdf',
})

JUNK_PATH_PATTERNS = [
    r'(^|/)__MACOSX/', r'(^|/)\.DS_Store$', r'(^|/)Thumbs\.db$',
    r'(^|/)node_modules/', r'(^|/)\.git/', r'(^|/)\.svn/', r'(^|/)\.hg/',
    r'(^|/)venv/', r'(^|/)\.venv/', r'(^|/)(env)/', r'(^|/)__pycache__/',
    r'(^|/)\.idea/', r'(^|/)\.vscode/', r'(^|/)target/', r'(^|/)\.netbeans_',
    r'(^|/)package-lock\.json$', r'(^|/)pnpm-lock\.yaml$', r'(^|/)yarn\.lock$',
    r'(^|/)composer\.lock$', r'(^|/)Cargo\.lock$', r'(^|/)bun\.lock$',
]
JUNK_COMPILED = [re.compile(p, re.IGNORECASE) for p in JUNK_PATH_PATTERNS]

# Media/image extensions eligible for multimodal OCR (SVG is text, skip it)
OCR_EXTENSIONS = frozenset({'png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'tiff', 'tif', 'pdf'})

# Raster image mime types
MIME_MAP = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'webp': 'image/webp', 'gif': 'image/gif', 'bmp': 'image/bmp',
    'svg': 'image/svg+xml', 'pdf': 'application/pdf',
}


def get_extension(filename: str) -> str:
    clean = filename.split('?')[0].split('#')[0]
    parts = clean.rsplit('.', 1)
    if len(parts) <= 1:
        base = clean.rsplit('/', 1)[-1].lower()
        return '' if base in ('dockerfile', 'makefile', 'license', 'readme') else ''
    return parts[-1].lower()


def classify_file(file_path: str) -> dict:
    """Return {category, language, label, is_binary, is_junk} for a path."""
    norm = file_path.replace('\\', '/')
    ext = get_extension(norm)

    is_junk_path = any(p.search(norm.lower()) for p in JUNK_COMPILED)
    is_binary_ext = ext in BINARY_EXTENSIONS and ext not in OCR_EXTENSIONS

    if ext in EXTENSION_MAP:
        category, language, label = EXTENSION_MAP[ext]
        return {
            'category': category, 'language': language, 'label': label,
            'is_binary': is_binary_ext, 'is_junk': is_junk_path,
        }

    basename = norm.rsplit('/', 1)[-1].lower()
    if basename == 'dockerfile':
        return {'category': 'config', 'language': 'dockerfile', 'label': 'Dockerfile', 'is_binary': False, 'is_junk': is_junk_path}
    if basename == 'makefile':
        return {'category': 'code', 'language': 'makefile', 'label': 'Makefile', 'is_binary': False, 'is_junk': is_junk_path}
    if basename in ('license', 'readme'):
        return {'category': 'document', 'language': 'markdown', 'label': 'Tài liệu', 'is_binary': False, 'is_junk': is_junk_path}

    return {
        'category': 'other' if is_binary_ext else 'document',
        'language': 'binary' if is_binary_ext else 'text',
        'label': f'File .{ext.upper()}' if ext else 'Tập tin',
        'is_binary': is_binary_ext,
        'is_junk': is_junk_path or is_binary_ext,
    }


def check_is_auxiliary(file_path: str, extension: str) -> tuple[bool, Optional[str]]:
    """(is_auxiliary, reason) — fonts, bytecode, IDE metadata, system binaries."""
    norm = file_path.replace('\\', '/').lower()
    ext = extension.lower()

    if ext == 'class':
        return True, 'Bytecode Java (.class)'
    if ext in ('eot', 'woff', 'woff2', 'ttf', 'otf'):
        return True, 'Font chữ web'
    if '.netbeans_' in norm or norm.endswith('.ds_store') or norm.endswith('thumbs.db'):
        return True, 'Metadata IDE/Hệ thống'
    if ext == 'jar' and ('/lib/' in norm or 'web-inf/lib' in norm):
        return True, 'Thư viện JAR phụ thuộc'
    if ext in ('exe', 'dll', 'so', 'dylib', 'bin', 'o', 'obj', 'pyc'):
        return True, 'Tệp nhị phân hệ thống'
    return False, None


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return -(-len(text) // 4)  # ceil; ~4 chars/token for mixed code+prose


def format_bytes(num: float) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(num) < 1024 or unit == 'GB':
            return f'{num:.1f} {unit}' if unit != 'B' else f'{int(num)} B'
        num /= 1024
    return f'{num:.1f} GB'


def detect_mime(extension: str) -> str:
    return MIME_MAP.get(extension.lower(), 'application/octet-stream')


def is_ocr_candidate(extension: str, category: Optional[str] = None) -> bool:
    ext = extension.lower()
    if ext == 'pdf':
        return True
    if category == 'media' and ext != 'svg':
        return True
    return ext in OCR_EXTENSIONS
