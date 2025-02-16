@echo off
:: 設定 UTF-8 編碼
chcp 65001
echo ===== 清除 Git 歷史中的敏感資訊 =====
echo.

:: 清除所有 Git 歷史
echo 清除 Git 歷史...
del /f /s /q .git
rmdir /s /q .git

:: 重新初始化 Git
echo 重新初始化 Git...
git init
git branch -M main

:: 設定遠端倉庫
git remote add origin https://github.com/aken1023/care_men.git

:: 清除快取
echo 清除快取...
git rm -r --cached .

:: 強制清除所有 .pyc 檔案和快取
del /s /q *.pyc
rmdir /s /q __pycache__

:: 重新添加檔案
echo 添加檔案...
git add .

:: 提交變更
echo 提交變更...
git commit -m "初始化專案（移除敏感資訊）"

:: 推送變更
echo 推送到 GitHub...
git push -u origin main --force

pause 