# ============================================================================
# services/registry.py — Service locator for converters & OCR providers.
# ============================================================================
from typing import Optional

from .base import DocumentConverter, OcrProvider


class Registry:
    def __init__(self) -> None:
        self._converters: list[DocumentConverter] = []
        self._ocr_providers: list[OcrProvider] = []

    # ---- registration -----------------------------------------------------
    def register_converter(self, converter: DocumentConverter) -> None:
        if any(c.id == converter.id for c in self._converters):
            return
        self._converters.append(converter)
        self._converters.sort(key=lambda c: -c.priority)

    def register_ocr_provider(self, provider: OcrProvider) -> None:
        if any(p.id == provider.id for p in self._ocr_providers):
            return
        self._ocr_providers.append(provider)

    # ---- resolution -------------------------------------------------------
    def converter_for(self, extension: str) -> Optional[DocumentConverter]:
        ext = extension.lower().lstrip('.')
        for c in self._converters:
            if ext in c.extensions and c.is_available():
                return c
        return None

    def ocr_provider(self) -> Optional[OcrProvider]:
        for p in self._ocr_providers:
            if p.is_available():
                return p
        return None

    # ---- high-level operations ---------------------------------------------
    def convert(self, file_name: str, data: bytes) -> Optional[tuple[str, str]]:
        """Route a file through available matching converters in priority order.
        Falls back to next converter if one fails.
        Returns (markdown, converter_id) or None when nothing claims the ext."""
        ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
        last_error = None
        for c in self._converters:
            if ext in c.extensions and c.is_available():
                try:
                    return c.convert(file_name, data), c.id
                except Exception as e:
                    last_error = e
                    continue
        if last_error:
            raise last_error
        return None

    def ocr(self, data: bytes, mime: str, file_name: Optional[str] = None,
            prompt: Optional[str] = None) -> Optional[str]:
        provider = self.ocr_provider()
        if provider is None:
            return None
        return provider.ocr(data, mime, file_name, prompt)

    # ---- introspection ------------------------------------------------------
    def status(self) -> list[dict]:
        out = []
        for c in self._converters:
            out.append({
                'kind': 'converter',
                'id': c.id,
                'name': c.name,
                'available': c.is_available(),
                'priority': c.priority,
                'extensions': list(c.extensions),
            })
        for p in self._ocr_providers:
            out.append({
                'kind': 'ocr',
                'id': p.id,
                'name': p.name,
                'available': p.is_available(),
            })
        return out


registry = Registry()


def bootstrap() -> None:
    """Register built-in backends."""
    from .docling import DoclingConverter
    from .markitdown import MarkItDownConverter
    from .qwen_ocr import QwenOcrProvider

    registry.register_converter(DoclingConverter())
    registry.register_converter(MarkItDownConverter())
    registry.register_ocr_provider(QwenOcrProvider())
