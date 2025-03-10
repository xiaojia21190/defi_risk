# DeFi风险监控平台

这是一个DeFi风险监控平台，用于分析和监控DeFi投资组合的风险。

## 项目结构

项目分为前端和后端两部分：

- `frontend/`: 基于Next.js的前端应用
- `backend/`: 基于FastAPI的后端API服务

## 功能特点

- 投资组合分析和风险评估
- 资产价格和市场趋势预测
- 风险监控和警报系统
- 智能投资建议

## 运行说明

### 后端

1. 进入后端目录：
   ```bash
   cd backend
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 启动后端服务：
   ```bash
   uvicorn main:app --reload
   ```

后端服务将在 http://localhost:8000 上运行。

### 前端

1. 进入前端目录：
   ```bash
   cd frontend
   ```

2. 安装依赖：
   ```bash
   npm install
   ```

3. 启动开发服务器：
   ```bash
   npm run dev
   ```

前端应用将在 http://localhost:3000 上运行。

## 演示模式

系统默认启用演示模式，可以在不连接真实钱包的情况下查看示例数据。

## API文档

后端API文档可以在 http://localhost:8000/docs 访问。

## 技术栈

- 前端：Next.js, React, TailwindCSS, Recharts
- 后端：FastAPI, Python, Pandas
- 区块链交互：Web3.py

## 许可证

MIT
