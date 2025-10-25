@echo off
chcp 65001 >nul
echo 正在打包 三界奇谈 项目...

:: 1. 设置输出名称
set EXE_NAME=三界奇谈.exe

:: 2. 配置UPX路径（需修改为您的实际路径）
set UPX_PATH=E:\upx-5.0.2-win64\upx.exe

:: 3. 执行打包
pyinstaller main.py ^
  --name "%EXE_NAME%" ^
  --onefile ^
  --windowed ^
  --icon=Graphics/Icons/icon.ico ^
  --add-data ".venv/Lib/site-packages/lupa;lupa" ^
  --exclude-module tkinter ^
  --exclude test_scripts ^
  --upx-dir=%UPX_PATH% ^
  --clean

:: 4. 验证结果
if exist "dist\%EXE_NAME%" (
    echo.
    echo 打包成功！程序路径：dist\%EXE_NAME%
) else (
    echo.
    echo 错误：打包失败，请检查日志
)

pause