@echo off
echo 启动DeFi风险监控平台...

echo 启动后端服务...
start cmd /k "cd backend && python -m uvicorn main:app --reload"

echo 等待后端服务启动...
timeout /t 5

echo 启动前端服务...
start cmd /k "cd frontend && npm run dev"

echo 服务已启动!
echo 前端: http://localhost:3000
echo 后端: http://localhost:8000
echo API文档: http://localhost:8000/docs

pause
