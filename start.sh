#!/bin/bash
echo "启动DeFi风险监控平台..."

echo "启动后端服务..."
cd backend && python -m uvicorn main:app --reload &
BACKEND_PID=$!

echo "等待后端服务启动..."
sleep 5

echo "启动前端服务..."
cd ../frontend && npm run dev &
FRONTEND_PID=$!

echo "服务已启动!"
echo "前端: http://localhost:3000"
echo "后端: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"

echo "按Ctrl+C停止服务"
wait $BACKEND_PID $FRONTEND_PID
