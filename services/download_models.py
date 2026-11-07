# ============================================================================
# services/download_models.py — Automated Vision OCR Model Downloader.
# Downloads Qwen2.5-VL-3B GGUF weights & vision projector from Hugging Face.
# Features chunked streaming, resume support (HTTP Range), and visual progress.
# ============================================================================
import argparse
import os
import sys
import time
from pathlib import Path

from services.base import init_cache_system, repo_root

init_cache_system()

MODELS_DIR = repo_root() / 'models'

# Official Hugging Face repository and model files
HF_REPO = 'Qwen/Qwen2.5-VL-3B-Instruct-GGUF'
MODELS = {
    'Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf': {
        'url': f'https://huggingface.co/{HF_REPO}/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf',
        'desc': 'Text backbone & language model (Q4_K_M)',
        'min_size': 1_800_000_000,   # ~1.93 GB
    },
    'mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf': {
        'url': f'https://huggingface.co/{HF_REPO}/resolve/main/mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf',
        'desc': 'Multimodal vision projector (Q8_0)',
        'min_size': 800_000_000,     # ~845 MB
    },
}


def check_models_present() -> bool:
    """Return True if all required GGUF model files exist and meet minimum size."""
    for filename, info in MODELS.items():
        path = MODELS_DIR / filename
        if not path.exists() or path.stat().st_size < info['min_size']:
            return False
    return True


def format_bytes(n: float) -> str:
    """Convert bytes to human-readable string (MB, GB)."""
    if n >= 1024 ** 3:
        return f'{n / (1024 ** 3):.2f} GB'
    if n >= 1024 ** 2:
        return f'{n / (1024 ** 2):.1f} MB'
    if n >= 1024:
        return f'{n / 1024:.1f} KB'
    return f'{n:.0f} B'


def download_file_with_resume(url: str, dest_path: Path, desc: str) -> bool:
    """Download a file with HTTP Range resume support and a visual progress bar."""
    import requests

    part_path = dest_path.with_suffix(dest_path.suffix + '.part')
    initial_bytes = part_path.stat().st_size if part_path.exists() else 0

    headers = {}
    if initial_bytes > 0:
        headers['Range'] = f'bytes={initial_bytes}-'

    print(f"\n[*] Đang kết nối tới Hugging Face...")
    print(f"    Tệp: {dest_path.name}")
    print(f"    Mô tả: {desc}")

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
    except Exception as e:
        print(f"[!] Lỗi kết nối tải file: {e}")
        return False

    if response.status_code == 416:
        # Range not satisfiable -> file already completely downloaded
        initial_bytes = 0
        part_path.unlink(missing_ok=True)
        response = requests.get(url, stream=True, timeout=30)

    if response.status_code not in (200, 206):
        print(f"[!] Máy chủ trả về mã lỗi HTTP {response.status_code}")
        return False

    content_range = response.headers.get('Content-Range')
    if content_range and '/' in content_range:
        total_size = int(content_range.split('/')[-1])
    else:
        total_size = int(response.headers.get('Content-Length', 0)) + initial_bytes

    mode = 'ab' if (response.status_code == 206 and initial_bytes > 0) else 'wb'
    if mode == 'wb':
        initial_bytes = 0

    current_bytes = initial_bytes
    chunk_size = 1024 * 1024  # 1MB buffer
    start_time = time.time()
    last_ui_update = 0

    with open(part_path, mode) as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                current_bytes += len(chunk)
                now = time.time()

                if now - last_ui_update > 0.2 or current_bytes == total_size:
                    last_ui_update = now
                    elapsed = now - start_time
                    speed = (current_bytes - initial_bytes) / elapsed if elapsed > 0 else 0
                    pct = (current_bytes / total_size * 100) if total_size > 0 else 0

                    bar_len = 30
                    filled = int(bar_len * current_bytes / total_size) if total_size > 0 else 0
                    bar = '█' * filled + '░' * (bar_len - filled)

                    eta_sec = (total_size - current_bytes) / speed if speed > 0 else 0
                    eta_str = f"{int(eta_sec // 60)}m {int(eta_sec % 60):02d}s" if eta_sec > 0 else "--:--"

                    speed_str = f"{format_bytes(speed)}/s"
                    downloaded_str = f"{format_bytes(current_bytes)} / {format_bytes(total_size)}"

                    sys.stdout.write(
                        f"\r    [{bar}] {pct:5.1f}% | {downloaded_str} | {speed_str} | Còn lại: {eta_str}   "
                    )
                    sys.stdout.flush()

    sys.stdout.write('\n')
    part_path.rename(dest_path)
    print(f"    ✓ Đã tải thành công: {dest_path.name}")
    return True


def ensure_models(interactive: bool = True, force: bool = False) -> bool:
    """Check for models and download if missing."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    missing = []
    for filename, info in MODELS.items():
        path = MODELS_DIR / filename
        if force or not path.exists() or path.stat().st_size < info['min_size']:
            missing.append((filename, info))

    if not missing:
        print("[*] Toàn bộ file mô hình Vision OCR (Qwen2.5-VL-3B) đã có sẵn trong models/.")
        return True

    print("\n" + "=" * 70)
    print("        Archive2MD — Trình Tải Mô Hình Vision AI (Qwen2.5-VL-3B)")
    print("=" * 70)
    print("Phát hiện chưa có các tệp mô hình GGUF sau trong thư mục models/:")
    for fname, info in missing:
        print(f"  - {fname:<42} ({info['desc']})")
    print("\nTổng dung lượng cần tải: ~2.75 GB từ Hugging Face.")
    print("Mô hình này cho phép tự động nhận diện chữ, bảng biểu, đề bài trong ảnh")
    print("và chạy trực tiếp trên GPU NVIDIA (CUDA) với tốc độ cao.")

    if interactive:
        try:
            choice = input("\nBạn có muốn tự động tải về ngay bây giờ không? [Y/n]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nĐã hủy tải mô hình.")
            return False
        if choice in ('n', 'no', 'khong', 'k'):
            print("[!] Bỏ qua tải mô hình. Tool vẫn sẽ chuyển đổi tài liệu văn phòng bình thường")
            print("    nhưng chức năng Vision OCR sẽ tạm thời không khả dụng.")
            return False

    success = True
    for fname, info in missing:
        target = MODELS_DIR / fname
        ok = download_file_with_resume(info['url'], target, info['desc'])
        if not ok:
            success = False
            print(f"[!] Thất bại khi tải {fname}. Bạn có thể chạy lại để tiếp tục tải tiếp (hỗ trợ Resume).")
            break

    if success:
        print("\n[✓] Hoàn tất tải toàn bộ mô hình Vision OCR!")
    return success


def main() -> int:
    parser = argparse.ArgumentParser(description="Tải mô hình Vision AI Qwen2.5-VL-3B cho Archive2MD")
    parser.add_argument('--check', action='store_true', help="Chỉ kiểm tra mô hình đã đủ chưa (0=đủ, 1=thiếu)")
    parser.add_argument('--auto', '-y', '--yes', action='store_true', help="Tự động tải không cần hỏi xác nhận")
    parser.add_argument('--force', action='store_true', help="Tải lại ngay cả khi file đã tồn tại")
    args = parser.parse_args()

    if args.check:
        if check_models_present():
            print("Models OK")
            return 0
        print("Models MISSING")
        return 1

    ok = ensure_models(interactive=not args.auto, force=args.force)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
