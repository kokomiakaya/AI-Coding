@echo off
rem 启动前端开发服务器（Vite，默认端口 5173）
cd /d "%~dp0..\frontend"
npm run dev
pause
