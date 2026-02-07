@echo off
echo Setting up Receipt Organizer...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo Starting Streamlit...
streamlit run app.py
pause