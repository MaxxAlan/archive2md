# Archive2MD 📦➡️📝

Chuyển đổi toàn diện kho lưu trữ (`.zip`, `.rar`, `.7z`, `.tar`, thư mục) thành tài liệu Markdown tinh gọn, hỗ trợ trích xuất tài liệu văn phòng (Docx, Excel, PowerPoint, PDF) và nhận diện văn bản hình ảnh bằng Vision AI cục bộ tăng tốc bằng card đồ họa rời NVIDIA.

---

## ⚡ Tính năng nổi bật

- 🗜️ **Giải nén đa tầng**: Hỗ trợ đệ quy ZIP, RAR, 7Z, TAR và thư mục thông thường.
- 🧹 **Lọc rác thông minh**: Tự động loại bỏ cache (`node_modules`, `__pycache__`, `.git`), binary thừa (`.dll`, `.exe`, `.so`), và các file phụ trợ không cần thiết.
- 📄 **Chuyển đổi tài liệu văn phòng**: Tích hợp Microsoft MarkItDown (Word, Excel, PowerPoint, PDF, HTML, v.v.).
- 👁️ **Local Vision OCR với NVIDIA GPU**: Chạy trực tiếp model **Qwen2.5-VL-3B** cục bộ qua `llama-cpp-python` trên card NVIDIA (GTX 1650, RTX series), không tốn phí API, không rò rỉ dữ liệu.
- 🧠 **AI Research Report (Đang định hình)**: Đóng vai trò như một chuyên gia/tiến sĩ đánh giá toàn diện nội dung tệp tin, phân tích chiều sâu kiến trúc phần mềm (**System Design** - khắc phục điểm yếu chắp vá kiến trúc của AI hiện nay), tối ưu mã nguồn, nâng tầm văn phong và củng cố tính chặt chẽ của báo cáo.
- 📑 **Xuất Markdown tiêu chuẩn**: Hỗ trợ xuất 1 file tổng hợp (`combined`), xuất từng file riêng biệt (`individual`), hoặc cả hai (`both`). Kèm theo cây thư mục, thống kê số dòng và ước tính token.

---

## 🖥️ Cấu hình phần cứng & GPU

Dự án đã được cấu hình tối ưu để khai thác sức mạnh phần cứng của bạn:
- **GPU**: NVIDIA GeForce GTX 1650 (4GB VRAM) / RTX series.
- **Hỗ trợ CUDA**: CUDA 13.5 Toolkit + CUDA Runtime DLLs được tự động nạp.
- Toàn bộ 36 layers của Qwen2.5-VL-3B được offload lên GPU VRAM, xử lý OCR nhanh gấp nhiều lần CPU.

---

## 📁 Cấu trúc thư mục dự án

```text
archive2md/
├── .venv/               # Môi trường ảo Python duy nhất (chứa đầy đủ các thư viện và CUDA runtime)
├── core/                # Logic xử lý nghiệp vụ chính
│   ├── intake.py        # Giải nén đệ quy và duyệt tệp tin
│   ├── classify.py      # Phân loại định dạng, lọc rác và file nhị phân
│   ├── convert.py       # Điều phối chuyển đổi tài liệu văn phòng
│   ├── ocr.py           # Điều phối OCR thị giác máy tính
│   ├── markdown.py      # Ghép và định dạng Markdown (cây thư mục, mục lục, token)
│   ├── research.py      # Tạo báo cáo tổng quan bằng Gemini AI
│   ├── pipeline.py      # Điều phối toàn bộ luồng xử lý
│   └── types.py         # Định nghĩa kiểu dữ liệu & schema
├── services/            # Tích hợp các công cụ chuyển đổi & AI
│   ├── base.py          # Cấu hình CUDA DLL, cache và giao diện cơ sở
│   ├── registry.py      # Service locator quản lý converter & OCR
│   ├── markitdown.py    # Microsoft MarkItDown (Word, Excel, PPT, PDF, ...)
│   ├── docling.py       # IBM Docling (tùy chọn)
│   └── qwen_ocr.py      # Qwen2.5-VL-3B OCR server chạy trên NVIDIA GPU
├── models/              # Chứa các file trọng số GGUF cho Qwen2.5-VL
├── samples/             # Dữ liệu thử nghiệm
├── output/              # Thư mục lưu kết quả Markdown xuất ra
├── cache/               # Bộ nhớ đệm tạm thời (tự động dọn dẹp)
├── cli.py               # Giao diện dòng lệnh chính (CLI)
├── run.bat              # Phím tắt chạy nhanh trên Windows
├── setup.bat            # Script khởi tạo môi trường tự động
├── requirements.txt     # Danh sách thư viện Python
└── pyproject.toml       # Cấu hình dự án chuẩn
```

---

## 🛠️ Cài đặt 1-Click (Dành cho máy người dùng mới tinh)

Nếu bạn vừa clone dự án từ Git về một máy tính Windows hoàn toàn mới (chưa có Python hoặc chưa có model AI):

1. **Chỉ cần nhấp đúp vào `setup.bat`**:
   - Tự động kiểm tra Python trên máy. Nếu chưa có, script sẽ **tự động tải và cài đặt Python 3.12 (64-bit)** chính thức từ python.org.
   - Tự động tạo môi trường ảo `.venv` cô lập.
   - Tự động cài đặt đầy đủ 100% các thư viện cần thiết (`markitdown`, parser văn phòng `docx/pdf/xlsx/pptx`, `py7zr`, `rarfile`, `llama-cpp-python`, NVIDIA CUDA...).
   - Tự động kiểm tra và hỏi bạn có muốn tải bộ mô hình Vision AI Qwen2.5-VL-3B (~2.7 GB) từ Hugging Face về thư mục `models/` (hỗ trợ tiếp tục tải Resume nếu mất mạng).
   - Kiểm tra toàn bộ hệ thống và hiển thị trạng thái sẵn sàng.

---

## 🚀 Hướng dẫn sử dụng

### 1. Chạy tương tác từng bước (Interactive Wizard) ⭐ *(Đơn giản nhất)*
Bạn chỉ cần **nhấp đúp chuột vào `run.bat`** (hoặc chạy lệnh `.\run.bat` không tham số):
- Hệ thống sẽ hiển thị giao diện hỏi đáp thân thiện.
- Dán đường dẫn file nén/thư mục (hỗ trợ tự động lọc bỏ dấu ngoặc kép `""` khi kéo thả hoặc dùng *Copy as path*).
- Nhập thư mục xuất và chọn kiểu xuất Markdown.
- Trong quá trình quét, nếu phát hiện hình ảnh/tài liệu scan, hệ thống sẽ tự động hỏi bạn có muốn bật GPU Vision OCR hay không.

### 2. Kiểm tra trạng thái hệ thống
```powershell
run.bat --status
# hoặc
.venv\Scripts\python.exe cli.py --status
```

### 3. Chạy trực tiếp qua dòng lệnh (CLI Mode)
```powershell
# Chuyển đổi cơ bản (1 file Markdown tổng hợp)
run.bat duong_dan_file.zip -o output

# Chuyển đổi kèm OCR hình ảnh/PDF bằng GPU
run.bat duong_dan_file.zip --ocr -o output

# Xuất cả file tổng hợp và từng file riêng rẽ
run.bat duong_dan_file.zip --mode both -o output
```

---

## ⚙️ Các tham số CLI

| Tham số | Ý nghĩa | Mặc định |
| :--- | :--- | :--- |
| `-i`, `--input` | Đường dẫn file nén (`.zip`, `.rar`, `.7z`, ...) hoặc thư mục | Bắt buộc |
| `-o`, `--output` | Thư mục xuất kết quả | `./output` |
| `--mode` | Chế độ xuất: `combined`, `individual`, `both` | `combined` |
| `--ocr` | Bật OCR thị giác cục bộ (Qwen2.5-VL-3B trên NVIDIA GPU) | Tắt |
| `--ocr-limit` | Giới hạn số file OCR (0 = không giới hạn) | 0 |
| `--research` | Tạo báo cáo AI Research (yêu cầu GEMINI_API_KEY) | Tắt |
| `--include-junk` | Giữ lại các file rác (`node_modules`, lockfile, ...) | Tắt |
| `--max-depth` | Độ sâu giải nén đệ quy tối đa | 5 |
| `--status` | Xem danh sách và trạng thái các công cụ chuyển đổi | |

---

## 🔬 Lựa chọn Converter & Xử lý Tài liệu Khoa Học

Dự án cung cấp cơ chế chuyển đổi linh hoạt với 2 backend chính:

### 1. Microsoft MarkItDown (Khuyên dùng mặc định)
- **Cơ chế**: Parser quy tắc chuyên sâu kết hợp engine trích xuất văn phòng tối ưu.
- **Ưu điểm**: Xử lý cực nhanh (vài mili-giây đến vài giây), siêu nhẹ (không tốn GPU/VRAM), hỗ trợ định dạng phong phú nhất (`.docx`, `.xlsx`, `.pptx`, `.pdf`, `.html`, `.csv`, `.epub`, `.msg`...).
- **Phù hợp**: 95% nhu cầu thực tế khi quét toàn bộ repo, kho tài liệu hoặc dự án lớn.

### 2. IBM Docling (Tùy chọn cho tài liệu khoa học phức tạp)
- **Cơ chế**: Deep Learning Document Layout Analysis (nhận diện bố cục trang 2 cột, bảng biểu lồng nhau, công thức toán LaTeX).
- **Trạng thái**: Tùy chọn (`MISSING` theo mặc định để tránh phình dung lượng môi trường ảo).
- **Cách kích hoạt**: Mã nguồn ([services/docling.py](file:///D:/project/archive2md/services/docling.py)) đã tích hợp sẵn và tự động ưu tiên `priority = 20`. Chỉ cần cài đặt:
  ```powershell
  .\.venv\Scripts\pip install docling
  ```
- **Lưu ý**: Nên để Docling chạy trên CPU nhằm tránh tranh chấp VRAM với model Qwen2.5-VL.

### 3. Quy trình khuyến nghị xử lý bài báo khoa học (arXiv, IEEE, PDF 2 cột)
- **Phương án nhẹ & thông minh**: Dùng **MarkItDown** kết hợp cờ `--research`:
  ```powershell
  run.bat paper.pdf --research -o output
  ```
  *MarkItDown trích xuất cấu trúc văn bản thô, sau đó Gemini AI sẽ tự động liên kết lại các cột, định dạng bảng số liệu và sinh báo cáo tổng quan phân tích sâu.*
- **Phương án giữ trọn vẹn bố cục**: Kích hoạt **Docling** và chạy không kèm cờ `--ocr` để tối ưu tài nguyên.

---

## 📊 Bảng Đánh Giá Hiệu Năng & Tiêu Thụ VRAM (GTX 1650 4GB)

Chi tiết mức độ tương thích và tài nguyên thực tế khi chạy trên cấu hình **NVIDIA GeForce GTX 1650 (4GB VRAM)**:

| Mô hình / Công cụ | Dung lượng VRAM | RAM hệ thống | Tốc độ xử lý | Khả thi trên GTX 1650 | Đánh giá & Rủi ro |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Qwen2.5-VL-3B (GGUF Q4_K_M)** *(Tích hợp sẵn)* | **~2.8 – 3.2 GB** | ~1 GB | **3 – 8s / ảnh** | ✅ **Hoàn hảo** | Chạy qua `llama-cpp-python` CUDA, offload toàn bộ 36 layers lên GPU. Vừa vặn an toàn trong 4GB VRAM. |
| **IBM Docling** *(Tùy chọn)* | ~2.5 – 3.5 GB *(nếu GPU)* | ~2 – 4 GB | 5 – 15s / trang | ⚠️ **Chỉ nên chạy CPU** | Nếu chạy GPU đồng thời với Qwen-VL sẽ **tràn 4GB VRAM (OOM Crash)**. Chạy thuần CPU thì rất ổn định. |
| **Nougat (Meta AI)** | `small`: ~2.8 – 3.5 GB<br>`base`: > 5.0 GB | ~4 GB | 15 – 30s / trang | ⚠️ **Chỉ bản small (ngấp nghé)** | Bản `base` chắc chắn OOM. Bản `small` ép chạy được nhưng dễ lặp từ (hallucination) và xử lý chậm. |
| **MinerU (PDF-Extract-Kit)** | **8 – 16 GB** *(Khuyến nghị)* | 12 – 16 GB | 1 – 3 phút / trang *(CPU)* | ❌ **Không khả thi local** | Pipeline gồm nhiều model lớn lồng nhau. GPU 4GB **chắc chắn OOM Crash**. Chạy CPU quá nặng và chậm. |

> [!NOTE]
> Đối với các bộ công cụ nặng như **MinerU**, giải pháp tối ưu nhất là sử dụng Web Demo miễn phí của OpenDataLab / HuggingFace Spaces hoặc chạy trên Google Colab GPU T4 (16GB VRAM), sau đó đưa kết quả Markdown về Archive2MD để lưu trữ và tổng hợp.
