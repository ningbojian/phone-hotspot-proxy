@echo off
rem ASCII-only content: cmd's codepage would garble Chinese here.
rem Python 3.6+ writes Unicode straight to the console, so the
rem Chinese output from rebuild_shortcut.py displays fine.
rem
rem Run this once after moving the folder: the desktop shortcut
rem stores an absolute path and goes stale when the folder moves.
rem
rem Interpreter order matters. "where python" often resolves to the
rem Microsoft Store stub in %LOCALAPPDATA%\Microsoft\WindowsApps,
rem which silently does nothing when run non-interactively. So real
rem install paths are probed first, and the PATH lookup comes last
rem with that stub explicitly filtered out.
cd /d "%~dp0"

if exist "%USERPROFILE%\anaconda3\python.exe"  goto :useanaconda
if exist "%USERPROFILE%\miniconda3\python.exe" goto :useminiconda
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" goto :use313
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" goto :use312

where py >nul 2>nul
if not errorlevel 1 goto :usepy

for /f "delims=" %%F in ('where python 2^>nul') do (
    echo %%F| find /i "WindowsApps" >nul
    if errorlevel 1 (
        "%%F" "%~dp0rebuild_shortcut.py"
        goto :done
    )
)

echo.
echo [ERROR] No usable Python interpreter found.
echo         Install Python 3.7+ and tick "Add python.exe to PATH".
echo         https://www.python.org/downloads/
echo.
pause >nul
exit /b 1

:useanaconda
"%USERPROFILE%\anaconda3\python.exe" "%~dp0rebuild_shortcut.py"
goto :done

:useminiconda
"%USERPROFILE%\miniconda3\python.exe" "%~dp0rebuild_shortcut.py"
goto :done

:use313
"%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%~dp0rebuild_shortcut.py"
goto :done

:use312
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%~dp0rebuild_shortcut.py"
goto :done

:usepy
py -3 "%~dp0rebuild_shortcut.py"
goto :done

:done
echo.
echo Press any key to close...
pause >nul
