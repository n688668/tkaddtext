import os
import threading
import time
from tkinter import filedialog, messagebox
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

        # Khởi tạo UI
        self.setup_ui()

    def setup_ui(self):
        # Header
        self.header_label = ctk.CTkLabel(self, text="TIKTOK VIDEO AI GENERATOR", font=("Segoe UI", 24, "bold"))
        self.header_label.pack(pady=(30, 20))

        # Input Frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=40, fill="x")

        self.topic_label = ctk.CTkLabel(self.input_frame, text="Chủ đề video (Tiếng Việt):")
        self.topic_label.pack(pady=(10, 0), padx=20, anchor="w")

        self.topic_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Ví dụ: Động lực làm giàu, bí quyết sống khỏe...", height=40)
        self.topic_entry.pack(pady=(5, 15), padx=20, fill="x")

        # Video Selection
        self.btn_select = ctk.CTkButton(self, text="Chọn Video Nền", command=self.select_video, fg_color="#3b3b3b", hover_color="#4a4a4a")
        self.btn_select.pack(pady=10)

        self.video_info_label = ctk.CTkLabel(self, text="Chưa chọn video nền", font=("Arial", 11), text_color="gray")
        self.video_info_label.pack()

        # Action Button
        self.btn_run = ctk.CTkButton(
            self,
            text="TẠO VIDEO TIKTOK",
            command=self.start_process,
            height=50,
            width=300,
            font=("Segoe UI", 16, "bold"),
            fg_color="#fe2c55"
        )
        self.btn_run.pack(pady=(30, 10))

        # Status & Progress
        self.status_label = ctk.CTkLabel(self, text="Trạng thái: Sẵn sàng", text_color="#aaaaaa")
        self.status_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

    def select_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mov *.avi")])
        if path:
            self.video_path = path
            self.video_info_label.configure(text=f"Đã chọn: {os.path.basename(path)}", text_color="#57bb8a")

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
            messagebox.showerror("Lỗi", "Không tìm thấy GEMINI_API_KEY trong file .env")
            return

        topic = self.topic_entry.get().strip()
        if not topic or not self.video_path:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập chủ đề và chọn video nền trước!")
            return

        if self.is_processing:
            return

        self.is_processing = True
        self.btn_run.configure(state="disabled", text="ĐANG XỬ LÝ...")

        # Chạy logic trong thread riêng để không treo giao diện
        thread = threading.Thread(target=self.run_logic, args=(topic,))
        thread.daemon = True
        thread.start()

    def run_logic(self, topic):
        try:
            # Bước 1: Tạo nội dung
            self.update_status("Đang sáng tạo nội dung AI...", 0.2)
            prompt = (
                f"Hãy đóng vai một bậc thầy triết học sâu sắc. Hãy viết một câu trích dẫn "
                f"mang tính đạo lý, thức tỉnh hoặc truyền cảm hứng mạnh mẽ về chủ đề: {topic}. "
                f"Yêu cầu: Câu văn phải thực tế, thấm thía, giàu hình ảnh, dễ hiểu, không sáo rỗng, độ dài khoảng 30-80 chữ. "
                f"Chỉ trả về nội dung câu nói bằng tiếng Việt, không thêm bất kỳ văn bản nào khác."
            )

            raw_content = self.generate_content_with_fallback(prompt)
            content = self.split_text(raw_content, max_chars_per_line=22)

            # Bước 2: Xử lý video
            self.update_status("Đang render video...", 0.5)
            clip = VideoFileClip(self.video_path)

            duration = min(clip.duration, 10)
            clip = clip.subclipped(0, duration)

            target_w = 720
            target_h = 1280

            background = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration)
            video_resized = clip.resized(width=int(target_w))
            video_centered = video_resized.with_position(('center', 'center'))

            # Bước 3: Tạo Text Overlay
            text_width = int(target_w * 0.85)
            txt_clip = TextClip(
                text=content,
                font_size=50,
                color='yellow',
                font='font.ttf',
                method='caption',
                size=(text_width, None),
                stroke_color='black',
                stroke_width=2,
                text_align='center'
            ).with_duration(duration).with_position(('center', 'center'))

            # Kết hợp
            final_video = CompositeVideoClip([background, video_centered, txt_clip], size=(target_w, target_h))

            output_name = f"tiktok_{topic.replace(' ', '_')[:10]}.mp4"
            final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac")

            self.update_status("Hoàn thành!", 1.0)
            messagebox.showinfo("Thành công", f"Video đã sẵn sàng:\n{os.path.abspath(output_name)}")

        except Exception as e:
            self.update_status("Lỗi hệ thống", 0)
            messagebox.showerror("Lỗi", f"Chi tiết: {str(e)}")

        finally:
            self.is_processing = False
            self.btn_run.configure(state="normal", text="TẠO VIDEO TIKTOK")

if __name__ == "__main__":
    app = VideoAIApp()
    app.mainloop()
