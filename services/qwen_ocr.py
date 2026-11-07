# ============================================================================
# services/qwen_ocr.py — Qwen2.5-VL local vision model with NVIDIA CUDA GPU offload.
# Runs in-process using llama-cpp-python with Qwen25VLChatHandler.
# Offloads model layers directly to NVIDIA GPU (GTX 1650, RTX series).
# ============================================================================
import base64
import io
from pathlib import Path
from typing import Optional

from .base import BackendUnavailable, OcrProvider, repo_root, setup_cuda_dlls

MODELS_DIR = repo_root() / 'models'
MODEL_FILE = MODELS_DIR / 'Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf'
MMPROJ_FILE = MODELS_DIR / 'mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf'

_llm_instance = None


def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        if not MODEL_FILE.exists():
            raise BackendUnavailable(f'[qwen] Khong tim thay model weights: {MODEL_FILE}')
        if not MMPROJ_FILE.exists():
            raise BackendUnavailable(f'[qwen] Khong tim thay vision projector: {MMPROJ_FILE}')

        setup_cuda_dlls()
        import llama_cpp
        from llama_cpp.llama_chat_format import Qwen25VLChatHandler

        chat_handler = Qwen25VLChatHandler(clip_model_path=str(MMPROJ_FILE))
        _llm_instance = llama_cpp.Llama(
            model_path=str(MODEL_FILE),
            chat_handler=chat_handler,
            n_gpu_layers=99,   # Toàn bộ layers đưa lên GPU NVIDIA
            n_ctx=4096,
            verbose=False,
        )
    return _llm_instance


def shutdown() -> None:
    """Free model resources."""
    global _llm_instance
    if _llm_instance is not None:
        try:
            del _llm_instance
        except Exception:
            pass
        _llm_instance = None


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
        llm = _get_llm()

        # Tối ưu kích thước ảnh (giữ nguyên độ nét, vừa vặn VRAM 4GB của GTX 1650)
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            if max(img.size) > 1120:
                img.thumbnail((1120, 1120), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                data = buf.getvalue()
                mime = 'image/png'
        except Exception:
            pass

        data_uri = f'data:{mime or "image/png"};base64,{base64.b64encode(data).decode("ascii")}'
        user_text = prompt or (
            'Ban la chuyen gia OCR tai lieu. Hay nhan dien va trich xuat toan bo chu viet, '
            'so lieu, ma nguon, bang bieu va de bai trong hinh anh nay thanh Markdown ro rang, day du.'
        )

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
        return markdown.strip() or '*(Khong phat hien van ban co the doc duoc)*'
