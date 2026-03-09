@echo off
echo ========================================
echo   MCP Chatbot Launcher
echo ========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please create a .env file with your API keys.
    echo.
    echo Required keys:
    echo   GROQ_API_KEY=your_key_here
    echo   STOCK_API_KEY=your_key_here
    echo   WEATHER_API_KEY=your_key_here
    echo.
    pause
    exit /b 1
)

echo [INFO] Environment file found
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [INFO] Python is installed
echo.

echo Choose an option:
echo.
echo 1. Test MCP Server only
echo 2. Test Backend Client only
echo 3. Launch Frontend (Streamlit)
echo 4. Install Requirements
echo 5. Exit
echo.

set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto test_server
if "%choice%"=="2" goto test_backend
if "%choice%"=="3" goto launch_frontend
if "%choice%"=="4" goto install_requirements
if "%choice%"=="5" goto end

:test_server
echo.
echo [INFO] Starting MCP Server...
echo Press Ctrl+C to stop
echo.
python mcp-tools-local.py
goto end

:test_backend
echo.
echo [INFO] Testing Backend Client...
echo.
python mcp_chatbot_backend_client.py
pause
goto end

:launch_frontend
echo.
echo [INFO] Launching Streamlit Frontend...
echo.
echo The application will open in your browser at http://localhost:8501
echo.
streamlit run mcp-chatbot-frontend.py
goto end

:install_requirements
echo.
echo [INFO] Installing required packages...
echo.
pip install -r requirements.txt
echo.
echo [INFO] Installation complete!
pause
goto end

:end
echo.
echo Goodbye!
