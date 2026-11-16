@echo off
chcp 65001 >nul
:: BlueVolume Windows 开机自启动配置脚本
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%pc_server.py"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_FILE=%STARTUP_FOLDER%\BlueVolumeAutoStart.vbs"

if "%1"=="uninstall" goto do_uninstall
if "%1"=="remove" goto do_uninstall

:do_install
echo ==================================================
echo  正在配置 BlueVolume Windows 开机自启动...
echo ==================================================
echo 目标脚本: %PYTHON_SCRIPT%
echo 启动位置: %STARTUP_FOLDER%

:: 创建无黑框后台静默运行的 VBS 脚本
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.Run "pythonw.exe """ ^& "%PYTHON_SCRIPT%" ^& """", 0, False
) > "%VBS_FILE%"

if exist "%VBS_FILE%" (
    echo.
    echo [成功] 已成功添加到 Windows 开机自启文件夹！
    echo 电脑开机或登录后，将通过后台静默运行 pc_server.py (无命令提示符黑框)。
    echo.
    echo 若要取消开机自启，请运行: autostart_windows.bat uninstall
) else (
    echo [错误] 无法写入启动项，请检查权限。
)
goto end

:do_uninstall
echo ==================================================
echo  正在移除 BlueVolume Windows 开机自启动...
echo ==================================================
if exist "%VBS_FILE%" (
    del "%VBS_FILE%"
    echo [成功] 已移除开机自启项目！
) else (
    echo [提示] 未找到自启配置文件，可能尚未安装。
)
goto end

:end
echo ==================================================
pause
