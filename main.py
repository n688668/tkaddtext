import os
import threading
import time
import random
import json
import sys
import subprocess
import traceback
import customtkinter as ctk
from google import genai
from dotenv import load_dotenv
# Cập nhật cách import cho MoviePy 2.0+
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# 1. Nạp biến môi trường từ file .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cấu hình Client Gemini
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# Cấu hình giao diện
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VideoAIApp(ctk.CTk):
    def has_playwright_chromium(self):
        browser_dir = os.path.join(
            os.environ.get("LOCALAPPDATA"),
            "ms-playwright"
        )

        if not os.path.isdir(browser_dir):
            return False

        for root, _, files in os.walk(browser_dir):
            if "chrome.exe" in files:
                return True

        return False

    def update_browser_ui_visibility(self):
        has_browser = self.has_playwright_chromium()

        if has_browser:
            self.update_status("Sẵn sàng", 0)
            self.progress_bar.pack_forget()
            self.btn_cancel_download.pack_forget()
        else:
            self.progress_bar.pack(pady=10)
            self.btn_cancel_download.pack(pady=5)
            self.btn_cancel_download.configure(state="disabled")

    def __init__(self):
        super().__init__()

        self.title("AI TikTok Video Generator")
        self.geometry("750x650")

        self.video_path = ""
        self.is_processing = False
        self.stop_requested = False
        self.target_count = 0

        self.chromium_user_cancelled = False
        self.chromium_download_process = None
        self.chromium_cancel_event = threading.Event()

        # Trạng thái thư viện (Kiểm tra động)
        self.has_playwright = self.check_playwright()

        # Khởi tạo UI
        self.setup_ui()

        # Thông báo lỗi ra console nếu thiếu thư viện
        if not self.has_playwright:
            print("-" * 50)
            print("HƯỚNG DẪN SỬA LỖI THƯ VIỆN (Dành cho VS Code Git Bash):")
            print(f"BƯỚC 1: Chạy lệnh cài đặt:")
            print(f"'{sys.executable}' -m pip install playwright playwright-stealth browser-cookie3")
            print(f"BƯỚC 2: Cài đặt trình duyệt:")
            print(f"'{sys.executable}' -m playwright install chromium")
            print("-" * 50)

        self.update_browser_ui_visibility()

    def cancel_chromium_download(self):
        self.chromium_user_cancelled = True
        self.chromium_cancel_event.set()

        if self.chromium_download_process:
            try:
                self.chromium_download_process.terminate()
            except:
                pass

        self.update_status(
            "Bạn đã hủy tải trình duyệt.\nNhấn Upload lại nếu muốn tiếp tục.",
            0
        )
        self.btn_cancel_download.configure(state="disabled")

    def fake_download_progress(self, stop_event, cancel_event):
        progress = 0.05
        self.progress_bar.set(progress)

        while not stop_event.is_set() and not cancel_event.is_set():
            time.sleep(random.uniform(0.3, 0.7))
            progress += random.uniform(0.02, 0.05)
            progress = min(progress, 0.9)
            self.progress_bar.set(progress)

        if stop_event.is_set():
            self.progress_bar.set(1.0)

    def ensure_playwright_chromium(self, retries=2, timeout=600):
        if self.chromium_user_cancelled:
            self.update_status(
                "Đã hủy tải trước đó.\nVui lòng bấm Upload lại để tiếp tục.",
                0
            )
            return False

        browser_dir = os.path.join(
            os.environ.get("LOCALAPPDATA"),
            "ms-playwright"
        )
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_dir

        # ---- kiểm tra đã có chromium chưa ----
        if os.path.isdir(browser_dir):
            for root, _, files in os.walk(browser_dir):
                if "chrome.exe" in files:
                    return True

        for attempt in range(1, retries + 1):
            self.chromium_cancel_event.clear()
            stop_event = threading.Event()

            self.update_status(
                f"Đang tải trình duyệt nền lần đầu (~150MB)\nQuá trình này chỉ diễn ra một lần.\nVui lòng không tắt ứng dụng.\n"
                f"Lần thử {attempt}/{retries}",
                0.05
            )
            self.btn_cancel_download.configure(state="normal")

            # ---- download thread ----
            def download():
                try:
                    self.chromium_download_process = subprocess.Popen(
                        [sys.executable, "-m", "playwright", "install", "chromium"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    self.chromium_download_process.wait()
                finally:
                    stop_event.set()

            threading.Thread(target=download, daemon=True).start()
            threading.Thread(
                target=self.fake_download_progress,
                args=(stop_event, self.chromium_cancel_event),
                daemon=True
            ).start()

            # ---- timeout watchdog ----
            start = time.time()
            while not stop_event.is_set():
                if self.chromium_cancel_event.is_set():
                    return False
                if time.time() - start > timeout:
                    try:
                        self.chromium_download_process.terminate()
                    except:
                        pass
                    self.update_status("Tải trình duyệt bị timeout.", 0)
                    break
                time.sleep(0.3)

            self.btn_cancel_download.configure(state="disabled")

            # ---- kiểm tra lại ----
            if os.path.isdir(browser_dir):
                for root, _, files in os.walk(browser_dir):
                    if "chrome.exe" in files:
                        self.update_status("Tải trình duyệt hoàn tất!", 1.0)
                        self.update_browser_ui_visibility()
                        return True

            self.update_status("Tải thất bại. Đang thử lại...", 0)

        self.update_status("Không thể tải trình duyệt. Vui lòng kiểm tra mạng.", 0)
        return False


    def check_playwright(self):
        """Kiểm tra xem thư viện có tồn tại không bằng cách thử import trực tiếp"""
        try:
            import playwright
            import playwright_stealth
            return True
        except ImportError:
            return False

    def setup_ui(self):
        # Header
        self.header_label = ctk.CTkLabel(self, text="AI TIKTOK VIDEO CREATOR", font=("Segoe UI", 24, "bold"))
        self.header_label.pack(pady=(20, 10))

        auth_info = (
            "🔐 XÁC THỰC TÀI KHOẢN TIKTOK\n"
            "• Ứng dụng sẽ yêu cầu đăng nhập TikTok trong lần sử dụng đầu tiên.\n"
            "• Thông tin đăng nhập được lưu an toàn trên máy của bạn.\n"
            "• Các lần sau không cần đăng nhập lại.\n"
            "• Không chia sẻ tài khoản cho bất kỳ bên thứ ba nào."
        )

        self.info_label = ctk.CTkLabel(self, text=auth_info, font=("Segoe UI", 11), text_color="#00ffcc", justify="center")
        self.info_label.pack(pady=5)

        # Hiển thị cảnh báo trực tiếp trên UI nếu thiếu thư viện
        self.lib_warning_label = ctk.CTkLabel(
            self,
            text="⚠️ Ứng dụng chưa sẵn sàng để sử dụng.\nVui lòng khởi động lại hoặc liên hệ hỗ trợ.",
            font=("Segoe UI", 12, "bold"),
            text_color="#ff4d4d"
        )
        if not self.has_playwright:
            self.lib_warning_label.pack(pady=5)

            self.btn_fix_lib = ctk.CTkButton(
                self,
                text="SỬA LỖI THƯ VIỆN NGAY",
                fg_color="#f39c12",
                hover_color="#e67e22",
                command=self.fix_libraries
            )
            self.btn_fix_lib.pack(pady=5)

        # Input Frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=40, fill="x")

        # Prompt input
        self.prompt_label = ctk.CTkLabel(self.input_frame, text="Prompt (Tiếng Việt):")
        self.prompt_label.pack(pady=(10, 0), padx=20, anchor="w")

        default_prompt = (
            "Hãy đóng vai một người cực kỳ nhiều chuyện, số nhọ, làm gì cũng hỏng và luôn gặp khó khăn trong cuộc sống. "
            "Hãy viết một dòng trạng thái (status) than vãn, kể khổ về chủ đề: ngẫu nhiên. "
            "Yêu cầu: Giọng văn phải đậm chất 'drama', hay than thân trách phận, kể lể những xui xẻo mình gặp phải và hỏi xin lời khuyên hoặc sự đồng cảm từ cộng đồng mạng. "
            "Sử dụng ngôn ngữ đời thường, có chút hờn dỗi, dùng nhiều từ cảm thán (ôi trời, sao tôi khổ thế, mệt mỏi quá...), độ dài khoảng 40-90 chữ. "
            "Chỉ trả về nội dung status bằng tiếng Việt, không thêm bất kỳ văn bản dẫn nhập nào khác."
        )

        self.default_prompt = default_prompt
        self.prompt_entry = ctk.CTkTextbox(self.input_frame, height=100, wrap="word")
        self.prompt_entry.insert("1.0", self.default_prompt)
        self.prompt_entry.pack(pady=(5, 15), padx=20, fill="both")

        # TikTok Upload Option
        self.upload_var = ctk.BooleanVar(value=True)
        self.upload_checkbox = ctk.CTkCheckBox(
            self,
            text="Tự động đăng video lên TikTok",
            variable=self.upload_var,
            font=("Segoe UI", 12)
        )
        self.upload_checkbox.pack(pady=5)

        # Chọn ngẫu nhiên video nền
        self.set_random_video()

        # Action Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=(15, 6))

        self.btn_run = ctk.CTkButton(
            btn_frame,
            text="TẠO VIDEO TIKTOK",
            command=self.start_process,
            height=50,
            width=220,
            font=("Segoe UI", 16, "bold"),
            fg_color="#fe2c55"
        )
        self.btn_run.grid(row=0, column=0, padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="DỪNG TẠO VIDEO",
            command=self.request_stop,
            height=50,
            width=140,
            font=("Segoe UI", 12, "bold"),
            fg_color="#6b6b6b"
        )
        self.btn_stop.grid(row=0, column=1)
        self.btn_stop.configure(state="disabled")

        # Nút Upload riêng biệt
        self.btn_upload_only = ctk.CTkButton(
            self,
            text="CHỈ UPLOAD VIDEO MỚI NHẤT",
            command=self.start_upload_only,
            height=40,
            width=300,
            font=("Segoe UI", 13, "bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71"
        )
        self.btn_upload_only.pack(pady=10)

        # Number of videos input
        qty_frame = ctk.CTkFrame(self)
        qty_frame.pack(pady=(6, 0))

        self.qty_label = ctk.CTkLabel(qty_frame, text="Số lượng video:")
        self.qty_label.grid(row=0, column=0, padx=(0, 8))
        self.qty_entry = ctk.CTkEntry(qty_frame, width=80)
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=0, column=1)

        # Status & Progress
        self.status_label = ctk.CTkLabel(self, text="Trạng thái: Sẵn sàng", text_color="#aaaaaa", wraplength=600)
        self.status_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        self.btn_cancel_download = ctk.CTkButton(
            self,
            text="HỦY TẢI TRÌNH DUYỆT",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=self.cancel_chromium_download
        )
        self.btn_cancel_download.pack(pady=5)
        self.btn_cancel_download.configure(state="disabled")


    def fix_libraries(self):
        """Tự động chạy lệnh cài đặt pip cho phiên bản Python hiện tại"""
        self.update_status("Đang cài đặt... Kiểm tra console (VS Code) để xem chi tiết.")
        def run_fix():
            try:
                # Chạy pip install bằng chính trình thông dịch đang chạy script
                subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "playwright-stealth"])
                subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "playwright-stealth", "browser-cookie3"])
                # Cài đặt trình duyệt chromium
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

                # Cập nhật lại trạng thái
                self.has_playwright = self.check_playwright()
                if self.has_playwright:
                    self.lib_warning_label.pack_forget()
                    if hasattr(self, 'btn_fix_lib'): self.btn_fix_lib.pack_forget()
                    self.update_status("Cài đặt thành công!")
                else:
                    self.update_status("Cài đặt xong nhưng hệ thống chưa nhận diện. Vui lòng mở lại App.")

                print("--- CÀI ĐẶT HOÀN TẤT THÀNH CÔNG ---")
            except Exception as e:
                self.update_status("Lỗi cài đặt thư viện. Kiểm tra console để xem chi tiết.")
                print("-" * 30)
                print("LỖI CÀI ĐẶT THƯ VIỆN:")
                traceback.print_exc()
                print("-" * 30)

        threading.Thread(target=run_fix, daemon=True).start()

    def set_random_video(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        input_dir = os.path.join(script_dir, "input")
        exts = (".mp4", ".mov", ".avi", ".mkv")
        candidates = []
        if os.path.isdir(input_dir):
            for fn in os.listdir(input_dir):
                if fn.lower().endswith(exts):
                    candidates.append(os.path.join(input_dir, fn))
        if candidates:
            self.video_path = random.choice(candidates)

    def update_status(self, text, progress=None):
        self.status_label.configure(text=f"Trạng thái: {text}")
        if progress is not None:
            self.progress_bar.set(progress)

    def split_text(self, text, max_chars_per_line=22):
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
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
        last_exception = None
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                return response.text.strip().replace('"', '')
            except Exception:
                last_exception = sys.exc_info()
                continue
        if last_exception:
            print("--- LỖI GOOGLE GEMINI API ---")
            traceback.print_exception(*last_exception)
            print("-" * 30)
        raise Exception("Không thể kết nối với Gemini API.")

    # ===== PLAYWRIGHT PERSISTENT PROFILE =====
    def get_pw_profile_dir(self):
        if getattr(sys, 'frozen', False):
            base = os.path.join(
                os.environ.get("APPDATA"),
                "TikTokVideoAI",
                "pw_profile"
            )
        else:
            base = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "pw_profile"
            )

        os.makedirs(base, exist_ok=True)
        return base


    def upload_to_tiktok_playwright(self, video_path, description):
        # ⭐ BẮT BUỘC: set path browser TRƯỚC khi import playwright
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
            os.environ.get("LOCALAPPDATA"),
            "ms-playwright"
        )

        # ⭐ Đảm bảo Chromium tồn tại (tự tải nếu thiếu)
        if not self.ensure_playwright_chromium():
            self.update_status("Không thể tải Chromium.")
            return False

        if not self.check_playwright():
            print("LỖI: Playwright chưa sẵn sàng.")
            return False

        from playwright.sync_api import sync_playwright
        import playwright_stealth

        profile_dir = self.get_pw_profile_dir()

        try:

            with sync_playwright() as p:
                # ⭐ Persistent Context: GIỮ COOKIE + LOGIN
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

                # ⭐ LẦN ĐẦU: yêu cầu login thủ công (chỉ 1 lần)
                if "login" in page.url:
                    self.update_status("Vui lòng đăng nhập TikTok để tiếp tục...")
                    try:
                        page.wait_for_url("**/tiktokstudio/upload", timeout=600000)
                    except:
                        print("Login timeout")
                        context.close()
                        return False

                # ---------------- Upload video ----------------
                self.update_status("Đang tải video...")
                file_input = page.locator('input[type="file"]')
                file_input.wait_for(state="attached", timeout=60000)
                file_input.set_input_files(video_path)

                # ---------------- Caption ----------------
                self.update_status("Đang nhập mô tả...")
                caption = page.locator('.notranslate.public-DraftEditor-content')
                caption.wait_for(state="visible", timeout=60000)
                caption.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(description)

                # ---------------- Post ----------------
                self.update_status("Chờ xử lý video...")
                post_btn = page.locator('button[data-e2e="post_video_button"]')

                start = time.time()
                while time.time() - start < 300:
                    if post_btn.is_visible() and post_btn.is_enabled():
                        if "Uploading" not in post_btn.inner_text():
                            break
                    time.sleep(3)

                post_btn.click()
                self.update_status("Đã nhấn nút Đăng!")

                time.sleep(15)
                context.close()
                return True

        except Exception:
            print("-" * 30)
            print("LỖI TIKTOK UPLOAD (PERSISTENT CONTEXT):")
            traceback.print_exc()
            print("-" * 30)
            return False

    def start_upload_only(self):
        """Logic tìm video mới nhất trong output và upload"""
        if self.is_processing:
            return

        self.has_playwright = self.check_playwright()
        if not self.has_playwright:
            self.update_status("Lỗi: Thiếu thư viện Playwright.")
            return

        output_dir = os.path.join(os.path.dirname(__file__), "output")
        if not os.path.isdir(output_dir):
            self.update_status("Lỗi: Không tìm thấy thư mục output.")
            return

        # Tìm video mới nhất
        files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".mp4")]
        if not files:
            self.update_status("Lỗi: Không có video nào trong thư mục output.")
            return

        latest_video = max(files, key=os.path.getctime)
        filename = os.path.basename(latest_video)

        self.update_status(f"Đang chuẩn bị upload: {filename}")
        self.btn_upload_only.configure(state="disabled")
        self.is_processing = True

        def run_upload_task():
            self.update_browser_ui_visibility()
            self.chromium_user_cancelled = False
            self.chromium_cancel_event.clear()
            try:
                description = "Chia sẻ khoảnh khắc thú vị trong ngày của tôi. Hy vọng mọi người thích video này! #trending #xuhuong #dailyvlog #fyp"
                success = self.upload_to_tiktok_playwright(latest_video, description)
                if success:
                    self.update_status("Upload video cũ thành công!")
                else:
                    self.update_status("Upload thất bại. Kiểm tra console.")
            finally:
                self.is_processing = False
                self.btn_upload_only.configure(state="normal")

        threading.Thread(target=run_upload_task, daemon=True).start()

    def start_process(self):
        if not GEMINI_API_KEY:
            self.update_status("Lỗi: Thiếu API KEY.", 0)
            print("CẢNH BÁO: Chưa cấu hình GEMINI_API_KEY trong file .env")
            return

        self.has_playwright = self.check_playwright()
        if not self.has_playwright:
            self.update_status("Lỗi: Thiếu thư viện hệ thống.", 0)
            return

        prompt_text = self.prompt_entry.get("1.0", "end").strip() or self.default_prompt
        if not self.video_path:
            self.update_status("Lỗi: Không tìm thấy video nền.", 0)
            return

        try:
            count = int(self.qty_entry.get())
        except:
            count = 1

        self.is_processing = True
        self.stop_requested = False
        self.target_count = count
        self.btn_run.configure(state="disabled", text="ĐANG XỬ LÝ...")
        self.btn_upload_only.configure(state="disabled")
        if count > 1: self.btn_stop.configure(state="normal")

        thread = threading.Thread(target=self.run_logic, args=(prompt_text, count))
        thread.daemon = True
        thread.start()

    def request_stop(self):
        self.stop_requested = True
        self.update_status("Đang dừng...")
        self.btn_stop.configure(state="disabled")

    def run_logic(self, prompt_text, count):
        try:
            for i in range(count):
                self.set_random_video()
                if not self.video_path or self.stop_requested: break

                self.update_status(f"({i+1}/{count}) Đang tạo nội dung...", 0.1)
                prompt = prompt_text.replace("{topic}", "ngẫu nhiên")
                raw_content = self.generate_content_with_fallback(prompt)
                display_text = self.split_text(raw_content, max_chars_per_line=22)

                self.update_status(f"({i+1}/{count}) Đang render video...", 0.4)
                clip = VideoFileClip(self.video_path)
                duration = min(clip.duration, 15)
                clip = clip.subclipped(0, duration)

                target_w, target_h = 720, 1280
                background = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration)
                video_resized = clip.resized(width=int(target_w))
                video_centered = video_resized.with_position(('center', 'center'))

                txt_clip = TextClip(
                    text=display_text, font_size=50, color='white', font='font.ttf',
                    method='caption', size=(int(target_w * 0.9), None),
                    stroke_color='black', stroke_width=2, text_align='center'
                ).with_duration(duration).with_position(('center', 'center'))

                final_video = CompositeVideoClip([background, video_centered, txt_clip], size=(target_w, target_h))

                ts = time.strftime("%Y%m%d%H%M%S")
                output_name = f"tiktok_{ts}.mp4"
                output_dir = os.path.join(os.path.dirname(__file__), "output")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.abspath(os.path.join(output_dir, output_name))

                final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

                if self.upload_var.get():
                    full_description = f"{raw_content}\n\n#tamtrang #sốnhọ #drama #funny"
                    self.update_status(f"({i+1}/{count}) Đang đăng TikTok...", 0.8)

                    success = self.upload_to_tiktok_playwright(output_path, full_description)

                    if success:
                        self.update_status(f"({i+1}/{count}) Đăng thành công!", 1.0)
                    else:
                        self.update_status(f"({i+1}/{count}) Upload không thành công.", 0.5)

                if self.stop_requested: break

                if i < count - 1:
                    wait_time = random.randint(30, 60)
                    for _ in range(wait_time):
                        if self.stop_requested: break
                        self.update_status(f"Nghỉ an toàn {wait_time- _}s...", 0)
                        time.sleep(1)

        except Exception:
            self.update_status("Đã xảy ra lỗi hệ thống.", 0)
            print("-" * 30)
            print("LỖI QUY TRÌNH CHÍNH (MAIN LOGIC):")
            traceback.print_exc()
            print("-" * 30)
        finally:
            self.is_processing = False
            self.btn_run.configure(state="normal", text="TẠO VIDEO TIKTOK")
            self.btn_upload_only.configure(state="normal")
            self.btn_stop.configure(state="disabled")

if __name__ == "__main__":
    app = VideoAIApp()
    app.mainloop()
