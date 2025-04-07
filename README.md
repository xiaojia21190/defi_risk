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

## 最近优化

项目最近进行了以下优化：

### 后端优化

- 使用 Pydantic BaseSettings 进行更严格的环境变量验证
- 将配置（风险权重和演示账户）移至外部YAML文件
- 增强了风险引擎中的错误处理机制，特别是在asyncio.gather中
- 清理了Demo模式配置，使其完全由环境变量控制

### 前端优化

- 统一使用pnpm作为包管理器
- 规范化Wagmi配置，保持web3配置在一个地方
- 增强API错误处理和日志记录
- 优化Demo状态获取逻辑，减少不必要的API调用
- 添加WalletConnect项目ID配置

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
   python run.py --debug
   ```

   或者使用批处理文件：
   ```bash
   ./start.bat  # Windows
   ./start.sh   # Linux/macOS
   ```

后端服务将在 http://localhost:8000 上运行。

### 前端

1. 进入前端目录：
   ```bash
   cd frontend
   ```

2. 安装依赖（使用pnpm）：
   ```bash
   pnpm install
   ```

3. 启动开发服务器：
   ```bash
   pnpm dev
   ```

前端应用将在 http://localhost:3000 上运行。

## 环境配置

### 后端环境变量 (.env)

```
DEBUG=true
DEMO_MODE=true
WEB3_PROVIDER_URL=https://mainnet.infura.io/v3/your-api-key
OPENAI_API_KEY=your-openai-key
OPENAI_API_URL=https://api.openai.com/v1
OPENAI_API_MODEL=gpt-3.5-turbo
```

### 前端环境变量 (.env.local)

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_WEB3_PROVIDER_URL=https://eth-mainnet.g.alchemy.com/v2/your-api-key
NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID=your-wallet-connect-project-id
```

## 演示模式

系统默认启用演示模式，可以在不连接真实钱包的情况下查看示例数据。

## API文档

后端API文档可以在 http://localhost:8000/docs 访问。

## 技术栈

- 前端：Next.js, React, TailwindCSS, Recharts, Wagmi
- 后端：FastAPI, Python, Pandas, Pydantic
- 区块链交互：Web3.py, Wagmi
- 配置：YAML

## 许可证

MIT
