# ============================================================================
# services/markitdown.py — Microsoft MarkItDown converter.
# Converts docx, pptx, xlsx, pdf, html, csv, xml, and many other formats.
# Runs in-process using the active virtual environment for maximum speed.
# ============================================================================
import io
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from .base import ConversionError, DocumentConverter, get_cache_dir, suppress_c_output

EXTENSIONS = (
    'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls',
    'html', 'htm', 'epub', 'msg', 'eml', 'rtf',
    'odt', 'ods', 'odp', 'csv', 'tsv', 'xml', 'pdf',
)

_markitdown_instance = None


def _get_converter():
    global _markitdown_instance
    if _markitdown_instance is None:
        try:
            from markitdown import MarkItDown
            _markitdown_instance = MarkItDown()
        except ImportError:
            _markitdown_instance = False
    return _markitdown_instance


class MarkItDownConverter(DocumentConverter):
    id = 'markitdown'
    name = 'Microsoft MarkItDown'
    extensions = EXTENSIONS
    priority = 10

    def is_available(self) -> bool:
        conv = _get_converter()
        return bool(conv)

    def convert(self, file_name: str, data: bytes) -> str:
        conv = _get_converter()
        if not conv:
            raise ConversionError('[markitdown] Thu vien markitdown chua duoc cai dat.')

        ext = Path(file_name).suffix.lstrip('.').lower() or 'bin'
        cache_tmp = get_cache_dir('tmp')
        tmp_dir = Path(tempfile.mkdtemp(prefix=f'mid-{ext}-', dir=str(cache_tmp)))
        tmp_file = tmp_dir / f'input.{ext}'

        try:
            tmp_file.write_bytes(data)
            with suppress_c_output():
                result = conv.convert(str(tmp_file))
            markdown = (result.text_content or '').strip()
            if not markdown:
                raise ConversionError(f'MarkItDown khong trich xuat duoc noi dung tu {file_name}')
            return markdown
        except Exception as e:
            if isinstance(e, ConversionError):
                raise
            raise ConversionError(f'[markitdown] Loi xu ly file {file_name}: {e}') from e
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
