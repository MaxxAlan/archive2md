# ============================================================================
# research — AI Research & Academic Mentor Report over extracted files.
#
# DESIGN SPECIFICATION (Ghi chú định hướng tính năng từ người dùng):
# Chức năng Nghiên cứu AI sẽ đóng vai trò như một "Giáo sư / Tiến sĩ chuyên ngành"
# đọc duyệt toàn bộ nội dung của tệp tin / bài tập / dự án:
# 1. Nhận diện & mô tả chính xác chủ đề cốt lõi mà tệp tin/dự án đang đề cập.
# 2. Đánh giá độ sâu rộng, mức độ hoàn thiện, tính chặt chẽ của nội dung.
# 3. Đưa ra các hướng phát triển / cải tiến phân định rõ ràng (rạch ròi, đủ sâu rộng):
#    - Đối với Mã nguồn (Code & System Design):
#        + Đánh giá chuyên sâu về System Design / Kiến trúc hệ thống: Phân tích sự phân tầng (layering),
#          tính gắn kết (cohesion), mức độ phụ thuộc lỏng lẻo (loose coupling), luồng dữ liệu (data flow)
#          và quản lý trạng thái (state management).
#        + Khắc phục điểm yếu chí mạng của AI hiện nay: AI thông thường viết từng hàm nhỏ thì ổn
#          nhưng rất hay mắc lỗi nghiêm trọng về System Design (thiếu bức tranh tổng thể, kiến trúc
#          chắp vá, không đáp ứng trọn vẹn yêu cầu người dùng).
#        + Đề xuất kiến trúc chuẩn (Architectural Blueprint), tối ưu thuật toán, Clean Code,
#          Design Patterns và cấu trúc thư mục/module rõ ràng.
#    - Đối với Văn phong / Bài viết: Nâng cao chất lượng biểu đạt, mạch lạc, ngôn từ học thuật/súc tích.
#    - Đối với Báo cáo / Tài liệu: Củng cố tính đầy đủ, chặt chẽ, luận cứ logic, bổ sung góc nhìn phản biện.
# (Tính năng này được lưu lại để triển khai nâng cấp trong giai đoạn tiếp theo).
# ============================================================================
import json
import os
import urllib.request
from pathlib import Path
from typing import Optional

API_BASE = 'https://generativelanguage.googleapis.com/v1beta/models'

PROMPT_TEMPLATE = """Bạn là một chuyên gia nghiên cứu hệ thống phần mềm và phân tích dữ liệu cấp cao (Principal Software Architect & Lead Data Engineer).
Người dùng vừa tải lên tệp nén hoặc thư mục dự án có tên: "{archive_name}".

Dưới đây là danh sách các tệp và trích đoạn mã nguồn/CSDL quan trọng trích xuất được từ gói nén này:

--- DANH SÁCH TỆP & CẤU TRÚC ---
{file_summaries}

--- TRÍCH ĐOẠN NỘI DUNG MÃ / SCHEMA / DỮ LIỆU ĐẠI DIỆN ---
{sample_code}

--- YÊU CẦU NGHIÊN CỨU & BÁO CÁO BẰNG MARKDOWN TIẾNG VIỆT ---
Hãy phân tích sâu (Research) và viết một bản báo cáo tổng kết chi tiết bằng Markdown:
1. **Tổng quan & Bản chất của dự án**: Đây là dự án gì, mục đích giải quyết bài toán gì?
2. **Cấu trúc công nghệ (Tech Stack)**: Các ngôn ngữ, thư viện, framework, hệ CSDL được nhận diện.
3. **Phân tích CSDL & Dữ liệu (Database Architecture)**: Các bảng/schema, quan hệ dữ liệu hoặc dữ liệu excel/csv/sql.
4. **Các module và luồng xử lý chính (Core Business Logic)**.
5. **Điểm mạnh kiến trúc & Các lưu ý/rủi ro tiềm ẩn (nếu có)**.

Hãy trình bày ngắn gọn, sắc sảo, dùng các bảng Markdown, bullet list rõ ràng."""

SAMPLE_CODE_BUDGET = 30_000   # chars of representative content sent to Gemini


def _build_context(files) -> tuple[str, str]:
    """(file_summaries, sample_code) from selected ExtractedFiles."""
    summaries: list[str] = []
    sample_parts: list[str] = []
    budget = SAMPLE_CODE_BUDGET

    for f in files:
        if not f.selected:
            continue
        summaries.append(f'- `{f.path}` ({f.category}, {f.lines_count} dòng, ~{f.token_estimate} tokens)')
        if f.category in ('code', 'database', 'config', 'spreadsheet') and f.raw_content:
            snippet = f.raw_content[:1200]
            if budget > 0:
                budget -= len(snippet)
                sample_parts.append(f'--- {f.path} ---\n{snippet}')

    return '\n'.join(summaries), '\n\n'.join(sample_parts)


def research(files, archive_name: str, model: str = 'gemini-flash-latest',
             api_key: Optional[str] = None) -> str:
    """Call Gemini generateContent and return the markdown report."""
    key = api_key or os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('Chua cau hinh GEMINI_API_KEY trong .env (chi can cho --research).')

    file_summaries, sample_code = _build_context(files)
    prompt = PROMPT_TEMPLATE.format(
        archive_name=archive_name,
        file_summaries=file_summaries or '(Không có)',
        sample_code=sample_code or '(Không có)',
    )
    payload = {'contents': [{'parts': [{'text': prompt}]}]}
    req = urllib.request.Request(
        f'{API_BASE}/{model}:generateContent?key={key}',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        body = json.loads(res.read().decode('utf-8'))
    try:
        return body['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError) as e:
        raise RuntimeError(f'Gemini tra ve khong doc duoc: {json.dumps(body)[:300]}') from e
