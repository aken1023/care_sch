@echo off
:: 設定 UTF-8 編碼
chcp 65001
echo ===== 部署到 GitHub =====
echo.

:: 設定顏色
color 0A

:: 刪除所有快取檔案
echo 清理快取檔案...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc

:: 備份 .env
echo 備份 .env...
if exist .env (
    copy .env .env.backup
)

:: 初始化 Git
echo 初始化 Git 倉庫...
rd /s /q .git
git init

:: 設定 .gitignore
echo 設定 .gitignore...
echo # 環境變數 > .gitignore
echo .env >> .gitignore
echo .env.* >> .gitignore
echo !.env.example >> .gitignore
echo # Python >> .gitignore
echo __pycache__/ >> .gitignore
echo *.pyc >> .gitignore
echo # 其他檔案 >> .gitignore
echo logs/ >> .gitignore
echo uploads/ >> .gitignore
echo records/ >> .gitignore
echo ssl/ >> .gitignore

:: 創建 Dockerfile
echo 創建 Dockerfile...
(
echo FROM python:3.8-slim
echo.
echo WORKDIR /app
echo.
echo COPY requirements.txt .
echo COPY .env.example .env
echo COPY . .
echo.
echo RUN python -m pip install --upgrade pip ^&^& \
echo     pip install -r requirements.txt
echo.
echo # 設定預設 PORT
echo ENV PORT=5000
echo ENV PYTHONUNBUFFERED=1
echo ENV FLASK_DEBUG=0
echo.
echo EXPOSE ${PORT}
echo.
echo # 使用環境變數中的 PORT
echo CMD gunicorn --bind 0.0.0.0:${PORT} app:app
) > Dockerfile

:: 創建 railway.toml
echo 創建 railway.toml...
(
echo [build]
echo builder = "NIXPACKS"
echo buildCommand = "python -m pip install --upgrade pip && pip install -r requirements.txt"
echo.
echo [deploy]
echo startCommand = "gunicorn --bind 0.0.0.0:${PORT} app:app"
echo healthcheckPath = "/callback"
echo healthcheckTimeout = 300
echo restartPolicyType = "ON_FAILURE"
echo healthcheckProtocol = "http"
echo healthcheckInterval = 30
) > railway.toml

:: 創建 README.md
echo # 常照觀護交班系統 > README.md
echo. >> README.md
echo 使用 Line Bot 進行照護記錄和交班管理的系統 >> README.md

:: 添加並提交檔案
echo 添加檔案...
git add .
git commit -m "更新 Docker 部署配置"

:: 設定分支和遠端倉庫
git branch -M main
git remote add origin https://github.com/aken1023/care_sch.git

:: 推送到 GitHub
echo 推送到 GitHub...
git push -u origin main --force

:: 恢復 .env
if exist .env.backup (
    copy .env.backup .env
    del .env.backup
)

echo 完成！
pause 