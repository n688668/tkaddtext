import io
import sys
import os
import requests
import zipfile
import threading
import time
import random
import json
import sys
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
    # Sẽ được xử lý trong phần fix_libraries
    pass

# 1. Nạp biến môi trường từ file .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cấu hình Client Gemini
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except:
        client = None
else:
    client = None

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

        # Thư mục input luôn nằm cùng cấp với Base Directory
        self.input_dir = os.path.join(self.base_dir, "input")
        self.output_dir = os.path.join(self.base_dir, "output")

        # Tự động tạo thư mục nếu chưa có để tránh lỗi
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Đặt đường dẫn trình duyệt ngay lập tức
        self.browser_base_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = self.browser_base_path

        self.title("AI TikTok Video Generator")
        self.geometry("750x750")

        self.video_path = ""
        self.is_processing = False
        self.stop_requested = False
        self.target_count = 0

        # Khởi tạo UI trước khi kiểm tra logic
        self.setup_ui()

        # Ẩn các thông báo lỗi ban đầu
        self.btn_fix_lib.pack_forget()
        self.lib_warning_label.pack_forget()
        self.magick_link_label.pack_forget()

        # Chạy kiểm tra bất đồng bộ sau khi UI hiển thị
        self.after(500, self.async_check_at_startup)

    def has_playwright_chromium(self):
        """Kiểm tra file thực thi chrome.exe"""
        if not os.path.isdir(self.browser_base_path):
            return False
        for root, _, files in os.walk(self.browser_base_path):
            if "chrome.exe" in files:
                return True
        return False

    def check_playwright_lib(self):
        """Kiểm tra thư viện python"""
        try:
            import playwright
            import playwright_stealth
            return True
        except ImportError:
            return False

    def async_check_at_startup(self):
        def task():
            # 1. Thử tìm ImageMagick tự động
            has_magick = self.check_imagemagick_installed()

            # 2. Kiểm tra Browser
            has_lib = self.check_playwright_lib()
            has_browser = self.has_playwright_chromium()

            if not (has_lib and has_browser and has_magick):
                self.after(0, lambda: self.show_fix_ui(not has_magick, not has_browser))
            else:
                self.after(0, lambda: self.update_status("Hệ thống đã sẵn sàng"))

        threading.Thread(target=task, daemon=True).start()

    def check_imagemagick_installed(self):
        """Kiểm tra ImageMagick trong PATH hoặc AppData"""
        # Kiểm tra trong biến môi trường hệ thống trước
        try:
            # Chạy thử lệnh magick -version
            subprocess.run(["magick", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except:
            pass

        # Kiểm tra trong thư mục cục bộ của App nếu có
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

    def show_fix_ui(self, missing_magick, missing_browser):
        msg = "⚠️ Hệ thống chưa đủ điều kiện:\n"
        if missing_browser:
            msg += "• Thiếu Browser (Nhấn nút cài đặt bên dưới)\n"
            self.btn_fix_lib.pack(pady=5)

        if missing_magick:
            msg += "• Thiếu ImageMagick (Bắt buộc để chèn chữ)\n"
            self.magick_link_label.pack(pady=5)

        self.lib_warning_label.configure(text=msg)
        self.lib_warning_label.pack(pady=5)
        self.update_status("Yêu cầu cài đặt môi trường")

    def setup_ui(self):
        # Header
        self.header_label = ctk.CTkLabel(self, text="AI TIKTOK VIDEO CREATOR", font=("Segoe UI", 24, "bold"))
        self.header_label.pack(pady=(20, 10))

        auth_info = "XÁC THỰC TÀI KHOẢN TIKTOK\n• Ứng dụng sẽ yêu cầu đăng nhập lần đầu.\n• Thông tin được lưu an toàn trên máy bạn."
        self.info_label = ctk.CTkLabel(self, text=auth_info, font=("Segoe UI", 11), text_color="#00ffcc", justify="center")
        self.info_label.pack(pady=5)

        self.lib_warning_label = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 12, "bold"), text_color="#ff4d4d"
        )

        # Link tải ImageMagick
        self.magick_link_label = ctk.CTkTextbox(self, height=60, width=500, fg_color="transparent", text_color="#3498db")
        self.magick_link_label.insert("1.0", "Tải ImageMagick tại đây, cài xong hãy mở lại App:\nhttps://imagemagick.org/script/download.php#windows")
        self.magick_link_label.configure(state="disabled")

        self.btn_fix_lib = ctk.CTkButton(
            self, text="CÀI ĐẶT MÔI TRƯỜNG (TRÌNH DUYỆT)", fg_color="#f39c12",
            hover_color="#e67e22", command=self.fix_libraries
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
        self.prompt_entry.pack(pady=(5, 15), padx=20, fill="both")

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

        # Chọn ngẫu nhiên video nền
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

        # 2. Nút Mở thư mục INPUT (MỚI THÊM)
        self.btn_open_input = ctk.CTkButton(secondary_btn_frame, text="THƯ MỤC INPUT", command=self.open_input_folder, height=40, width=160, font=("Segoe UI", 12, "bold"), fg_color="#8e44ad", hover_color="#9b59b6")
        self.btn_open_input.grid(row=0, column=1, padx=5)

        # 3. Nút Mở thư mục OUTPUT
        self.btn_open_folder = ctk.CTkButton(secondary_btn_frame, text="THƯ MỤC OUTPUT", command=self.open_output_folder, height=40, width=160, font=("Segoe UI", 12, "bold"), fg_color="#34495e", hover_color="#2c3e50")
        self.btn_open_folder.grid(row=0, column=2, padx=5)

        # Status & Progress
        self.status_label = ctk.CTkLabel(self, text="Trạng thái: Đang kiểm tra hệ thống...", text_color="#aaaaaa", wraplength=600)
        self.status_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

    def fix_libraries(self):
        """NÚT CÀI ĐẶT MÔI TRƯỜNG TỔNG HỢP"""
        self.btn_fix_lib.configure(state="disabled", text="ĐANG CÀI ĐẶT...")

        def run_fix():
            try:
                # Cài đặt Chromium (Chỉ tải nếu chưa có)
                if not self.has_playwright_chromium():
                    self.update_status("Đang tải trình duyệt Chromium (~150MB)...")
                    subprocess.check_call(["playwright", "install", "chromium"], shell=True)
                else:
                    self.update_status(" Trình duyệt đã có sẵn.")

            except Exception as e:
                self.update_status(f"Lỗi cài đặt: {str(e)}")
                traceback.print_exc()
            finally:
                self.after(0, lambda: self.btn_fix_lib.configure(state="normal", text="CÀI ĐẶT MÔI TRƯỜNG"))

        threading.Thread(target=run_fix, daemon=True).start()

    def extract_archive(self, file_source, target_dir):
        """Giải nén tự động cho cả file .zip và .7z"""
        os.makedirs(target_dir, exist_ok=True)

        if isinstance(file_source, bytes):
            stream = io.BytesIO(file_source)
        else:
            stream = open(file_source, "rb")

        try:
            import py7zr
            with py7zr.SevenZipFile(stream, mode='r') as z:
                z.extractall(target_dir)
            return True
        except Exception as e:
            traceback.print_exc()
            return False
        finally:
            if not isinstance(file_source, bytes): stream.close()

    def update_status(self, text, progress=None):
        if hasattr(self, 'status_label'):
            self.status_label.configure(text=f"Trạng thái: {text}")

        if hasattr(self, 'progress_bar'):
            if progress is not None:
                # Nếu có giá trị progress, đảm bảo thanh bar đang hiện
                if not self.progress_bar.winfo_viewable():
                    self.progress_bar.pack(pady=10)
                self.progress_bar.set(progress)
            else:
                # Nếu không có progress (ví dụ lúc chờ), có thể ẩn đi cho đẹp
                self.progress_bar.pack_forget()
                pass

    def open_output_folder(self):
        os.startfile(self.output_dir)

    def open_input_folder(self):
        os.startfile(self.input_dir)

    def set_random_video(self):
        candidates = [os.path.join(self.input_dir, f) for f in os.listdir(self.input_dir) if f.lower().endswith((".mp4", ".mov", ".avi"))]
        if candidates:
            self.video_path = random.choice(candidates)

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
        if not client: raise Exception("API Key chưa cấu hình.")
        for model_name in ["gemini-2.0-flash", "gemini-2.5-flash"]:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                return response.text.strip().replace('"', '')
            except: continue
        raise Exception("Không thể kết nối Gemini API.")

    def get_pw_profile_dir(self):
        path = os.path.join(os.environ.get("APPDATA", ""), "TikTokVideoAI", "pw_profile")
        os.makedirs(path, exist_ok=True)
        return path

    def upload_to_tiktok_playwright(self, video_path, description):
        from playwright.sync_api import sync_playwright
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

                if "login" in page.url:
                    self.update_status("Vui lòng đăng nhập TikTok trên trình duyệt để tiếp tục...")
                    try:
                        page.wait_for_url("**/tiktokstudio/upload", timeout=600000)
                    except:
                        print("Login timeout")
                        context.close()
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

    def start_manual_upload(self):
        """Mở chọn file tại đúng thư mục lưu video và upload"""
        if self.is_processing:
            return

        # Mở hộp thoại chọn file
        selected_file = filedialog.askopenfilename(
            initialdir=self.output_dir,
            title="Chọn video để upload",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv")]
        )

        if not selected_file:
            return

        filename = os.path.basename(selected_file)
        self.update_status(f"Đang chuẩn bị upload: {filename}")
        self.btn_upload_manual.configure(state="disabled")
        self.is_processing = True

        def run_upload_task():
            self.update_browser_ui_visibility()
            try:
                description = "Khoảnh khắc thú vị! #trending #xuhuong #dailyvlog #cuocsong"
                success = self.upload_to_tiktok_playwright(selected_file, description)
                if success:
                    self.update_status("Upload thành công!")
                else:
                    self.update_status("Upload thất bại. Kiểm tra console.")
            finally:
                self.is_processing = False
                self.btn_upload_manual.configure(state="normal")

        threading.Thread(target=run_upload_task, daemon=True).start()

    def request_stop(self):
        self.stop_requested = True
        self.update_status("Đang dừng...")
        self.btn_stop.configure(state="disabled")

    def start_process(self):
        if not GEMINI_API_KEY:
            self.update_status("Lỗi: Thiếu API KEY.", 0)
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
        self.btn_upload_manual.configure(state="disabled")
        if count > 1: self.btn_stop.configure(state="normal")

        thread = threading.Thread(target=self.run_logic, args=(prompt_text, count))
        thread.daemon = True
        thread.start()

    def run_logic(self, prompt_text, count):
        try:
            for i in range(count):
                if self.stop_requested: break
                self.set_random_video()
                if not self.video_path: break

                self.update_status(f"({i+1}/{count}) Đang tạo nội dung...", 0.1)
                raw_content = self.generate_content_with_fallback(prompt_text)
                display_text = self.split_text(raw_content, max_chars_per_line=22)

                self.update_status(f"({i+1}/{count}) Đang render video...", 0.4)
                clip = VideoFileClip(self.video_path)
                duration = min(clip.duration, 15)
                clip = clip.subclipped(0, duration)

                target_w, target_h = 720, 1280
                background = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration)
                video_resized = clip.resized(width=int(target_w))
                video_centered = video_resized.with_position(('center', 'center'))

                # Tìm font
                def get_resource_path(relative_path):
                    if hasattr(sys, '_MEIPASS'):
                        return os.path.join(sys._MEIPASS, relative_path)
                    return os.path.join(os.path.abspath("."), relative_path)

                # Khi dùng font:
                font_path = get_resource_path("font.ttf")

                txt_clip = TextClip(
                    text=display_text, font_size=50, color='white', font=font_path,
                    method='caption', size=(int(target_w * 0.9), None),
                    stroke_color='black', stroke_width=2, text_align='center'
                ).with_duration(duration).with_position(('center', 'center'))

                final_video = CompositeVideoClip([background, video_centered, txt_clip], size=(target_w, target_h))

                ts = time.strftime("%Y%m%d%H%M%S")
                output_name = f"tiktok_{ts}.mp4"
                output_path = os.path.abspath(os.path.join(self.output_dir, output_name))

                try:
                    final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

                    if self.upload_var.get():
                        full_description = f"{raw_content}\n\n#tamtrang #cuocsong #trend #tamsu"
                        self.update_status(f"({i+1}/{count}) Đang đăng TikTok...", 0.8)
                        success = self.upload_to_tiktok_playwright(output_path, full_description)
                        if success:
                            self.update_status(f"({i+1}/{count}) Đăng thành công!", 1.0)
                        else:
                            self.update_status(f"({i+1}/{count}) Upload không thành công.", 0.5)
                finally:
                    # Đảm bảo luôn đóng clip dù thành công hay thất bại
                    if 'final_video' in locals(): final_video.close()
                    if 'clip' in locals(): clip.close()

                if self.stop_requested: break

                if i < count - 1:
                    wait_time = random.randint(30, 60)
                    for _ in range(wait_time):
                        if self.stop_requested: break
                        self.update_status(f"Nghỉ an toàn {wait_time- _}s...", 0)
                        time.sleep(1)

        except Exception:
            self.update_status("Đã xảy ra lỗi hệ thống.", 0)
            traceback.print_exc()
        finally:
            self.is_processing = False
            self.btn_run.configure(state="normal", text="TẠO VIDEO TIKTOK", height=50, width=220, font=("Segoe UI", 16, "bold"), fg_color="#fe2c55")
            self.btn_upload_manual.configure(state="normal", height=40, width=160, font=("Segoe UI", 12, "bold"), fg_color="#27ae60", hover_color="#2ecc71")
            self.btn_stop.configure(state="disabled", height=50, width=140, font=("Segoe UI", 12, "bold"), fg_color="#6b6b6b")

if __name__ == "__main__":
    app = VideoAIApp()
    app.mainloop()
