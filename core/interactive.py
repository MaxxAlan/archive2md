# ============================================================================
# core/interactive.py — Interactive CLI Wizard for Archive2MD.
# Clean, compact step-by-step guidance without broken boxes or excessive spaces.
# ============================================================================
from pathlib import Path
from typing import Optional, Tuple

from .ui import ANSI, init_terminal


def prompt_interactive() -> Optional[Tuple[Path, Path, str]]:
    """Prompt user interactively for:
    1. Input path (with automatic quote stripping)
    2. Output location (with default ./output)
    3. Export mode (combined / individual / both)

    Returns (input_path, output_dir, mode) or None if user cancelled.
    """
    init_terminal()
    width = 66
    line = "─" * width

    print()
    print(f"{ANSI.B_CYAN}╭─ Archive2MD 📦➡️📝 · Trình Chuyển Đổi Kho Lưu Trữ ──────────{ANSI.RESET}")
    print(f"{ANSI.B_CYAN}│{ANSI.RESET}  {ANSI.GRAY}Chế độ tương tác từng bước (Interactive Setup Wizard){ANSI.RESET}")
    print(f"{ANSI.B_CYAN}╰{line}{ANSI.RESET}\n")

    # 1. Ask for input path
    while True:
        try:
            print(f"{ANSI.BOLD}{ANSI.B_CYAN}[1/3] Nhập đường dẫn tệp nén (.zip, .rar, .7z...) hoặc thư mục cần xử lý:{ANSI.RESET}")
            print(f"  {ANSI.GRAY}• Có thể kéo thả tệp/thư mục trực tiếp vào đây hoặc dán đường dẫn{ANSI.RESET}")
            raw = input(f"  {ANSI.B_YELLOW}👉 Đường dẫn: {ANSI.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{ANSI.YELLOW}[!] Đã hủy thao tác.{ANSI.RESET}\n")
            return None

        # Clean surrounding quotes (handles Windows "Copy as path" and drag & drop)
        cleaned = raw.strip(' "\'\t\r\n')
        if not cleaned:
            print(f"  {ANSI.RED}⚠ Đường dẫn không được để trống. Vui lòng nhập lại.{ANSI.RESET}\n")
            continue

        p = Path(cleaned).resolve()
        if not p.exists():
            print(f"  {ANSI.RED}⚠ Không tìm thấy: {p}{ANSI.RESET}")
            print(f"  {ANSI.GRAY}Vui lòng kiểm tra lại đường dẫn và dán lại.{ANSI.RESET}\n")
            continue

        input_path = p
        print(f"  {ANSI.B_GREEN}✓ Đã chọn: {input_path.name}{ANSI.RESET}\n")
        break

    # 2. Ask for output location
    try:
        print(f"{ANSI.BOLD}{ANSI.B_CYAN}[2/3] Nhập thư mục xuất kết quả:{ANSI.RESET}")
        print(f"  {ANSI.GRAY}• Nhấn [Enter] để dùng mặc định: ./output{ANSI.RESET}")
        raw_out = input(f"  {ANSI.B_YELLOW}👉 Thư mục [output]: {ANSI.RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{ANSI.YELLOW}[!] Đã hủy thao tác.{ANSI.RESET}\n")
        return None

    cleaned_out = raw_out.strip(' "\'\t\r\n')
    if not cleaned_out:
        output_dir = Path("output").resolve()
    else:
        output_dir = Path(cleaned_out).resolve()
    print(f"  {ANSI.B_GREEN}✓ Thư mục xuất: {output_dir}{ANSI.RESET}\n")

    # 3. Ask for export mode
    try:
        print(f"{ANSI.BOLD}{ANSI.B_CYAN}[3/3] Chọn kiểu xuất Markdown:{ANSI.RESET}")
        print(f"  {ANSI.WHITE}[1]{ANSI.RESET} Xuất 1 file Markdown tổng hợp duy nhất {ANSI.GRAY}(Combined) [Khuyên dùng - Mặc định]{ANSI.RESET}")
        print(f"  {ANSI.WHITE}[2]{ANSI.RESET} Xuất từng file Markdown riêng biệt theo cây thư mục {ANSI.GRAY}(Individual){ANSI.RESET}")
        print(f"  {ANSI.WHITE}[3]{ANSI.RESET} Xuất cả hai định dạng trên {ANSI.GRAY}(Both){ANSI.RESET}")
        raw_mode = input(f"  {ANSI.B_YELLOW}👉 Lựa chọn [1]: {ANSI.RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{ANSI.YELLOW}[!] Đã hủy thao tác.{ANSI.RESET}\n")
        return None

    mode_map = {"1": "combined", "2": "individual", "3": "both"}
    mode = mode_map.get(raw_mode, "combined")
    mode_name = {
        "combined": "1 file Markdown tổng hợp (Combined)",
        "individual": "Từng file riêng (Individual)",
        "both": "Cả hai định dạng (Both)",
    }[mode]
    print(f"  {ANSI.B_GREEN}✓ Chế độ đã chọn: {mode_name}{ANSI.RESET}\n")

    return input_path, output_dir, mode
