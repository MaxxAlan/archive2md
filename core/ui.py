# ============================================================================
# core/ui.py — Beautiful, Clean Terminal UI & Progress Tracker for Archive2MD.
# Immune to frame breaking: Uses sleek open-right card borders, no wide-char overflow.
# Zero-dependency, pure Python, native ANSI color and VT100 support on Windows.
# ============================================================================
import os
import shutil
import sys
import time
from typing import Optional


class ANSI:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

    # Foreground
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    GRAY = '\033[90m'

    # Bright foreground
    B_RED = '\033[91m'
    B_GREEN = '\033[92m'
    B_YELLOW = '\033[93m'
    B_BLUE = '\033[94m'
    B_MAGENTA = '\033[95m'
    B_CYAN = '\033[96m'
    B_WHITE = '\033[97m'

    # Cursor
    CLEAR_LINE = '\033[2K'
    CLEAR_TO_END = '\033[K'


def init_terminal() -> None:
    """Enable ANSI/VT100 escape codes and UTF-8 encoding on Windows console."""
    if os.name == 'nt':
        os.system('')
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


def get_term_width(default: int = 80) -> int:
    try:
        cols = shutil.get_terminal_size((default, 24)).columns
        return max(40, cols)
    except Exception:
        return default


def format_duration(seconds: float) -> str:
    """Format seconds into readable 00:00 or 00:00:00 format."""
    if seconds < 0 or seconds != seconds:  # NaN check
        return "--:--"
    total_secs = int(round(seconds))
    mins, secs = divmod(total_secs, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_bytes(size: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != 'B' else f"{size} B"
        size /= 1024
    return f"{size:.1f} TB"


def truncate_middle(text: str, max_len: int) -> str:
    """Truncate text with ... in the middle if it exceeds max_len."""
    if len(text) <= max_len:
        return text
    if max_len <= 5:
        return text[:max_len]
    half = (max_len - 3) // 2
    return text[:half] + "..." + text[-half:]


def print_banner(input_name: str, input_size: int, output_dir: str, mode: str,
                 ocr_enabled: bool, converter_name: str, ocr_name: str) -> None:
    """Print an eye-catching, modern header banner with open-right border (never breaks)."""
    width = min(get_term_width(), 68)
    bot_line = "─" * width

    size_str = format_bytes(input_size) if input_size > 0 else "Thư mục"
    ocr_str = ocr_name if ocr_enabled else "Tắt (Skip)"

    print()
    print(f"{ANSI.B_CYAN}╭─ Archive2MD 📦➡️📝 · Trích Xuất Kho Lưu Trữ ────────────────{ANSI.RESET}")
    print(f"{ANSI.B_CYAN}│{ANSI.RESET}  {ANSI.GRAY}Tập tin   :{ANSI.RESET} {ANSI.BOLD}{ANSI.B_WHITE}{input_name}{ANSI.RESET} {ANSI.GRAY}({size_str}){ANSI.RESET}")
    print(f"{ANSI.B_CYAN}│{ANSI.RESET}  {ANSI.GRAY}Xuất ra   :{ANSI.RESET} {ANSI.B_WHITE}{output_dir}{ANSI.RESET} {ANSI.CYAN}[{mode.upper()}]{ANSI.RESET}")
    print(f"{ANSI.B_CYAN}│{ANSI.RESET}  {ANSI.GRAY}Bộ chuyển :{ANSI.RESET} {ANSI.GREEN}{converter_name}{ANSI.RESET}")
    print(f"{ANSI.B_CYAN}│{ANSI.RESET}  {ANSI.GRAY}Vision OCR:{ANSI.RESET} {ANSI.B_MAGENTA if ocr_enabled else ANSI.GRAY}{ocr_str}{ANSI.RESET}")
    print(f"{ANSI.B_CYAN}╰{bot_line}{ANSI.RESET}")
    print()


def print_stage(step: int, total_steps: int, icon: str, title: str, subtitle: str = "") -> None:
    """Print a clean stage divider without line wrapping."""
    width = min(get_term_width(), 68)
    dash_len = max(6, width - len(title) - 18)
    line = "─" * dash_len
    print(f"\n{ANSI.BOLD}{ANSI.B_BLUE}── [{step}/{total_steps}] {icon} {title} {line}{ANSI.RESET}")
    if subtitle:
        print(f"   {ANSI.GRAY}└─ {subtitle}{ANSI.RESET}")


class ProgressBar:
    """Real-time progress bar with percentage, speed, elapsed time, and ETA."""

    def __init__(self, total: int, label: str = "Tiến độ", unit: str = "tệp",
                 bar_width: int = 20, is_active: bool = True) -> None:
        self.total = max(1, total)
        self.current = 0
        self.label = label
        self.unit = unit
        self.bar_width = bar_width
        self.is_active = is_active
        self.start_time = time.time()
        self.last_update_time = 0.0
        self.is_tty = sys.stdout.isatty()

    def update(self, current: int, item_name: str = "", status: str = "") -> None:
        self.current = min(current, self.total)
        now = time.time()
        if self.current < self.total and (now - self.last_update_time < 0.05):
            return
        self.last_update_time = now

        elapsed = max(0.001, now - self.start_time)
        pct = self.current / self.total
        filled = int(round(pct * self.bar_width))
        empty = self.bar_width - filled
        bar_str = f"{ANSI.B_GREEN}{'█' * filled}{ANSI.GRAY}{'░' * empty}{ANSI.RESET}"

        if self.current > 0:
            avg_per_item = elapsed / self.current
            remaining_items = self.total - self.current
            eta_seconds = remaining_items * avg_per_item
            eta_str = format_duration(eta_seconds)

            if avg_per_item >= 1.0:
                speed_str = f"{avg_per_item:.1f}s/{self.unit}"
            else:
                speed_str = f"{self.current / elapsed:.1f} {self.unit}/s"
        else:
            eta_str = "--:--"
            speed_str = f"-- {self.unit}/s"

        percent_str = f"{int(pct * 100):>3}%"
        counts_str = f"[{self.current}/{self.total}]"

        term_width = min(get_term_width(), 80)
        left_part = f"  {ANSI.BOLD}{percent_str}{ANSI.RESET} {bar_str} {ANSI.B_WHITE}{counts_str}{ANSI.RESET}"
        mid_part = f" │ {ANSI.YELLOW}⚡ {speed_str}{ANSI.RESET} │ {ANSI.B_MAGENTA}⏳ Còn: ~{eta_str}{ANSI.RESET}"

        # Truncate filename gracefully to prevent line wrapping
        avail = max(10, term_width - 55)
        file_disp = ""
        if item_name:
            truncated = truncate_middle(item_name, avail)
            status_disp = f" ({status})" if status else ""
            file_disp = f" │ {ANSI.GRAY}{truncated}{status_disp}{ANSI.RESET}"

        line = f"{left_part}{mid_part}{file_disp}"

        if self.is_tty:
            sys.stdout.write(f"\r{ANSI.CLEAR_TO_END}{line}")
            sys.stdout.flush()
        else:
            if self.current == self.total or self.current % max(1, self.total // 5) == 0:
                print(f"  [{percent_str}] {counts_str} {item_name} (ETA: {eta_str})")

    def finish(self, message: str = "") -> None:
        elapsed = time.time() - self.start_time
        if self.is_tty:
            sys.stdout.write(f"\r{ANSI.CLEAR_TO_END}")
            sys.stdout.flush()
        icon = f"{ANSI.B_GREEN}✓{ANSI.RESET}"
        msg = f"{ANSI.GREEN}{message}{ANSI.RESET}" if message else f"{ANSI.GREEN}Hoàn tất ({self.total} {self.unit}){ANSI.RESET}"
        time_tag = f"{ANSI.GRAY}(Thời gian: {elapsed:.1f}s){ANSI.RESET}"
        print(f"  {icon} {msg} {time_tag}")


def print_summary(stats, total_time: float, output_dir: str,
                  combined_path: Optional[str] = None,
                  individual_dir: Optional[str] = None,
                  research_path: Optional[str] = None) -> None:
    """Print an exquisite completion summary card with open-right border (never breaks)."""
    width = min(get_term_width(), 68)
    bot_line = "─" * width

    print()
    print(f"{ANSI.B_GREEN}╭─ 🎉 HOÀN TẤT XỬ LÝ ({total_time:.2f}s) ──────────────────────────{ANSI.RESET}")
    print(f"{ANSI.B_GREEN}│{ANSI.RESET}  {ANSI.GRAY}📦 Tổng số tệp quét được :{ANSI.RESET} {ANSI.BOLD}{ANSI.B_WHITE}{stats.total_files:,} tệp{ANSI.RESET}")
    print(f"{ANSI.B_GREEN}│{ANSI.RESET}  {ANSI.GRAY}✅ Tệp hợp lệ được chọn  :{ANSI.RESET} {ANSI.BOLD}{ANSI.B_WHITE}{stats.selected_count:,} tệp{ANSI.RESET} {ANSI.GRAY}(lọc {stats.junk_count + stats.auxiliary_count:,} rác/phụ trợ){ANSI.RESET}")
    if stats.converted_count > 0:
        print(f"{ANSI.B_GREEN}│{ANSI.RESET}  {ANSI.GRAY}📄 Tài liệu đã chuyển đổi:{ANSI.RESET} {ANSI.BOLD}{ANSI.B_WHITE}{stats.converted_count:,} tệp{ANSI.RESET} {ANSI.GRAY}(MarkItDown/Docling){ANSI.RESET}")
    if stats.ocr_completed_count > 0:
        print(f"{ANSI.B_GREEN}│{ANSI.RESET}  {ANSI.GRAY}👁️ Thị giác GPU OCR     :{ANSI.RESET} {ANSI.BOLD}{ANSI.B_WHITE}{stats.ocr_completed_count:,} hình ảnh/trang{ANSI.RESET}")
    print(f"{ANSI.B_GREEN}│{ANSI.RESET}  {ANSI.GRAY}📝 Tổng số dòng văn bản  :{ANSI.RESET} {ANSI.BOLD}{ANSI.B_WHITE}~{stats.selected_lines:,} dòng{ANSI.RESET}")
    print(f"{ANSI.B_GREEN}│{ANSI.RESET}  {ANSI.GRAY}🪙 Ước tính Token LLM    :{ANSI.RESET} {ANSI.BOLD}{ANSI.B_WHITE}~{stats.selected_tokens:,} tokens{ANSI.RESET}")
    print(f"{ANSI.B_GREEN}│{ANSI.RESET}")
    print(f"{ANSI.B_GREEN}│{ANSI.RESET}  {ANSI.BOLD}{ANSI.B_YELLOW}📁 Tệp tin xuất ra:{ANSI.RESET}")
    if combined_path:
        print(f"{ANSI.B_GREEN}│{ANSI.RESET}   {ANSI.CYAN}├─ Combined Markdown:{ANSI.RESET} {ANSI.B_WHITE}{combined_path}{ANSI.RESET}")
    if individual_dir:
        print(f"{ANSI.B_GREEN}│{ANSI.RESET}   {ANSI.CYAN}├─ Thư mục Markdown :{ANSI.RESET} {ANSI.B_WHITE}{individual_dir}{ANSI.RESET}")
    if research_path:
        print(f"{ANSI.B_GREEN}│{ANSI.RESET}   {ANSI.CYAN}├─ AI Research      :{ANSI.RESET} {ANSI.B_WHITE}{research_path}{ANSI.RESET}")
    print(f"{ANSI.B_GREEN}│{ANSI.RESET}   {ANSI.CYAN}└─ Thư mục kết quả  :{ANSI.RESET} {ANSI.B_WHITE}{output_dir}{ANSI.RESET}")
    print(f"{ANSI.B_GREEN}╰{bot_line}{ANSI.RESET}")
    print()
