@echo off
REM Quick start script for Drone Operations Coordinator (Windows)

echo.
echo 🚁 Skylark Drones - Operations Coordinator
echo ==========================================
echo.

REM Check Python version
echo Checking Python version...
python --version
echo ✓ Python found

REM Check if venv exists
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    echo ✓ Virtual environment created
)

REM Activate venv
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo ✓ Virtual environment activated

REM Install dependencies
echo.
echo Installing dependencies...
pip install -q -r requirements.txt
echo ✓ Dependencies installed

REM Check if .env exists
if not exist ".env" (
    echo.
    echo Creating .env file...
    copy .env.example .env
    echo ✓ .env file created - review and update as needed
)

REM Display instructions
echo.
echo ==========================================
echo ✓ Setup complete!
echo.
echo To start the application:
echo.
echo   Terminal 1 - Backend:
echo     python main.py
echo.
echo   Terminal 2 - Frontend:
echo     streamlit run app.py
echo.
echo Then open:
echo   - Backend API docs: http://localhost:8000/docs
echo   - Frontend: http://localhost:8501
echo.
echo ==========================================
pause
