# ============================================================================
# services/mineru_ocr.py — MinerU2.5-Pro local vision model with NVIDIA CUDA GPU offload.
# Architecture: Qwen2-VL specialized for document parsing, tables, and formula extraction.
# Runs in-process using llama-cpp-python with Qwen25VLChatHandler.
# Offloads model layers directly to NVIDIA GPU (GTX 1650, RTX series).
# ============================================================================
import base64
import io
import sys
from pathlib import Path
from typing import Optional

# Globally silence any unraisable C/Python GC warnings on Windows
sys.unraisablehook = lambda u: None

from .base import BackendUnavailable, OcrProvider, repo_root, setup_cuda_dlls, suppress_c_output

MODELS_DIR = repo_root() / 'models'

# MinerU2.5-Pro-2604-1.2B GGUF weights & multimodal projector
MODEL_FILE = MODELS_DIR / 'MinerU2.5-Pro-2604-1.2B.Q4_K_M.gguf'
MMPROJ_FILE = MODELS_DIR / 'MinerU2.5-Pro-2604-1.2B.mmproj-Q8_0.gguf'

# Fallback to legacy Qwen2.5-VL if user has not yet downloaded MinerU
LEGACY_MODEL_FILE = MODELS_DIR / 'Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf'
LEGACY_MMPROJ_FILE = MODELS_DIR / 'mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf'

_llm_instance = None
_active_model_name = None
_log_callback_ref = None


def _dummy_log(level, text, user_data):
    pass


def _resolve_model_files() -> tuple[Optional[Path], Optional[Path], Optional[str]]:
    """Resolve active model weights. Prioritize MinerU2.5-Pro, fallback to legacy Qwen."""
    if MODEL_FILE.exists() and MMPROJ_FILE.exists():
        return MODEL_FILE, MMPROJ_FILE, 'MinerU2.5-Pro-1.2B'
    if LEGACY_MODEL_FILE.exists() and LEGACY_MMPROJ_FILE.exists():
        return LEGACY_MODEL_FILE, LEGACY_MMPROJ_FILE, 'Qwen2.5-VL-3B (Legacy)'
    return None, None, None


def _get_llm():
    global _llm_instance, _active_model_name, _log_callback_ref
    if _llm_instance is None:
        model_path, mmproj_path, model_name = _resolve_model_files()
        if not model_path or not mmproj_path:
            raise BackendUnavailable(
                f'[mineru] Không tìm thấy model weights trong {MODELS_DIR}. '
                f'Vui lòng chạy: python cli.py --download-models'
            )

        setup_cuda_dlls()
        import llama_cpp
        from llama_cpp import Llama
        from llama_cpp._internals import LlamaModel, LlamaContext
        import llama_cpp.mtmd_cpp as mtmd_cpp
        from llama_cpp.llama_chat_format import Qwen25VLChatHandler

        # Permanently neutralize crashy C++ destructors on Windows CUDA
        try:
            Llama.__del__ = lambda self: None
            LlamaModel.__del__ = lambda self: None
            LlamaContext.__del__ = lambda self: None
        except Exception:
            pass

        # Disable low-level C logs from llama.cpp & mtmd.dll with persistent callback reference
        try:
            _log_callback_ref = llama_cpp.llama_log_callback(_dummy_log)
            llama_cpp.llama_log_set(_log_callback_ref, None)
            if hasattr(mtmd_cpp, 'mtmd_log_set'):
                mtmd_cpp.mtmd_log_set(_log_callback_ref, None)
            if hasattr(mtmd_cpp, 'mtmd_helper_log_set'):
                mtmd_cpp.mtmd_helper_log_set(_log_callback_ref, None)
        except Exception:
            pass

        chat_handler = Qwen25VLChatHandler(
            clip_model_path=str(mmproj_path),
            verbose=False,
        )

        _llm_instance = Llama(
            model_path=str(model_path),
            chat_handler=chat_handler,
            n_gpu_layers=99,   # Toàn bộ layers đưa lên GPU NVIDIA
            n_ctx=2048,
            verbose=False,
        )
        _active_model_name = model_name

    return _llm_instance


def shutdown() -> None:
    """Safe no-op on Windows to prevent C-level double-free crashes on exit."""
    pass


class MinerUOcrProvider(OcrProvider):
    id = 'mineru-vl'
    name = 'MinerU2.5-Pro-1.2B (NVIDIA GPU)'

    def is_available(self) -> bool:
        model_path, mmproj_path, _ = _resolve_model_files()
        if not model_path or not mmproj_path:
            return False
        try:
            setup_cuda_dlls()
            import llama_cpp  # noqa: F401
            return True
        except Exception:
            return False

    def ocr(self, data: bytes, mime: str, file_name: Optional[str] = None,
            prompt: Optional[str] = None) -> str:
        # Xử lý trường hợp tài liệu PDF chuyển qua OCR
        if data.startswith(b'%PDF'):
            try:
                import pdfminer.high_level
                text = pdfminer.high_level.extract_text(io.BytesIO(data))
                if text and text.strip():
                    return text.strip()
            except Exception:
                pass
            return '*(Tài liệu PDF dạng quét hình ảnh: không thể trích xuất nội dung)*'

        llm = _get_llm()

        # Chuẩn hóa và tối ưu kích thước ảnh (RGB JPEG, max 896px chuẩn Qwen2-VL patch)
        try:
            from PIL import Image, ImageStat
            img = Image.open(io.BytesIO(data))
            w, h = img.size
            if w < 32 or h < 32:
                return '*(Kích thước ảnh quá nhỏ, bỏ qua OCR)*'

            if img.mode in ('RGBA', 'LA', 'P'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                channels = img.split()
                mask = channels[-1] if len(channels) == 4 else None
                bg.paste(img, mask=mask)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Bỏ qua ảnh đơn sắc / rỗng (không chứa chữ)
            stat = ImageStat.Stat(img)
            if max(stat.var) < 2.0:
                return '*(Hình ảnh trống hoặc đơn sắc, không có văn bản)*'

            # Kích thước tối ưu 896px: vừa sắc nét cho chữ nhỏ, vừa tiết kiệm VRAM và tăng tốc encode GPU
            if max(img.size) > 896:
                img.thumbnail((896, 896), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=88)
            data = buf.getvalue()
            mime = 'image/jpeg'
        except Exception as e:
            return f'*(Không thể đọc định dạng hình ảnh: {e})*'

        data_uri = f'data:{mime};base64,{base64.b64encode(data).decode("ascii")}'
        # Prompt chuẩn của mô hình MinerU2.5-Pro: "\nText Recognition:"
        user_text = prompt or '\nText Recognition:'

        try:
            with suppress_c_output():
                res = llm.create_chat_completion(
                    messages=[
                        {
                            'role': 'user',
                            'content': [
                                {'type': 'image_url', 'image_url': {'url': data_uri}},
                                {'type': 'text', 'text': user_text},
                            ],
                        }
                    ],
                    max_tokens=1024,
                    temperature=0.0,
                )
            choices = res.get('choices') or [{}]
            markdown = choices[0].get('message', {}).get('content') or ''
            return markdown.strip() or '*(Không phát hiện văn bản có thể đọc được)*'
        except Exception as e:
            return f'*(Không thể nhận diện hình ảnh: {e})*'
