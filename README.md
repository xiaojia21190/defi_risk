# DeFi 投资组合风险监控工具

这是一个用于监控 DeFi 投资组合风险的工具，提供实时风险警报和投资建议。

## 功能特点

- 实时风险监控
- 多协议支持 (Aave, Uniswap 等)
- AI 驱动的市场预测
- 清算风险预警
- 临时损失计算
- 投资组合优化建议

## 技术栈

### 前端
- Next.js
- TypeScript
- TailwindCSS
- Web3.js
- Ethers.js

### 后端
- Python
- FastAPI
- TensorFlow/PyTorch
- Web3.py

### 智能合约
- Solidity
- Hardhat

## 系统要求

- Node.js 16+
- Python 3.8+
- Git

## 安装说明

1. 克隆仓库
```bash
git clone [repository-url]
cd defi_risk
```

2. 安装前端依赖
```bash
cd frontend
npm install
```

3. 安装后端依赖
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. 安装智能合约依赖
```bash
cd contracts
npm install
```

## 配置

1. 创建 `.env` 文件并设置必要的环境变量：
```
NEXT_PUBLIC_INFURA_ID=your_infura_id
NEXT_PUBLIC_CHAIN_ID=1
DATABASE_URL=your_database_url
```

2. 配置区块链网络
3. 设置 AI 模型参数

## 使用说明

1. 启动前端开发服务器
```bash
cd frontend
npm run dev
```

2. 启动后端服务器
```bash
cd backend
python main.py
```

3. 访问 http://localhost:3000 使用应用

## 主要功能模块

1. 投资组合监控
   - 实时头寸追踪
   - 风险指标计算
   - 收益分析

2. 风险预警系统
   - 清算风险预警
   - 临时损失预警
   - 市场波动预警

3. AI 预测模块
   - 价格趋势预测
   - 风险评估
   - 投资建议生成

4. 用户界面
   - 仪表板
   - 风险监控面板
   - 设置界面

## 贡献指南

欢迎提交 Pull Requests 和 Issues。

## 许可证

MIT
