#!/usr/bin/env python
# ============================================================================
# cli.py — Archive2MD command line interface.
#
# Usage (python o day la venv cua core — xem setup.ps1):
#   python cli.py <input.zip|input.7z|input.rar|input.tar|folder> [options]
#
# Examples:
#   python cli.py project.zip -o out
#   python cli.py project.zip --mode both --ocr -o out
#   python cli.py . --status
#   python cli.py project.zip --research
# ============================================================================
import argparse
import os
import sys
import time
import warnings
from pathlib import Path

# Silence third-party deprecation & parsing warnings to preserve pristine UI
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Initialize centralized cache management early (routes bytecode into cache/pycache for fast startup)
from services.base import get_cache_stats, init_cache_system
init_cache_system()

from core.ui import ANSI, init_terminal, print_banner, print_stage, print_summary


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines, no quotes handling needed here)."""
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def cmd_status() -> int:
    from services import bootstrap, registry
    bootstrap()
    print()
    print(f"{ANSI.BOLD}{ANSI.B_CYAN}{'KIND':<12} {'ID':<14} {'NAME':<30} {'TRẠNG THÁI':<14} EXTENSIONS{ANSI.RESET}")
    print(f"{ANSI.GRAY}{'─' * 80}{ANSI.RESET}")
    for s in registry.status():
        ext = ','.join(s.get('extensions', [])) if s.get('extensions') else ''
        avail = s['available']
        status_disp = f"{ANSI.B_GREEN}● SẴN SÀNG{ANSI.RESET} " if avail else f"{ANSI.GRAY}○ TÙY CHỌN{ANSI.RESET} "
        kind_styled = f"{ANSI.CYAN}{s['kind']:<12}{ANSI.RESET}"
        id_styled = f"{ANSI.B_WHITE}{s['id']:<14}{ANSI.RESET}"
        name_styled = f"{s['name']:<30}"
        print(f"{kind_styled} {id_styled} {name_styled} {status_disp:<22} {ANSI.GRAY}{ext}{ANSI.RESET}")
    print()

    print(f"{ANSI.BOLD}{ANSI.B_YELLOW}{'THƯ MỤC CACHE':<16} {'FILE':<8} {'DUNG LƯỢNG':<14} MỤC ĐÍCH & ĐIỀU HƯỚNG{ANSI.RESET}")
    print(f"{ANSI.GRAY}{'─' * 80}{ANSI.RESET}")
    cache_stats = get_cache_stats()
    for sub, info in cache_stats.items():
        sub_name = f"cache/{sub}/"
        size_str = f"{info['size_bytes'] / 1024:.1f} KB" if info['size_bytes'] > 0 else "0 KB"
        count_str = f"{info['file_count']}"
        desc = info['description']
        print(f"{ANSI.B_WHITE}{sub_name:<16}{ANSI.RESET} {ANSI.CYAN}{count_str:<8}{ANSI.RESET} {ANSI.GRAY}{size_str:<14}{ANSI.RESET} {ANSI.GRAY}{desc}{ANSI.RESET}")
    print()
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog='archive2md',
        description='Unpack archive/folder → convert docs → OCR (optional) → Markdown. Local Python, no Node.',
    )
    parser.add_argument('-i', '--input', dest='input_path', default=None,
                        help='Input: archive file (.zip/.rar/.7z/.tar/...) hoặc thư mục')
    parser.add_argument('input', nargs='?', help=argparse.SUPPRESS)  # positional alias
    parser.add_argument('-o', '--output', default='output', help='Thư mục xuất kết quả (mặc định: ./output)')
    parser.add_argument('--mode', choices=['combined', 'individual', 'both'], default='combined',
                        help='Kiểu xuất Markdown (mặc định: combined)')
    parser.add_argument('--onemd', '-onemd', '--one-md', dest='onemd', action='store_true',
                        help='Xuất 1 file Markdown tổng hợp duy nhất (tương đương --mode combined)')
    parser.add_argument('--no-ocr', '--skip-ocr', dest='no_ocr', action='store_true',
                        help='Tắt tự động OCR hình ảnh (mặc định: tự động OCR mọi ảnh)')
    parser.add_argument('--ocr', dest='force_ocr', action='store_true',
                        help='Bật OCR hình ảnh (mặc định đã tự động BẬT)')
    parser.add_argument('--ocr-limit', type=int, default=0, help='Giới hạn số file OCR (0 = tất cả)')
    parser.add_argument('--ocr-prompt', default=None, help='Prompt OCR tùy chỉnh')
    parser.add_argument('--max-depth', type=int, default=5, help='Chiều sâu giải nén tối đa (mặc định 5)')
    parser.add_argument('--include-junk', action='store_true', help='Giữ junk (node_modules, .git, lock files...)')
    parser.add_argument('--include-auxiliary', action='store_true', help='Giữ file phụ trợ (font, bytecode, dll...)')
    parser.add_argument('--research', action='store_true', help='Tạo báo cáo AI Research (Gemini, cần GEMINI_API_KEY)')
    parser.add_argument('--status', action='store_true', help='Hiển thị trạng thái các backend rồi thoát')
    parser.add_argument('--download-models', action='store_true',
                        help='Kiểm tra và tự động tải mô hình Vision AI Qwen2.5-VL-3B từ Hugging Face')
    parser.add_argument('--interactive', '-it', dest='interactive', action='store_true',
                        help='Chế độ hỏi đáp tương tác từng bước (Interactive Wizard)')
    args = parser.parse_args(argv)

    init_terminal()
    load_dotenv(Path(__file__).resolve().parent / '.env')

    if args.status:
        return cmd_status()

    if args.download_models:
        from services.download_models import ensure_models
        ok = ensure_models(interactive=True)
        return 0 if ok else 1

    interactive_mode = args.interactive
    input_arg = args.input_path or args.input

    # If launched without any arguments (e.g. double clicking run.bat), start interactive wizard!
    if not input_arg and not interactive_mode:
        interactive_mode = True

    if interactive_mode:
        from core.interactive import prompt_interactive
        res = prompt_interactive()
        if res is None:
            return 0
        input_path, output_dir, mode = res
        interactive_ocr = True
        ocr_enabled = True
    else:
        input_path = Path(input_arg).resolve()
        if not input_path.exists():
            print(f'{ANSI.RED}Input khong ton tai: {input_path}{ANSI.RESET}', file=sys.stderr)
            return 1
        output_dir = Path(args.output).resolve()
        mode = 'combined' if args.onemd else args.mode
        interactive_ocr = False
        ocr_enabled = not args.no_ocr

    # Register all backends into the services registry before the pipeline runs
    from services import bootstrap, registry
    bootstrap()

    # Determine converter & OCR display names
    active_convs = [c.name for c in registry._converters if c.is_available()]
    conv_name = active_convs[0] if active_convs else "Khong co"
    ocr_p = registry.ocr_provider()
    ocr_name = ocr_p.name if ocr_p else "Khong co"

    input_size = input_path.stat().st_size if input_path.is_file() else 0
    print_banner(input_path.name, input_size, str(output_dir), mode, ocr_enabled, conv_name, ocr_name)

    t_start = time.time()

    from core.pipeline import run
    result = run(
        input_path, output_dir,
        mode=mode,
        ocr=ocr_enabled,
        ocr_prompt=args.ocr_prompt,
        ocr_limit=args.ocr_limit,
        skip_junk=not args.include_junk,
        skip_auxiliary=not args.include_auxiliary,
        max_depth=args.max_depth,
        show_ui=True,
        interactive_ocr=interactive_ocr,
    )

    research_path: Optional[Path] = None
    if args.research:
        print_stage(5, 5, "🧠", "AI Research Report (Gemini)", "Đánh giá System Design & Kiến trúc dự án")
        t_res = time.time()
        try:
            from core.research import research
            report = research(result.files, result.archive_name)
            research_path = output_dir / f'{result.archive_name}_ai_research.md'
            research_path.write_text(report, encoding='utf-8')
            print(f"  {ANSI.B_GREEN}✓{ANSI.RESET} Đã xuất '{research_path.name}' {ANSI.GRAY}({time.time() - t_res:.1f}s){ANSI.RESET}")
        except Exception as e:
            print(f"  {ANSI.RED}✗ Lỗi AI Research: {e}{ANSI.RESET}", file=sys.stderr)

    total_time = time.time() - t_start
    print_summary(
        result.stats, total_time, str(output_dir),
        combined_path=str(result.combined_path) if result.combined_path else None,
        individual_dir=str(result.individual_dir) if result.individual_dir else None,
        research_path=str(research_path) if research_path else None,
    )
    return 0


if __name__ == '__main__':
    code = main(sys.argv[1:])
    sys.exit(code)
