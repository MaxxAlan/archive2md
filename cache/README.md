# Archive2MD — Hệ Thống Quản Lý Cache Tập Trung

Thư mục `cache/` được thiết kế để gom toàn bộ dữ liệu tạm, bộ nhớ đệm và kết quả biên dịch phát sinh từ tất cả các chương trình, thư viện con trong quá trình chạy công cụ về một mối duy nhất.

---

## Cấu Trúc Thư Mục

| Thư mục | Biến Môi Trường / Cơ Chế | Mục Đích | Chính Sách Dọn Dẹp |
| :--- | :--- | :--- | :--- |
| `cache/pycache/` | `PYTHONPYCACHEPREFIX`, `sys.pycache_prefix` | Chứa toàn bộ file bytecode (`.pyc`) biên dịch của Python. Giúp mã nguồn không bị rác thư mục `__pycache__` rải rác, đồng thời tăng tốc độ khởi động cực nhanh cho các lần chạy sau. | **GIỮ LẠI** (Cache biên dịch, không xóa để chạy nhanh) |
| `cache/cuda/` | `CUDA_CACHE_PATH` | Lưu trữ kernel PTX / JIT compiled của NVIDIA CUDA khi khởi chạy GPU offloading. | **GIỮ LẠI** (Tránh biên dịch lại kernel CUDA mỗi lần chạy) |
| `cache/build/` | Build scripts / artifacts | Chứa các file thực thi nhị phân, source C++/CUDA thử nghiệm (như `cuda_run.exe`, `test.cu`). | **GIỮ LẠI** |
| `cache/models/` | `HF_HOME`, `TORCH_HOME` | Cache mô hình và tokenizer (HuggingFace, PyTorch) nếu phát sinh từ các bộ chuyển đổi tài liệu. | **GIỮ LẠI** |
| `cache/pip/` | `PIP_CACHE_DIR` | Chứa cache bánh xe `.whl` và download của Pip khi chạy `setup.bat`. | **GIỮ LẠI** (Tránh tải lại gói thư viện) |
| `cache/ocr/` | Subsystem OCR | Bộ nhớ đệm xử lý ảnh trung gian trước khi gửi tới Vision AI. | **TỰ ĐỘNG QUẢN LÝ** |
| `cache/tmp/` | `TEMP`, `TMP`, `tempfile.tempdir` | File trích xuất tạm từ file nén (7z, zip, rar...) và tài liệu tạm thời của Docling / MarkItDown. | **TỰ ĐỘNG DỌN DẸP** (Xóa các file tạm cũ > 24h qua hàm `purge_stale_cache`) |

---

## Cơ Chế Tự Động Điều Hướng
Khi khởi chạy thông qua `run.bat`, `setup.bat` hoặc trực tiếp từ `cli.py`:
1. Hàm `init_cache_system()` từ `services/base.py` sẽ tự động khởi tạo đầy đủ các thư mục trên nếu chưa có.
2. Thiết lập `sys.pycache_prefix` và kích hoạt bytecode caching để Python tự ghi `.pyc` vào `cache/pycache/`.
3. Gán biến môi trường hệ thống (`TEMP`, `TMP`, `CUDA_CACHE_PATH`, `HF_HOME`, `TORCH_HOME`, `PIP_CACHE_DIR`) để ép tất cả thư viện bên thứ ba ghi cache về đúng thư mục con tương ứng trong `cache/`.
4. Hàm vệ sinh cache `purge_stale_cache()` sẽ tự động quét và chỉ xóa các file tạm trong `cache/tmp/` đã tồn tại hơn 24 giờ. Toàn bộ cache biên dịch và tài nguyên tăng tốc khác đều được bảo toàn.
