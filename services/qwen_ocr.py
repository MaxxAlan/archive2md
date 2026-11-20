# ============================================================================
# services/qwen_ocr.py — Backward compatibility alias for MinerUOcrProvider.
# Automatically redirects to services.mineru_ocr.
# ============================================================================
from .mineru_ocr import MinerUOcrProvider, _get_llm, _resolve_model_files, shutdown

# Backward compatibility alias
QwenOcrProvider = MinerUOcrProvider

__all__ = ['MinerUOcrProvider', 'QwenOcrProvider', '_get_llm', 'shutdown']
