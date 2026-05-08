@echo off
cd /d f:\jyw\study\python\photo-manager\electron
echo Building Windows installer...
npm run build:win
echo.
echo Build completed!
pause