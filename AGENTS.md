# AGENTS.md — Quy Chuẩn Làm Việc Của Dự Án Archive2MD

> **Dành cho mọi Agent/AI làm việc trong dự án này:** Tuân thủ nghiêm ngặt các nguyên tắc dưới đây.

---

## 1. Nguyên Tắc Cốt Lõi (Core Rules)
- **Đọc hiểu Base trước khi code:** Luôn trace luồng công việc (`cli.py` -> `core/` -> `services/`) trước khi sửa đổi bất kỳ tệp nào. Không đoán mò.
- **Tuân thủ đúng định dạng Output:** Người dùng yêu cầu xuất như thế nào thì phải làm đúng y như vậy. Trả lời ngắn gọn, thẳng thắn, không lòng vòng.
- **Sửa tận gốc, không đổi chức năng:** Sửa lỗi kỹ thuật và xử lý edge case mà không làm thay đổi hành vi hoặc chức năng hiện có của dự án.
- **Tự kiểm thử trước khi báo hoàn tất:** Luôn tự chạy thử nghiệm (kiểm tra syntax, import, chạy thực tế) xác nhận Exit Code 0 và không có ngoại lệ trước khi bàn giao.

---

## 2. Những Điều Tuyệt Đối BỊ CẤM (Strict Prohibitions)
1. **CẤM TỰ Ý PUSH GIT (`git push`):** Chỉ commit tại local branch. Tuyệt đối không tự ý push lên remote trừ khi người dùng ra lệnh bằng văn bản.
2. **CẤM RÒ RỈ LOG DEBUG / AI RA MÀN HÌNH:**
   - Người dùng chỉ muốn thấy giao diện terminal sạch đẹp.
   - Tuyệt đối chặn mọi C-level log, tensor dumps, clip loader, prompt dumps của AI model (`llama.cpp`, `mtmd.dll`).
3. **CẤM GHI FILE RA NGOÀI DỰ ÁN (Strict Isolation):**
   - Mọi cache, compiled bytecode, models, temp files phải nằm trong thư mục `./cache/` và `./models/` của chính dự án.
   - Không được ghi vào `AppData`, `~/.cache` hay thư mục `TEMP` của Windows.
