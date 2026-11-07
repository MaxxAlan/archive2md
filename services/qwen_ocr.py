# ============================================================================
# services/qwen_ocr.py — Qwen2.5-VL local vision model with NVIDIA CUDA GPU offload.
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
MODEL_FILE = MODELS_DIR / 'Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf'
MMPROJ_FILE = MODELS_DIR / 'mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf'

_llm_instance = None
_log_callback_ref = None


def _dummy_log(level, text, user_data):
    pass


def _get_llm():
    global _llm_instance, _log_callback_ref
    if _llm_instance is None:
        if not MODEL_FILE.exists():
            raise BackendUnavailable(f'[qwen] Khong tim thay model weights: {MODEL_FILE}')
        if not MMPROJ_FILE.exists():
            raise BackendUnavailable(f'[qwen] Khong tim thay vision projector: {MMPROJ_FILE}')

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
            clip_model_path=str(MMPROJ_FILE),
            verbose=False,
        )
        _llm_instance = Llama(
            model_path=str(MODEL_FILE),
            chat_handler=chat_handler,
            n_gpu_layers=99,   # Toàn bộ layers đưa lên GPU NVIDIA
            n_ctx=4096,
            verbose=False,
        )
    return _llm_instance


def shutdown() -> None:
    """Safe no-op on Windows to prevent C-level double-free crashes on exit."""
    pass


class QwenOcrProvider(OcrProvider):
    id = 'qwen2.5-vl'
    name = 'Qwen2.5-VL-3B (NVIDIA GPU)'

    def is_available(self) -> bool:
        if not MODEL_FILE.exists() or not MMPROJ_FILE.exists():
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

        # Chuẩn hóa và tối ưu kích thước ảnh (RGB JPEG, max 1120px)
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            if img.mode in ('RGBA', 'LA', 'P'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                mask = img.split()[-1] if len(img.split()) == 4 else None
                bg.paste(img, mask=mask)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            if max(img.size) > 1120:
                img.thumbnail((1120, 1120), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=95)
            data = buf.getvalue()
            mime = 'image/jpeg'
        except Exception as e:
            return f'*(Không thể đọc định dạng hình ảnh: {e})*'

        data_uri = f'data:{mime};base64,{base64.b64encode(data).decode("ascii")}'
        user_text = prompt or (
            'Ban la chuyen gia OCR tai lieu. Hay nhan dien va trich xuat toan bo chu viet, '
            'so lieu, ma nguon, bang bieu va de bai trong hinh anh nay thanh Markdown ro rang, day du.'
        )

        try:
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
                max_tokens=2048,
                temperature=0.1,
            )
            choices = res.get('choices') or [{}]
            markdown = choices[0].get('message', {}).get('content') or ''
            return markdown.strip() or '*(Không phát hiện văn bản có thể đọc được)*'
        except Exception as e:
            return f'*(Không thể nhận diện hình ảnh: {e})*'
