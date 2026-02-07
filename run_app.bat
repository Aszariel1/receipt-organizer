@echo off
echo Setting up Receipt Organizer...

:: Try 'py' first (standard Windows launcher), then 'python'
py -0 >nul 2>&1 && set PYTHON_CMD=py || set PYTHON_CMD=python

%PYTHON_CMD% -m venv venv
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python from python.org and check "Add to PATH".
    pause
    exit /b
)

call venv\Scripts\activate
echo Installing libraries...
pip install -r requirements.txt
echo Starting Streamlit...
streamlit run app.py
pause