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
        self.geometry("700x550")

        self.video_path = ""
        self.is_processing = False
        self.stop_requested = False
        self.target_count = 0

        # Khởi tạo UI
        self.setup_ui()

    def setup_ui(self):
        # Header
        self.header_label = ctk.CTkLabel(self, text="TIKTOK VIDEO AI GENERATOR", font=("Segoe UI", 24, "bold"))
        self.header_label.pack(pady=(30, 20))

        # Input Frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=40, fill="x")

        # Prompt input (thay cho topic)
        self.prompt_label = ctk.CTkLabel(self.input_frame, text="Prompt (Tiếng Việt):")
        self.prompt_label.pack(pady=(10, 0), padx=20, anchor="w")

        # Mặc định prompt giống nội dung cũ với topic='ngẫu nhiên'
        default_prompt = (
            "Hãy đóng vai một người cực kỳ nhiều chuyện, số nhọ, làm gì cũng hỏng và luôn gặp khó khăn trong cuộc sống. "
            "Hãy viết một dòng trạng thái (status) than vãn, kể khổ về chủ đề: ngẫu nhiên. "
            "Yêu cầu: Giọng văn phải đậm chất 'drama', hay than thân trách phận, kể lể những xui xẻo mình gặp phải và hỏi xin lời khuyên hoặc sự đồng cảm từ cộng đồng mạng. "
            "Sử dụng ngôn ngữ đời thường, có chút hờn dỗi, dùng nhiều từ cảm thán (ôi trời, sao tôi khổ thế, mệt mỏi quá...), độ dài khoảng 40-90 chữ. "
            "Chỉ trả về nội dung status bằng tiếng Việt, không thêm bất kỳ văn bản dẫn nhập nào khác."
        )

        # lưu prompt mặc định lên instance để dùng được ở nơi khác
        self.default_prompt = default_prompt

        # Multiline prompt box so user can enter newlines; wrap by word (break at spaces)
        self.prompt_entry = ctk.CTkTextbox(self.input_frame, height=120, wrap="word")
        self.prompt_entry.insert("1.0", self.default_prompt)
        self.prompt_entry.pack(pady=(5, 15), padx=20, fill="both")

        # Chọn ngẫu nhiên video nền từ thư mục `input`
        self.set_random_video()

        # Action Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=(30, 6))

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
        self.qty_entry = ctk.CTkEntry(qty_frame, width=80, placeholder_text="1")
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=0, column=1)

        # Status & Progress
        self.status_label = ctk.CTkLabel(self, text="Trạng thái: Sẵn sàng", text_color="#aaaaaa")
        self.status_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

    def set_random_video(self):
        """Tự động chọn ngẫu nhiên một video từ thư mục `input` (relative to script)."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        input_dir = os.path.join(script_dir, "input")

        exts = (".mp4", ".mov", ".avi", ".mkv")
        candidates = []
        if os.path.isdir(input_dir):
            for fn in os.listdir(input_dir):
                if fn.lower().endswith(exts):
                    candidates.append(os.path.join(input_dir, fn))

        if not candidates:
            self.video_path = ""
            # Thông báo lỗi qua status thay vì hiển thị tên file
            self.update_status("Không tìm thấy video nền trong input/", 0)
        else:
            choice = random.choice(candidates)
            self.video_path = choice
            # Không hiển thị tên file video nền (yêu cầu: ẩn thông tin video nền)

    def update_status(self, text, progress=None):
        self.status_label.configure(text=f"Trạng thái: {text}")
        if progress is not None:
            self.progress_bar.set(progress)

    def split_text(self, text, max_chars_per_line=22):
        """Ngắt dòng văn bản theo dấu cách để tránh cắt đôi từ."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_chars_per_line:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)

    def generate_content_with_fallback(self, prompt):
        """Cơ chế thử lại với các model khác nhau."""
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
        last_exception = None

        for model_name in models_to_try:
            try:
                print(f"Đang thử model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text.strip().replace('"', '')
            except Exception as e:
                print(f"Model {model_name} lỗi: {str(e)}")
                last_exception = e
                time.sleep(1)
                continue

        raise last_exception

    def start_process(self):
        """Hàm khởi chạy tiến trình xử lý."""
        if not GEMINI_API_KEY:
            self.update_status("Lỗi: Không tìm thấy GEMINI_API_KEY trong file .env", 0)
            return

        # Read multiline prompt from textbox
        try:
            prompt_text = self.prompt_entry.get("1.0", "end").strip() or self.default_prompt
        except Exception:
            # fallback if widget API differs
            prompt_text = getattr(self.prompt_entry, 'get', lambda *a: self.default_prompt)().strip() or self.default_prompt

        if not self.video_path:
            self.update_status("Thiếu dữ liệu: Vui lòng đảm bảo có video nền.", 0)
            return

        if self.is_processing:
            return

        # Đọc số lượng video
        try:
            count = int(self.qty_entry.get())
            if count < 1:
                count = 1
        except Exception:
            count = 1

        self.is_processing = True
        self.stop_requested = False
        self.target_count = count
        self.btn_run.configure(state="disabled", text="ĐANG XỬ LÝ...")
        # Chỉ cho phép dừng nếu có nhiều hơn 1 video sẽ tạo
        if count > 1:
            self.btn_stop.configure(state="normal")
        else:
            self.btn_stop.configure(state="disabled")

        # Chạy logic trong thread riêng để không treo giao diện
        thread = threading.Thread(target=self.run_logic, args=(prompt_text, count))
        thread.daemon = True
        thread.start()

    def request_stop(self):
        """Yêu cầu dừng quá trình tạo video tự động (dừng sau video hiện tại)."""
        # Chỉ thực hiện nếu đang trong tiến trình tạo và đang tạo nhiều video
        if not self.is_processing or self.target_count <= 1:
            return

        self.stop_requested = True
        self.update_status("Yêu cầu dừng: sẽ dừng sau video hiện tại.")
        self.btn_stop.configure(state="disabled")


    def run_logic(self, prompt_text, count):
        try:
            created = 0
            for i in range(count):
                # Chọn lại video nền ngẫu nhiên cho mỗi lần tạo
                self.set_random_video()
                if not self.video_path:
                    self.update_status("Không có video nền để tiếp tục.", 0)
                    break

                if self.stop_requested:
                    break

                # Bước 1: Tạo nội dung
                self.update_status(f"({i+1}/{count}) Đang sáng tạo nội dung AI...", 0.1)
                # Nếu prompt chứa placeholder {topic}, thay bằng 'ngẫu nhiên'
                prompt = prompt_text.replace("{topic}", "ngẫu nhiên")
                raw_content = self.generate_content_with_fallback(prompt)
                content = self.split_text(raw_content, max_chars_per_line=22)

                # Bước 2: Xử lý video
                self.update_status(f"({i+1}/{count}) Đang render video...", 0.5)
                clip = VideoFileClip(self.video_path)

                duration = min(clip.duration, 10)
                clip = clip.subclipped(0, duration)

                target_w = 720
                target_h = 1280

                background = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration)
                video_resized = clip.resized(width=int(target_w))
                video_centered = video_resized.with_position(('center', 'center'))

                # Bước 3: Tạo Text Overlay
                text_width = int(target_w * 0.95)
                txt_clip = TextClip(
                    text=content,
                    font_size=50,
                    color='white',
                    font='font.ttf',
                    method='caption',
                    size=(text_width, None),
                    stroke_color='black',
                    stroke_width=2,
                    text_align='center'
                ).with_duration(duration)

                # Đảm bảo dòng cuối không bị cắt: tính chiều cao text và đẩy lên vài px nếu cần
                try:
                    txt_h = txt_clip.h
                    y = max(0, int((target_h - txt_h) / 2) - 10)
                    txt_clip = txt_clip.with_position(('center', y))
                except Exception:
                    # Nếu không thể lấy chiều cao, fallback về center
                    txt_clip = txt_clip.with_position(('center', 'center'))

                # Kết hợp
                final_video = CompositeVideoClip([background, video_centered, txt_clip], size=(target_w, target_h))

                ts = time.strftime("%Y%m%d%H%M%S")
                # Tạo tên an toàn từ prompt (nếu rỗng dùng 'prompt')
                safe_topic = re.sub(r'[^A-Za-z0-9]', '_', prompt_text)[:10] or 'prompt'
                output_name = f"tiktok_{safe_topic}_{ts}.mp4"
                # Lưu vào thư mục output
                script_dir = os.path.dirname(os.path.abspath(__file__))
                output_dir = os.path.join(script_dir, "output")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_name)

                final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

                created += 1
                self.update_status(f"({i+1}/{count}) Hoàn thành: {os.path.abspath(output_path)}", 1.0)

                # Nếu có yêu cầu dừng thì ngưng, không chờ tiếp
                if self.stop_requested:
                    break

                # Nếu chưa phải video cuối cùng thì chờ 30 giây (cho phép dừng trong thời gian chờ)
                if i < count - 1:
                    self.update_status(f"Đợi 30s trước khi tạo video tiếp ({i+1}/{count})...", 0)
                    for _ in range(30):
                        if self.stop_requested:
                            break
                        time.sleep(1)

        except Exception as e:
            self.update_status(f"Lỗi hệ thống: {str(e)}", 0)

        finally:
            self.is_processing = False
            self.target_count = 0
            self.stop_requested = False
            self.btn_run.configure(state="normal", text="TẠO VIDEO TIKTOK")
            self.btn_stop.configure(state="disabled")

if __name__ == "__main__":
    app = VideoAIApp()
    app.mainloop()
