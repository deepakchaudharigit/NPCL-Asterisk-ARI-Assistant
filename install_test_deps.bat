@echo off
echo ================================================================================
echo   INSTALLING TEST DEPENDENCIES
echo ================================================================================

echo.
echo 📦 Installing missing test packages...

echo   Installing pytest-mock...
pip install pytest-mock>=3.10.0

echo   Installing pytest-cov...
pip install pytest-cov>=4.0.0

echo.
echo 📋 Installing all test requirements...
pip install -r requirements-test.txt

echo.
echo ✅ Installation complete!
echo.
echo 🚀 You can now run tests with:
echo    python run_all_tests.py
echo.
pause