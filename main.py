import os
import sys
import threading
import time
import random
import json
import subprocess
import traceback
import customtkinter as ctk
from tkinter import filedialog
from google import genai
from dotenv import load_dotenv

# Import MoviePy 2.0+
try:
    from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
    from moviepy.config import change_settings
except ImportError:
    # Báo hiệu thiếu MoviePy, sẽ được kiểm tra ở phần async_check_at_startup
    pass

# Cấu hình giao diện
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VideoAIApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Xác định thư mục gốc (Base Directory)
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # ****************************************************************
        # NẠP BIẾN MÔI TRƯỜNG TỪ FILE .env
        # ****************************************************************
        self.env_file_path = os.path.join(self.base_dir, ".env")
        load_dotenv(dotenv_path=self.env_file_path)

        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        if self.GEMINI_API_KEY and self.GEMINI_API_KEY != "YOUR_KEY_HERE":
            try:
                # Khởi tạo client
                self.client = genai.Client(api_key=self.GEMINI_API_KEY)
            except Exception:
                self.client = None
        else:
            self.client = None

        # Thư mục input/output
        self.input_dir = os.path.join(self.base_dir, "input")
        self.output_dir = os.path.join(self.base_dir, "output")

        # Tự động tạo thư mục nếu chưa có
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Đặt đường dẫn trình duyệt (Cần thiết cho Playwright)
        self.browser_base_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = self.browser_base_path

        self.title("AI TIKTOK VIDEO CREATOR")
        self.geometry("680x860")

        self.video_path = ""
        self.is_processing = False
        self.stop_requested = False
        self.target_count = 0

        # Khởi tạo UI
        self.setup_ui()

        # Ẩn các thông báo lỗi ban đầu (Không còn nút fix_lib)
        self.lib_warning_label.pack_forget()

        # Chạy kiểm tra bất đồng bộ sau khi UI hiển thị
        self.after(500, self.async_check_at_startup)

    # ****************************************************************
    # CÁC HÀM TIỆN ÍCH HIỂN THỊ LỖI TRÊN UI
    # ****************************************************************
    def show_app_error(self, title, message):
        """Hiển thị thông báo lỗi trên CTkTextbox chuyên dụng."""
        print(f"[{title}] LỖI: {message}") # Vẫn in ra console

        def update_ui():
            # Hiển thị và cập nhật Textbox lỗi
            if not self.error_display.winfo_viewable():
                self.error_display.pack(pady=5, padx=40, fill="x")

            current_time = time.strftime("[%H:%M:%S]")
            error_message = f"{current_time} ❌ {title}: {message}\n"

            self.error_display.configure(state="normal")
            # Chèn thông báo lỗi mới lên đầu
            self.error_display.insert("1.0", error_message)
            self.error_display.configure(state="disabled")

            # Cập nhật trạng thái chung
            self.update_status(f"Đã xảy ra lỗi: {title}", progress=0)

        # Chạy việc cập nhật UI trên luồng chính
        self.after(0, update_ui)

    # ****************************************************************
    # CÁC HÀM KIỂM TRA MÔI TRƯỜNG
    # ****************************************************************

    def check_gemini_api_key(self):
        """Kiểm tra xem GEMINI_API_KEY có được nạp thành công và hợp lệ hay không."""
        key = os.getenv("GEMINI_API_KEY")
        # Kiểm tra sự tồn tại và độ dài tối thiểu (để loại trừ key rỗng/mẫu)
        return key is not None and len(key.strip()) > 10 and key.strip().lower() != "your_key_here"

    def has_playwright_chromium(self):
        """Kiểm tra file thực thi chrome.exe của Playwright."""
        if not os.path.isdir(self.browser_base_path):
            return False
        # Tìm kiếm chrome.exe trong các thư mục con của ms-playwright
        for root, _, files in os.walk(self.browser_base_path):
            if "chrome.exe" in files:
                return True
        return False

    def check_imagemagick_installed(self):
        """Kiểm tra ImageMagick trong PATH."""
        try:
            # Chạy thử lệnh magick -version
            subprocess.run(["magick", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except:
            pass

        # Kiểm tra trong thư mục cục bộ của App (nếu có)
        app_data = os.path.join(os.environ.get("APPDATA", ""), "TikTokVideoAI", "ImageMagick")
        for root, _, files in os.walk(app_data):
             if "magick.exe" in files:
                 path = os.path.join(root, "magick.exe")
                 os.environ["IMAGEMAGICK_BINARY"] = path
                 try:
                     change_settings({"IMAGEMAGICK_BINARY": path})
                 except: pass
                 return True
        return False

    def async_check_at_startup(self):
        """Chạy kiểm tra môi trường ở luồng khác để không làm treo UI."""
        def task():
            has_magick = self.check_imagemagick_installed()
            has_browser = self.has_playwright_chromium()
            has_gemini_key = self.check_gemini_api_key()

            # Giả định thư viện Python (MoviePy, Playwright) đã được cài đặt
            is_ready = has_magick and has_browser and has_gemini_key

            if not is_ready:
                # Nếu thiếu, hiển thị giao diện FIX và TẮT nút chức năng
                self.after(0, lambda: self.show_fix_ui(
                    not has_magick,
                    not has_browser,
                    not has_gemini_key
                ))
                self.after(0, lambda: self.set_main_buttons_state("disabled"))
            else:
                # Nếu đã sẵn sàng
                self.after(0, lambda: self.set_main_buttons_state("normal"))
                self.after(0, lambda: self.lib_warning_label.pack_forget())
                self.after(0, lambda: self.update_status("Hệ thống đã sẵn sàng"))
                self.after(0, lambda: self.error_display.pack_forget())

        threading.Thread(target=task, daemon=True).start()

    def show_fix_ui(self, missing_magick, missing_browser, missing_gemini_key):
        """Hiển thị cảnh báo và yêu cầu người dùng tự cài đặt."""

        # 1. Cập nhật Textbox
        self.lib_warning_label.configure(state="normal")
        self.lib_warning_label.delete("1.0", "end")

        msg = "⚠️ Hệ thống chưa đủ điều kiện sử dụng (Vui lòng cài đặt thủ công):\n\n"

        # 2. Quản lý Browser
        if missing_browser:
            msg += "• THIẾU TRÌNH DUYỆT (Playwright Chromium).\n"
            msg += "  => Yêu cầu chạy lệnh `python -m playwright install chromium` trong Terminal.\n\n"

        # 3. Quản lý ImageMagick
        if missing_magick:
            download_url = "https://imagemagick.org/script/download.php#windows"
            msg += f"• THIẾU IMAGEMAGICK (Xử lý ảnh/chữ).\n"
            msg += f"  => Tải ImageMagick tại đây, cài xong hãy mở lại App:\n{download_url}\n"
            msg += "\n*Lưu ý khi cài ImageMagick (RẤT QUAN TRỌNG):\n"
            msg += "1. Phải tích chọn 'Install legacy utilities' và 'Add application directory to your system path'.\n"
            msg += "2. Nên khởi động lại máy/ứng dụng sau khi cài đặt.\n\n"

        # 4. Quản lý Gemini API Key
        if missing_gemini_key:
            msg += "• THIẾU/SAI GEMINI API KEY (Không thể tạo nội dung AI).\n"
            msg += "  => Vui lòng mở file .env (cùng thư mục app) và thêm GEMINI_API_KEY=YOUR_KEY vào file.\n"

        # Cập nhật Textbox và Status
        self.lib_warning_label.insert("1.0", msg)

        # Phần tính toán chiều cao và pack/configure
        num_lines = msg.count('\n') + 2
        new_height = num_lines * 22
        self.lib_warning_label.configure(height=new_height)
        self.lib_warning_label.configure(state="disabled")

        self.lib_warning_label.pack(pady=5)
        self.set_main_buttons_state("disabled")
        self.update_status("Yêu cầu cài đặt môi trường")

    # ****************************************************************
    # CÁC HÀM TIỆN ÍCH UI
    # ****************************************************************

    def setup_ui(self):
        # Header
        self.header_label = ctk.CTkLabel(self, text="AI TIKTOK VIDEO CREATOR", font=("Segoe UI", 24, "bold"))
        self.header_label.pack(pady=(20, 10))

        auth_info = "XÁC THỰC TÀI KHOẢN TIKTOK\n• Ứng dụng sẽ yêu cầu đăng nhập lần đầu.\n• Thông tin được lưu an toàn trên máy bạn."
        self.info_label = ctk.CTkLabel(self, text=auth_info, font=("Segoe UI", 11), text_color="#00ffcc", justify="center")
        self.info_label.pack(pady=5)

        # Sử dụng CTkTextbox để hiển thị cảnh báo
        self.lib_warning_label = ctk.CTkTextbox(
            self, height=1, width=600, activate_scrollbars=False,
            font=("Segoe UI", 12, "bold"), text_color="#ff4d4d",
            fg_color=self._fg_color,
            border_width=0,
            wrap="word"
        )

        # Textbox Hiển thị LỖI RUNTIME
        self.error_display = ctk.CTkTextbox(
            self, height=80, width=600, activate_scrollbars=True,
            font=("Segoe UI", 11), text_color="#f08080",
            fg_color="#333333",
            border_width=1,
            wrap="word",
            state="disabled"
        )

        # Input Frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=40, fill="x")

        # Prompt input
        self.prompt_label = ctk.CTkLabel(self.input_frame, text="Prompt (Tiếng Việt):")
        self.prompt_label.pack(pady=(10, 0), padx=20, anchor="w")

        self.default_prompt = (
            "Hãy đóng vai một cô gái ngốc nghếch."
            "Hãy viết một dòng trạng thái (status) than vãn, kể khổ về chủ đề: ngẫu nhiên. "
            "Yêu cầu: Giọng văn hay than thân trách phận. "
            "Sử dụng ngôn ngữ đời thường, độ dài khoảng 40-90 chữ. "
            "Chỉ trả về nội dung status bằng tiếng Việt, không thêm bất kỳ văn bản dẫn nhập nào khác."
        )

        self.prompt_entry = ctk.CTkTextbox(self.input_frame, height=100, wrap="word")
        self.prompt_entry.insert("1.0", self.default_prompt)
        self.prompt_entry.pack(pady=(5, 15), padx=10, fill="both")

        # --- Phần nhập Số lượng video ---
        qty_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        qty_frame.pack(pady=(0, 15), padx=20, anchor="w")

        self.qty_label = ctk.CTkLabel(qty_frame, text="Số lượng video tự động tạo:", font=("Segoe UI", 12))
        self.qty_label.grid(row=0, column=0, padx=(0, 10))

        self.qty_entry = ctk.CTkEntry(qty_frame, width=60, justify="center")
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=0, column=1)

        # TikTok Upload Option
        self.upload_var = ctk.BooleanVar(value=True)
        self.upload_checkbox = ctk.CTkCheckBox(self, text="Tự động đăng video lên TikTok", variable=self.upload_var, font=("Segoe UI", 12))
        self.upload_checkbox.pack(pady=5)

        # Chọn ngẫu nhiên video nền ban đầu
        self.set_random_video()

        # Action Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=(15, 6))

        self.btn_run = ctk.CTkButton(btn_frame, text="TẠO VIDEO & UPLOAD TIKTOK", command=self.start_process, height=50, width=220, font=("Segoe UI", 16, "bold"), fg_color="#fe2c55")
        self.btn_run.grid(row=0, column=0, padx=(0, 10))

        self.btn_stop = ctk.CTkButton(btn_frame, text="DỪNG TẠO VIDEO TIẾP THEO", command=self.request_stop, height=50, width=140, font=("Segoe UI", 12, "bold"), fg_color="#6b6b6b")
        self.btn_stop.grid(row=0, column=1)
        self.btn_stop.configure(state="disabled")

        # --- Folder & Manual Upload Frame ---
        secondary_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        secondary_btn_frame.pack(pady=10)

        # 1. Nút Chọn và Upload thủ công
        self.btn_upload_manual = ctk.CTkButton(secondary_btn_frame, text="CHỌN & UPLOAD", command=self.start_manual_upload, height=40, width=160, font=("Segoe UI", 12, "bold"), fg_color="#27ae60", hover_color="#2ecc71")
        self.btn_upload_manual.grid(row=0, column=0, padx=5)

        # 2. Nút Mở thư mục INPUT
        self.btn_open_input = ctk.CTkButton(secondary_btn_frame, text="THƯ MỤC VIDEO NỀN", command=self.open_input_folder, height=40, width=160, font=("Segoe UI", 12, "bold"), fg_color="#8e44ad", hover_color="#9b59b6")
        self.btn_open_input.grid(row=0, column=1, padx=5)

        # 3. Nút Mở thư mục OUTPUT
        self.btn_open_folder = ctk.CTkButton(secondary_btn_frame, text="THƯ MỤC VIDEO ĐÃ TẠO", command=self.open_output_folder, height=40, width=160, font=("Segoe UI", 12, "bold"), fg_color="#34495e", hover_color="#2c3e50")
        self.btn_open_folder.grid(row=0, column=2, padx=5)

        # Status & Progress
        self.status_label = ctk.CTkLabel(self, text="Trạng thái: Đang kiểm tra hệ thống...", text_color="#aaaaaa", wraplength=600)
        self.status_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

    def update_status(self, text, progress=None):
        """Cập nhật trạng thái và thanh tiến trình."""
        if hasattr(self, 'status_label'):
            self.status_label.configure(text=f"Trạng thái: {text}")

        if hasattr(self, 'progress_bar'):
            if progress is not None and progress >= 0:
                # Nếu có giá trị progress, đảm bảo thanh bar đang hiện
                if not self.progress_bar.winfo_viewable():
                    self.progress_bar.pack(pady=10)
                self.progress_bar.set(progress)
            else:
                # Nếu không có progress (ví dụ lúc chờ), có thể ẩn đi
                self.progress_bar.pack_forget()
                self.progress_bar.set(0)
                pass

    def open_output_folder(self):
        """Mở thư mục output."""
        try:
            os.startfile(self.output_dir)
        except Exception as e:
            self.show_app_error("Lỗi Mở Thư Mục", f"Không thể mở thư mục output: {e}")

    def open_input_folder(self):
        """Mở thư mục input."""
        try:
            os.startfile(self.input_dir)
        except Exception as e:
            self.show_app_error("Lỗi Mở Thư Mục", f"Không thể mở thư mục input: {e}")

    def set_main_buttons_state(self, state):
        """Đặt trạng thái (normal/disabled) cho các nút chức năng chính."""
        # Nút TẠO VIDEO & UPLOAD TIKTOK
        self.btn_run.configure(state=state)
        # Nút CHỌN & UPLOAD
        self.btn_upload_manual.configure(state=state)

    def set_random_video(self):
        """Chọn ngẫu nhiên một video nền trong thư mục input."""
        candidates = [os.path.join(self.input_dir, f) for f in os.listdir(self.input_dir) if f.lower().endswith((".mp4", ".mov", ".avi"))]
        if candidates:
            self.video_path = random.choice(candidates)
        else:
            self.video_path = ""

    def split_text(self, text, max_chars_per_line=22):
        """Chia văn bản thành các dòng để hiển thị đẹp hơn trên video dọc."""
        words = text.split()
        lines, current_line, current_length = [], [], 0
        for word in words:
            if current_length + len(word) + 1 <= max_chars_per_line:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line: lines.append(" ".join(current_line))
        return "\n".join(lines)

    def generate_content_with_fallback(self, prompt):
        """Tạo nội dung AI với cơ chế fallback model."""
        if not self.client:
            error_msg = "API Key chưa cấu hình. Vui lòng mở file .env và thêm GEMINI_API_KEY=YOUR_KEY vào file."
            raise Exception(error_msg)
        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash"]:
            try:
                response = self.client.models.generate_content(model=model_name, contents=prompt)
                return response.text.strip().replace('"', '')
            except Exception as e:
                print(f"Lỗi khi dùng model {model_name}: {e}")
                continue

        error_msg = "Không thể kết nối Gemini API (Key có thể sai hoặc hết hạn). Vui lòng kiểm tra lại giá trị GEMINI_API_KEY trong file .env."
        raise Exception(error_msg)

    def get_pw_profile_dir(self):
        """Lấy đường dẫn thư mục profile Playwright để lưu đăng nhập."""
        path = os.path.join(os.environ.get("APPDATA", ""), "TikTokVideoAI", "pw_profile")
        os.makedirs(path, exist_ok=True)
        return path

    def upload_to_tiktok_playwright(self, video_path, description):
        """Tự động đăng video lên TikTok bằng Playwright."""
        from playwright.sync_api import sync_playwright
        # playwright_stealth là thư viện Python, không cần import từ file JS
        import playwright_stealth
        profile_dir = self.get_pw_profile_dir()

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    viewport={'width': 1280, 'height': 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox'
                    ]
                )

                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(120000)

                try:
                    playwright_stealth.stealth(page)
                except Exception as e:
                    print(f"Stealth warning: {e}")

                self.update_status("Đang truy cập TikTok...")
                page.goto(
                    "https://www.tiktok.com/tiktokstudio/upload",
                    wait_until="domcontentloaded"
                )

                # Chờ đăng nhập nếu cần
                if "login" in page.url:
                    self.update_status("Vui lòng đăng nhập TikTok trên trình duyệt để tiếp tục...")
                    try:
                        page.wait_for_url("**/tiktokstudio/upload", timeout=600000)
                    except:
                        print("Login timeout")
                        context.close()
                        self.show_app_error("Lỗi Đăng Nhập", "Quá thời gian chờ đăng nhập TikTok. Vui lòng thử lại.")
                        return False

                self.update_status("Đang tải video...")
                file_input = page.locator('input[type="file"]')
                file_input.wait_for(state="attached", timeout=60000)
                file_input.set_input_files(video_path)

                self.update_status("Đang nhập mô tả...")
                caption = page.locator('.notranslate.public-DraftEditor-content')
                caption.wait_for(state="visible", timeout=60000)
                caption.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(description)

                self.update_status("Chờ xử lý video...")
                post_btn = page.locator('button[data-e2e="post_video_button"]')

                start = time.time()
                while time.time() - start < 300: # Chờ tối đa 5 phút
                    if post_btn.is_visible() and post_btn.is_enabled():
                        if "Uploading" not in post_btn.inner_text():
                            break
                    time.sleep(3)

                if time.time() - start >= 300:
                    error_msg = "Lỗi: Quá thời gian chờ xử lý video trên TikTok. Vui lòng kiểm tra video hoặc kết nối mạng."
                    self.update_status(error_msg)
                    context.close()
                    self.show_app_error("Lỗi Upload TikTok", error_msg)
                    return False

                post_btn.click()
                self.update_status("Đã nhấn nút Đăng!")

                time.sleep(15) # Chờ một chút để quá trình hoàn tất
                context.close()
                return True

        except Exception as e:
            # Bắt tất cả các lỗi Playwright/Python
            print("-" * 30)
            print("LỖI TIKTOK UPLOAD:")
            traceback.print_exc()
            print("-" * 30)
            self.show_app_error("Lỗi Upload TikTok Chung", f"Đã xảy ra lỗi khi upload: {type(e).__name__}. Xem console để biết thêm.")
            return False

    def start_manual_upload(self):
        """Chọn file thủ công từ thư mục output để upload."""
        if self.is_processing:
            self.update_status("Đang có tác vụ khác chạy, vui lòng chờ.")
            return

        # Mở hộp thoại chọn file tại đúng thư mục lưu video
        selected_file = filedialog.askopenfilename(
            initialdir=self.output_dir,
            title="Chọn video để upload",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv")]
        )

        if not selected_file:
            return

        filename = os.path.basename(selected_file)
        self.update_status(f"Đang chuẩn bị upload: {filename}")
        self.set_main_buttons_state("disabled") # Tắt tất cả nút chính
        self.is_processing = True

        def run_upload_task():
            try:
                # Mô tả mẫu cho upload thủ công
                description = "Khoảnh khắc thú vị! #trending #xuhuong #dailyvlog #cuocsong"
                success = self.upload_to_tiktok_playwright(selected_file, description)
                if success:
                    self.update_status("Upload thành công!")
                else:
                    self.update_status("Upload thất bại. Kiểm tra thông báo lỗi.")
            except Exception as e:
                # Lỗi không mong muốn trong luồng
                self.update_status("Đã xảy ra lỗi không mong muốn khi upload thủ công.", 0)
                traceback.print_exc()
                self.show_app_error("Lỗi Upload Thủ Công", f"Đã xảy ra lỗi không mong muốn: {type(e).__name__}.")
            finally:
                self.is_processing = False
                # Bật lại nút sau khi hoàn thành/lỗi
                self.after(0, self.async_check_at_startup)

        threading.Thread(target=run_upload_task, daemon=True).start()

    def request_stop(self):
        """Yêu cầu dừng quá trình xử lý video tiếp theo."""
        self.stop_requested = True
        self.update_status("Đang dừng...")
        self.btn_stop.configure(state="disabled")

    def start_process(self):
        """Bắt đầu quá trình tạo video tự động."""
        if not self.check_gemini_api_key():
            error_msg = "Lỗi: Thiếu API KEY. Vui lòng mở file .env và thêm GEMINI_API_KEY=YOUR_KEY vào file."
            self.update_status(error_msg, 0)
            self.show_app_error("Lỗi API Key", error_msg)
            return

        prompt_text = self.prompt_entry.get("1.0", "end").strip() or self.default_prompt
        self.set_random_video() # Chọn lại video nền ngẫu nhiên trước khi chạy

        if not self.video_path:
            error_msg = "Lỗi: Không tìm thấy video nền. Vui lòng thêm video vào thư mục input."
            self.update_status(error_msg, 0)
            self.show_app_error("Lỗi Video Nền", error_msg)
            return

        try:
            count = int(self.qty_entry.get())
        except ValueError: # Bắt lỗi khi nhập không phải số
            count = 1
            error_msg = "Lỗi: Số lượng video không hợp lệ. Đặt mặc định là 1."
            self.update_status(error_msg, 0)
            self.show_app_error("Lỗi Input", error_msg)

        if count <= 0:
            error_msg = "Lỗi: Số lượng video phải lớn hơn 0."
            self.update_status(error_msg, 0)
            self.show_app_error("Lỗi Input", error_msg)
            return

        # Xóa các lỗi cũ trước khi bắt đầu một tiến trình mới
        self.error_display.configure(state="normal")
        self.error_display.delete("1.0", "end")
        self.error_display.configure(state="disabled")
        self.error_display.pack_forget()

        self.is_processing = True
        self.stop_requested = False
        self.target_count = count
        self.btn_run.configure(state="disabled", text="ĐANG XỬ LÝ...")
        self.btn_upload_manual.configure(state="disabled")
        if count > 1: self.btn_stop.configure(state="normal")

        thread = threading.Thread(target=self.run_logic, args=(prompt_text, count))
        thread.daemon = True
        thread.start()

    def run_logic(self, prompt_text, count):
        """Logic chính để tạo và upload video."""
        # Biến để đánh dấu lỗi đã xảy ra
        had_error = False

        try:
            for i in range(count):
                if self.stop_requested: break

                # 1. Chọn video nền ngẫu nhiên cho mỗi lần lặp
                self.set_random_video()
                if not self.video_path:
                    error_msg = "Lỗi: Không tìm thấy video nền để tiếp tục."
                    self.update_status(error_msg, 0)
                    self.show_app_error("Lỗi Video Nền", error_msg)
                    had_error = True
                    break

                # 2. Tạo nội dung AI
                self.update_status(f"({i+1}/{count}) Đang tạo nội dung...", 0.1)

                raw_content = ""
                try:
                    raw_content = self.generate_content_with_fallback(prompt_text)
                except Exception:
                    # Lỗi đã được xử lý bằng show_app_error trong generate_content_with_fallback
                    had_error = True
                    break # Thoát khỏi vòng lặp

                display_text = self.split_text(raw_content, max_chars_per_line=22)

                # 3. Render Video
                self.update_status(f"({i+1}/{count}) Đang render video...", 0.4)

                # Khai báo biến cần đóng ở phạm vi rộng hơn
                clip = None
                final_video = None

                try:
                    clip = VideoFileClip(self.video_path)
                    duration = min(clip.duration, 15)
                    clip = clip.subclipped(0, duration)

                    target_w, target_h = 720, 1280
                    background = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration)

                    # Tỉ lệ khung hình (resize)
                    video_resized = clip.resized(width=int(target_w))
                    video_centered = video_resized.with_position(('center', 'center'))

                    # Tìm font
                    def get_resource_path(relative_path):
                        if hasattr(sys, '_MEIPASS'):
                            return os.path.join(sys._MEIPASS, relative_path)
                        return os.path.join(os.path.abspath("."), relative_path)

                    font_path = get_resource_path("font.ttf")

                    txt_clip = TextClip(
                        text=display_text, font_size=50, color='white',
                        font=font_path if os.path.exists(font_path) else 'Arial', # Fallback font
                        method='caption', size=(int(target_w * 0.9), None),
                        stroke_color='black', stroke_width=2, text_align='center'
                    ).with_duration(duration).with_position(('center', 'center'))

                    final_video = CompositeVideoClip([background, video_centered, txt_clip], size=(target_w, target_h))

                    ts = time.strftime("%Y%m%d%H%M%S")
                    output_name = f"tiktok_{ts}.mp4"
                    output_path = os.path.abspath(os.path.join(self.output_dir, output_name))

                    final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

                    # 4. Upload TikTok
                    if self.upload_var.get():
                        full_description = f"{raw_content}\n\n#tamtrang #cuocsong #trend #tamsu"
                        self.update_status(f"({i+1}/{count}) Đang đăng TikTok...", 0.8)
                        # upload_to_tiktok_playwright đã có cơ chế bắt lỗi và hiển thị lỗi trên App
                        success = self.upload_to_tiktok_playwright(output_path, full_description)
                        if success:
                            self.update_status(f"({i+1}/{count}) Đăng thành công!", 1.0)
                        else:
                            # Nếu upload thất bại, lỗi đã được hiển thị trên App
                            self.update_status(f"({i+1}/{count}) Upload không thành công. Video đã được lưu tại thư mục output.", 0.5)
                            had_error = True

                    else:
                        self.update_status(f"({i+1}/{count}) Tạo video thành công! Đã lưu tại output.", 1.0)

                except Exception as e:
                    # Bắt lỗi MoviePy, ImageMagick hoặc lỗi file/đường dẫn
                    error_msg = f"Lỗi trong quá trình Render Video: {type(e).__name__} - {str(e)}"
                    print("-" * 30)
                    print(error_msg)
                    traceback.print_exc()
                    print("-" * 30)
                    self.show_app_error("Lỗi Render Video", "Đã xảy ra lỗi khi tạo video. Kiểm tra console và đảm bảo ImageMagick đã cài đặt đúng.")
                    had_error = True
                    break # Thoát khỏi vòng lặp

                finally:
                    # Đảm bảo luôn đóng clip dù thành công hay thất bại
                    if final_video: final_video.close()
                    if clip: clip.close()

                if self.stop_requested: break

                # Nghỉ giữa các lần lặp nếu còn video cần tạo
                if i < count - 1 and not self.stop_requested:
                    wait_time = random.randint(30, 60)
                    for j in range(wait_time):
                        if self.stop_requested: break
                        self.update_status(f"Nghỉ an toàn {wait_time - j}s trước video tiếp theo...", 0)
                        time.sleep(1)

            if not had_error and not self.stop_requested:
                 self.update_status("Hoàn tất tiến trình tạo video.")
            elif self.stop_requested:
                 self.update_status("Đã dừng tiến trình theo yêu cầu.")

        except Exception as e:
            # Bắt lỗi luồng chính (nếu có)
            error_msg = "Đã xảy ra lỗi hệ thống không mong muốn."
            self.update_status(error_msg, 0)
            traceback.print_exc()
            self.show_app_error("Lỗi Hệ Thống Chung", f"{error_msg}. Xem console để biết thêm.")
        finally:
            self.is_processing = False
            # Bật lại nút sau khi hoàn thành/lỗi
            self.after(0, self.async_check_at_startup) # Gọi lại để kiểm tra và đặt trạng thái nút
            self.after(0, lambda: self.btn_run.configure(text="TẠO VIDEO & UPLOAD TIKTOK"))
            self.after(0, lambda: self.btn_stop.configure(state="disabled"))

if __name__ == "__main__":
    app = VideoAIApp()
    app.mainloop()
