# DeFi风险监控平台

这是一个DeFi风险监控平台，用于分析和监控DeFi投资组合的风险。

## 项目结构

项目分为前端、后端和智能合约三部分：

- `frontend/`: 基于Next.js的前端应用 (使用pnpm管理)
- `backend/`: 基于FastAPI的后端API服务
- `contracts/`: Solidity 智能合约源代码 (可选，根据需求使用)
- `start.sh` / `start.bat`: 用于快速启动前后端服务的脚本

## 功能特点

- 投资组合分析和风险评估
- 资产价格和市场趋势预测
- 风险监控和警报系统
- 智能投资建议

## 技术栈

- 前端：Next.js, React, TailwindCSS, Recharts, Wagmi, pnpm
- 后端：FastAPI, Python, Pandas, Pydantic
- 区块链交互：Web3.py (后端), Wagmi (前端)
- 配置：YAML, Pydantic BaseSettings (后端)
- 数据库/存储：(如果使用了特定数据库，请在此处添加)

## 先决条件

在运行本项目之前，请确保您已安装以下软件：

- [Python](https://www.python.org/) (建议版本 3.9+)
- [Node.js](https://nodejs.org/) (建议版本 18+)
- [pnpm](https://pnpm.io/) (可以通过 `npm install -g pnpm` 安装)

## 安装与运行

### 1. 克隆仓库 (如果尚未完成)

```bash
git clone <your-repository-url>
cd <repository-directory>
```

### 2. 安装依赖

**后端依赖:**

```bash
cd backend
pip install -r requirements.txt
cd ..
```

**前端依赖:** (请确保使用 pnpm)

```bash
cd frontend
pnpm install
cd ..
```

### 3. 配置环境变量

在启动服务之前，您需要配置必要的环境变量。

- **后端**: 复制 `backend/.env.example` (如果存在) 或手动创建 `backend/.env` 文件，并根据下面的"环境配置"部分填入您的配置。
- **前端**: 复制 `frontend/.env.local.example` (如果存在) 或手动创建 `frontend/.env.local` 文件，并根据下面的"环境配置"部分填入您的配置。

### 4. 启动服务

您可以选择以下任一方式启动服务：

**方法一：使用启动脚本 (推荐)**

根目录提供了便捷的启动脚本，可以同时启动后端和前端服务。

```bash
# Linux/macOS
./start.sh

# Windows
./start.bat
```

**注意**: 这些脚本默认使用 `npm run dev` 来启动前端开发服务器。由于本项目推荐使用 `pnpm`，您可以手动编辑 `start.sh` 和 `start.bat` 文件，将 `npm run dev` 替换为 `pnpm dev`，以获得最佳兼容性。

**方法二：手动启动**

如果您希望单独控制或调试，可以在不同的终端窗口中分别启动后端和前端。

**启动后端:**

```bash
cd backend
# 确保 .env 文件已配置
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端:**

```bash
cd frontend
# 确保 .env.local 文件已配置
pnpm dev
```

### 5. 访问应用

服务启动后，您可以通过以下地址访问：

- **前端应用**: [http://localhost:3000](http://localhost:3000)
- **后端 API (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **后端 API (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 环境配置

项目运行需要配置环境变量。请在对应的目录下创建 `.env` 文件。

### 后端环境变量 (`backend/.env`)

在 `backend` 目录下创建 `.env` 文件，并填入以下内容 (根据您的实际情况修改):

```dotenv
# FastAPI 应用调试模式 (true/false)
DEBUG=true
# 是否启用演示模式 (true/false)
DEMO_MODE=true
# Web3 Provider URL (例如 Infura, Alchemy)
WEB3_PROVIDER_URL=https://mainnet.infura.io/v3/your-api-key
# OpenAI API Key (用于智能建议功能)
OPENAI_API_KEY=your-openai-key
# OpenAI API Base URL
OPENAI_API_URL=https://api.openai.com/v1
# 使用的 OpenAI 模型
OPENAI_API_MODEL=gpt-3.5-turbo
```

### 前端环境变量 (`frontend/.env.local`)

在 `frontend` 目录下创建 `.env.local` 文件，并填入以下内容 (根据您的实际情况修改):

```dotenv
# 后端 API 的基础 URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# 是否启用前端演示模式 (应与后端 DEMO_MODE 保持一致)
NEXT_PUBLIC_DEMO_MODE=true
# 前端使用的 Web3 Provider URL (可以是与后端不同的提供商或 RPC 端点)
NEXT_PUBLIC_WEB3_PROVIDER_URL=https://eth-mainnet.g.alchemy.com/v2/your-api-key
# WalletConnect 项目 ID (用于钱包连接)
NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID=your-wallet-connect-project-id
```

## Contracts

`contracts/` 目录包含项目相关的 Solidity 智能合约源代码。

**注意**: 当前这些合约仅作为参考或未来集成使用，标准的本地运行流程 (如上所述) 不涉及这些合约的编译或部署。如果您需要使用或开发这些合约，请参考 Solidity 和相关框架 (如 Hardhat/Truffle) 的文档进行操作。


## API文档

后端API文档可以在 [http://localhost:8000/docs](http://localhost:8000/docs) 访问。

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

## 许可证

MIT
