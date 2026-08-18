@echo off
REM Small-Cap Momentum Trader - Windows 启动脚本

echo 【Small-Cap Momentum Trader】
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.9+ 然后重试
    pause
    exit /b 1
)

REM 显示 Python 版本
echo ✅ 已找到 Python:
python --version
echo.

REM 运行机械人
echo 🚀 启动交易机械人...
echo.

cd /d "%~dp0"
python run.py

pause
