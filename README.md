# CMD
```
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

pyinstaller TikTokVideoAI.spec

pyinstaller --noconfirm --onedir --windowed --add-data=".env:." --add-data="font.ttf:." --add-data="icon.ico:." --collect-all playwright --collect-all playwright_stealth --collect-all moviepy --collect-all customtkinter main.py

pyinstaller --noconfirm --onedir --windowed ^
--add-data="config.env.template:." ^
--add-data="font.ttf:." ^
--add-data="icon.ico:." ^
--add-data="input/video_mau.mp4:input" ^  <-- THÊM DÒNG NÀY
--collect-all playwright ^
--collect-all playwright_stealth ^
--collect-all moviepy ^
--collect-all customtkinter ^
main.py
```
# .env
```
GEMINI_API_KEY="GEMINI_API_KEY_IS_HERE"
```