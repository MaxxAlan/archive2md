# ============================================================================
# services/docling.py — IBM Docling converter.
# Advanced layout & document analysis. Optional backend.
# ============================================================================
import shutil
import tempfile
from pathlib import Path

from .base import ConversionError, DocumentConverter, get_cache_dir

EXTENSIONS = (
    'pdf', 'docx', 'pptx', 'xlsx', 'html', 'htm',
    'csv', 'tsv', 'rtf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff',
)

_docling_available = None


def _check_docling():
    global _docling_available
    if _docling_available is None:
        try:
            import docling  # noqa: F401
            _docling_available = True
        except ImportError:
            _docling_available = False
    return _docling_available


class DoclingConverter(DocumentConverter):
    id = 'docling'
    name = 'IBM Docling'
    extensions = EXTENSIONS
    priority = 20

    def is_available(self) -> bool:
        return _check_docling()

    def convert(self, file_name: str, data: bytes) -> str:
        if not self.is_available():
            raise ConversionError('[docling] Docling chua duoc cai dat.')

        from docling.document_converter import DocumentConverter as DlConverter

        ext = Path(file_name).suffix.lstrip('.').lower() or 'bin'
        cache_tmp = get_cache_dir('tmp')
        tmp_dir = Path(tempfile.mkdtemp(prefix=f'dl-{ext}-', dir=str(cache_tmp)))
        tmp_file = tmp_dir / f'input.{ext}'

        try:
            tmp_file.write_bytes(data)
            conv = DlConverter()
            result = conv.convert(str(tmp_file))
            markdown = result.document.export_to_markdown().strip()
            if not markdown:
                raise ConversionError(f'Docling khong trich xuat duoc noi dung tu {file_name}')
            return markdown
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
