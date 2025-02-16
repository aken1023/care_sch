@echo off
:: 設定 UTF-8 編碼
chcp 65001
echo ===== 重置 Git 倉庫 =====

:: 備份 .env 檔案
echo 備份 .env 檔案...
copy .env .env.backup

:: 刪除 Git 倉庫
echo 刪除 Git 倉庫...
rd /s /q .git

:: 刪除所有快取檔案
echo 刪除快取檔案...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc

:: 重新初始化 Git
echo 重新初始化 Git...
git init
git branch -M main

:: 添加 .gitignore
echo 更新 .gitignore...
copy /y .gitignore .gitignore.new
echo .env >> .gitignore.new
del .gitignore
ren .gitignore.new .gitignore

:: 設定遠端倉庫
echo 設定遠端倉庫...
git remote add origin https://github.com/aken1023/care_men.git

:: 添加並提交檔案
echo 添加檔案...
git add .
git commit -m "初始化專案"

:: 推送到 GitHub
echo 推送到 GitHub...
git push -u origin main --force

:: 恢復 .env 檔案
echo 恢復 .env 檔案...
copy .env.backup .env
del .env.backup

echo 完成！
pause 