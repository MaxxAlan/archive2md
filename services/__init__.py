# ============================================================================
# services package — Converters, OCR providers, and registry.
# ============================================================================
from .base import (
    STANDARD_CACHE_SUBDIRS,
    BackendUnavailable,
    ConversionError,
    DocumentConverter,
    OcrProvider,
    get_cache_dir,
    get_cache_stats,
    init_cache_system,
    purge_stale_cache,
    repo_root,
    setup_cuda_dlls,
)
from .registry import bootstrap, registry

__all__ = [
    'STANDARD_CACHE_SUBDIRS',
    'BackendUnavailable',
    'ConversionError',
    'DocumentConverter',
    'OcrProvider',
    'bootstrap',
    'get_cache_dir',
    'get_cache_stats',
    'init_cache_system',
    'purge_stale_cache',
    'registry',
    'repo_root',
    'setup_cuda_dlls',
]
