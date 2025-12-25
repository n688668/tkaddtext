import os
import threading
import time
import random
import re
import customtkinter as ctk
from google import genai
from dotenv import load_dotenv
# Cập nhật cách import cho MoviePy 2.0+
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- IMPORT THÊM CHO TIKTOK ---
try:
    from tiktok_uploader.upload import upload_video
    from tiktok_uploader.auth import AuthBackend
    HAS_TIKTOK_LIB = True
except ImportError:
    HAS_TIKTOK_LIB = False
    print("CẢNH BÁO: Thư viện tiktok-uploader chưa được cài đặt!")

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

        self.title("AI TikTok Video Creator Pro")
        self.geometry("750x700")

        self.video_path = ""
        self.is_processing = False
        self.stop_requested = False
        self.target_count = 0

        # Khởi tạo UI
        self.setup_ui()

    def setup_ui(self):
        # Header
        self.header_label = ctk.CTkLabel(self, text="TIKTOK VIDEO AI GENERATOR", font=("Segoe UI", 24, "bold"))
        self.header_label.pack(pady=(20, 10))

        # Hướng dẫn xử lý lỗi Auth & Selenium
        auth_info = (
            "⚠️ LƯU Ý KHI VIDEO ĐÃ LÊN NHƯNG BÁO LỖI: \n"
            "1. Nếu bạn thấy video đã xuất hiện trên TikTok (kể cả chờ duyệt), hãy kệ nó.\n"
            "2. Tool đã được cập nhật để ĐỢI 20 GIÂY sau khi nhấn Post nhằm tránh lỗi Stale.\n"
            "3. Nếu trình duyệt đóng ngay khi vừa bấm Post, hãy kiểm tra lại file cookies.txt."
        )
        self.info_label = ctk.CTkLabel(self, text=auth_info, font=("Segoe UI", 11), text_color="#ffcc00", justify="center")
        self.info_label.pack(pady=5)

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
        self.upload_var = ctk.BooleanVar(value=False)
        self.upload_checkbox = ctk.CTkCheckBox(
            self,
            text="Tự động đăng lên TikTok (Hiện trình duyệt)",
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
            except Exception as e:
                last_exception = e
                continue
        raise last_exception

    def start_process(self):
        if not GEMINI_API_KEY:
            self.update_status("Lỗi: Không tìm thấy GEMINI_API_KEY", 0)
            return

        prompt_text = self.prompt_entry.get("1.0", "end").strip() or self.default_prompt
        if not self.video_path:
            self.update_status("Thiếu dữ liệu: Vui lòng đảm bảo có video nền.", 0)
            return

        try:
            count = int(self.qty_entry.get())
        except:
            count = 1

        self.is_processing = True
        self.stop_requested = False
        self.target_count = count
        self.btn_run.configure(state="disabled", text="ĐANG XỬ LÝ...")
        if count > 1: self.btn_stop.configure(state="normal")

        thread = threading.Thread(target=self.run_logic, args=(prompt_text, count))
        thread.daemon = True
        thread.start()

    def request_stop(self):
        self.stop_requested = True
        self.update_status("Yêu cầu dừng: sẽ dừng sau video hiện tại.")
        self.btn_stop.configure(state="disabled")

    def run_logic(self, prompt_text, count):
        try:
            for i in range(count):
                self.set_random_video()
                if not self.video_path or self.stop_requested: break

                # Bước 1: Tạo nội dung
                self.update_status(f"({i+1}/{count}) Đang sáng tạo nội dung AI...", 0.1)
                prompt = prompt_text.replace("{topic}", "ngẫu nhiên")
                raw_content = self.generate_content_with_fallback(prompt)
                display_text = self.split_text(raw_content, max_chars_per_line=22)

                # Bước 2: Render video
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
                output_path = os.path.join(output_dir, output_name)

                final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

                # Bước 3: Upload TikTok
                if self.upload_var.get():
                    if not HAS_TIKTOK_LIB:
                        self.update_status("LỖI: Chưa cài 'tiktok-uploader'.", 0)
                    elif not os.path.exists("cookies.txt"):
                        self.update_status("LỖI: Thiếu file 'cookies.txt'!", 0)
                    else:
                        full_description = f"{raw_content}\n\n#tamtrang #sốnhọ #drama #ai_bot"

                        # Chỉ thử upload, nếu gặp lỗi sau khi đã bấm post thì bỏ qua
                        self.update_status(f"({i+1}/{count}) Đang upload lên TikTok...", 0.8)
                        try:
                            # Đảm bảo nghỉ 1 chút trước khi bắt đầu
                            time.sleep(3)

                            success = upload_video(
                                output_path,
                                description=full_description,
                                cookies='cookies.txt',
                                headless=False,
                                browser='chrome'
                            )

                            # Sau khi hàm upload_video chạy xong, chúng ta ép trình duyệt đợi thêm
                            # để TikTok xử lý xong yêu cầu POST video trước khi thư viện đóng trình duyệt
                            self.update_status("Đợi TikTok xác nhận (20s)...", 0.9)
                            time.sleep(20)

                            if success:
                                self.update_status(f"({i+1}/{count}) Đăng thành công!", 1.0)
                            else:
                                # Kiểm tra xem video có thực sự đã lên chưa (thư viện đôi khi báo False nhầm)
                                self.update_status(f"({i+1}/{count}) Kiểm tra lại kênh TikTok của bạn.", 1.0)

                        except Exception as e:
                            err_msg = str(e)
                            # Nếu lỗi xảy ra NHƯNG video thực tế đã được gửi đi (stale element thường gặp ở bước cuối)
                            if "stale" in err_msg.lower() or "element" in err_msg.lower():
                                print(f"Cảnh báo Stale Element nhưng có thể video đã lên: {err_msg}")
                                self.update_status(f"({i+1}/{count}) Video có thể đã lên (Chờ duyệt).", 1.0)
                                time.sleep(10) # Nghỉ thêm để ổn định
                            else:
                                self.update_status(f"Lỗi upload: {err_msg[:30]}", 0)
                                time.sleep(5)

                self.update_status(f"({i+1}/{count}) Hoàn thành video {i+1}", 1.0)
                if self.stop_requested: break

                if i < count - 1:
                    wait_time = random.randint(60, 120)
                    for _ in range(wait_time):
                        if self.stop_requested: break
                        self.update_status(f"Nghỉ an toàn {wait_time- _}s...", 0)
                        time.sleep(1)

        except Exception as e:
            self.update_status(f"Lỗi hệ thống: {str(e)}", 0)
        finally:
            self.is_processing = False
            self.btn_run.configure(state="normal", text="TẠO VIDEO TIKTOK")
            self.btn_stop.configure(state="disabled")

if __name__ == "__main__":
    app = VideoAIApp()
    app.mainloop()
