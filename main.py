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

# Thêm thư viện lấy cookie từ trình duyệt
try:
    import browser_cookie3
except ImportError:
    browser_cookie3 = None

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
    def __init__(self):
        super().__init__()

        self.title("AI TikTok Video Creator Pro (Playwright Edition)")
        self.geometry("750x850")

        self.video_path = ""
        self.is_processing = False
        self.stop_requested = False
        self.target_count = 0

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
        self.header_label = ctk.CTkLabel(self, text="TIKTOK VIDEO AI GENERATOR", font=("Segoe UI", 24, "bold"))
        self.header_label.pack(pady=(20, 10))

        # Hướng dẫn xử lý Playwright
        auth_info = (
            "🚀 HỆ THỐNG TỰ ĐỘNG HÓA PLAYWRIGHT\n"
            "• Ưu tiên dùng cookies.txt (nếu có).\n"
            "• Nếu không có file, App sẽ tự lấy cookie từ trình duyệt (Chrome/Edge).\n"
            "• Vui lòng đăng nhập TikTok trên trình duyệt trước."
        )
        self.info_label = ctk.CTkLabel(self, text=auth_info, font=("Segoe UI", 11), text_color="#00ffcc", justify="center")
        self.info_label.pack(pady=5)

        # Hiển thị cảnh báo trực tiếp trên UI nếu thiếu thư viện
        self.lib_warning_label = ctk.CTkLabel(
            self,
            text="⚠️ CẢNH BÁO: CHƯA CÀI ĐẶT THƯ VIỆN CẦN THIẾT\nNếu bạn vừa cài xong, hãy thử nhấn nút Tạo Video.",
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
            text="Tự động đăng lên TikTok (Playwright - Hiện trình duyệt)",
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

    def get_browser_cookies(self):
        """Tự động lấy cookies TikTok từ trình duyệt đang mở"""
        if not browser_cookie3:
            print("Cảnh báo: Thư viện browser-cookie3 chưa được cài đặt.")
            return None

        try:
            print("Đang thử lấy cookies từ trình duyệt...")
            # Thử lấy từ Chrome trước, nếu không có thử các trình duyệt khác
            cj = None
            try:
                cj = browser_cookie3.chrome(domain_name='.tiktok.com')
            except:
                try:
                    cj = browser_cookie3.load(domain_name='.tiktok.com')
                except:
                    pass

            if not cj:
                return None

            formatted_cookies = []
            for cookie in cj:
                formatted_cookies.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'expires': cookie.expires,
                    'httpOnly': False, # Mặc định
                    'secure': cookie.secure,
                    'sameSite': 'Lax'
                })
            print(f"Đã lấy thành công {len(formatted_cookies)} cookies từ trình duyệt.")
            return formatted_cookies
        except Exception as e:
            print(f"Không thể tự động lấy cookies: {e}")
            return None

    def upload_to_tiktok_playwright(self, video_path, description):
        if not self.check_playwright():
            print("LỖI: Thư viện Playwright chưa được cài đặt đúng cách.")
            return False

        from playwright.sync_api import sync_playwright
        import playwright_stealth

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )

                # Logic lấy cookie linh hoạt
                loaded_cookies = None

                # 1. Thử đọc từ file cookies.txt (Ưu tiên nhất)
                if os.path.exists("cookies.txt"):
                    try:
                        with open("cookies.txt", "r", encoding="utf-8") as f:
                            raw_cookies = json.load(f)
                            loaded_cookies = []
                            for c in raw_cookies:
                                if 'sameSite' in c and c['sameSite']:
                                    c['sameSite'] = str(c['sameSite']).capitalize()
                                    if c['sameSite'] not in ["Strict", "Lax", "None"]:
                                        c['sameSite'] = "Lax"
                                loaded_cookies.append(c)
                            print("Sử dụng cookies từ file cookies.txt")
                    except Exception as e:
                        print(f"Lỗi đọc file cookie: {e}")

                # 2. Nếu không có file, thử lấy từ trình duyệt
                if not loaded_cookies:
                    loaded_cookies = self.get_browser_cookies()

                # 3. Áp dụng cookies nếu tìm thấy
                if loaded_cookies:
                    try:
                        context.add_cookies(loaded_cookies)
                    except Exception as e:
                        print(f"Không thể áp dụng cookies vào trình duyệt: {e}")
                else:
                    print("Cảnh báo: Không tìm thấy bất kỳ nguồn cookies nào. Bạn có thể cần đăng nhập thủ công.")

                page = context.new_page()
                page.set_default_timeout(90000)

                # Kích hoạt Stealth để tránh bị phát hiện bot
                try:
                    playwright_stealth.stealth(page)
                except Exception as stealth_err:
                    print(f"Cảnh báo: Không thể kích hoạt Stealth: {stealth_err}")

                self.update_status("Đang truy cập TikTok...")
                page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until="domcontentloaded", timeout=90000)

                # Nếu trang yêu cầu đăng nhập (do cookie hết hạn hoặc không có)
                if "login" in page.url:
                    self.update_status("Vui lòng đăng nhập TikTok trên trình duyệt hiện ra...")
                    # Chờ cho đến khi người dùng đăng nhập xong và chuyển hướng về trang upload
                    try:
                        page.wait_for_url("**/tiktokstudio/upload", timeout=300000)
                    except:
                        print("Hết thời gian chờ đăng nhập.")
                        browser.close()
                        return False

                time.sleep(5)

                self.update_status("Đang tải video...")
                file_input = page.locator('input[type="file"]')
                file_input.wait_for(state="attached", timeout=60000)
                file_input.set_input_files(video_path)

                self.update_status("Đang nhập mô tả...")
                caption_container = page.locator('.notranslate.public-DraftEditor-content')
                caption_container.wait_for(state="visible", timeout=60000)

                caption_container.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(description)
                time.sleep(2)

                self.update_status("Chờ video tải xong để đăng...")
                post_btn = page.locator('button[data-e2e="post_video_button"]')

                start_wait = time.time()
                while time.time() - start_wait < 300:
                    if post_btn.is_visible() and post_btn.is_enabled():
                        if "Uploading" not in post_btn.inner_text():
                            break
                    time.sleep(3)

                post_btn.click()
                self.update_status("Đã nhấn nút Đăng!")

                time.sleep(15)
                browser.close()
                return True
        except Exception:
            print("-" * 30)
            print("LỖI TIKTOK UPLOAD (PLAYWRIGHT):")
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
