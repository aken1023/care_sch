@echo off
:: 設定 UTF-8 編碼
chcp 65001
echo ===== 清除 Python 快取檔案 =====

:: 刪除所有 __pycache__ 目錄
echo 刪除 Python 快取目錄...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

:: 刪除所有 .pyc 檔案
echo 刪除 .pyc 檔案...
del /s /q *.pyc

echo 清除完成！
pause 