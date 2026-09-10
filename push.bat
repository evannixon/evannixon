@echo off
echo ==============================================
echo   Pushing evannixon profile repo to GitHub...
echo ==============================================
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Profil GitHub dan bot auto-streak berhasil di-upload!
) else (
    echo [FAILED] Pastikan repo 'evannixon' sudah dibuat di https://github.com/new sebagai Public!
)
pause
