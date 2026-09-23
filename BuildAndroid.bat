@echo off
setlocal
cd /d "%~dp0"
python --version
if errorlevel 1 goto fail
if exist ".test-tools\android-sdk\build-tools\android-15\aapt2.exe" goto build
:setup
echo Android SDK build tools were not found. Installing the pinned SDK components...
python mobile\setup_android.py
if errorlevel 1 goto fail
:build
python mobile\build_apk.py %*
if errorlevel 1 goto fail
echo Build complete. APK: dist\PlayerStudio-android.apk
goto done
:fail
echo Android build failed. Review the checks above and mobile\README.md.
exit /b 1
:done
pause
