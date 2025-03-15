# DeFi风险分析API

这是一个用于分析DeFi投资组合风险的API服务。该服务提供了全面的风险分析功能，包括市场风险、协议风险、流动性风险、智能合约风险和相关性风险等多个维度的评估。

## 功能特点

- **投资组合风险分析**：全面评估DeFi投资组合的风险状况
- **市场数据分析**：获取和分析加密货币市场数据
- **协议风险评估**：评估DeFi协议的安全性和风险
- **钱包分析**：分析钱包持仓和风险状况
- **AI驱动的洞察**：利用AI提供风险洞察和建议
- **区块链数据集成**：实时获取和分析区块链数据

## 技术架构

- **后端框架**：FastAPI
- **风险分析引擎**：模块化风险分析系统
- **AI服务**：集成AI模型提供智能分析
- **区块链服务**：与以太坊区块链交互

## API端点

### 投资组合分析

- `POST /api/v1/portfolio/analyze`：分析投资组合风险

### 市场数据

- `GET /api/v1/market/data/{asset}`：获取资产市场数据
- `POST /api/v1/market/predict/{asset}`：预测资产市场趋势
- `GET /api/v1/market/gas`：获取当前gas价格

### 协议分析

- `GET /api/v1/protocol/list`：获取支持的协议列表
- `GET /api/v1/protocol/{protocol_name}`：获取协议信息
- `GET /api/v1/protocol/risk/{protocol_name}`：分析协议风险

### 钱包分析

- `GET /api/v1/wallet/{wallet_address}/balance`：获取钱包余额
- `GET /api/v1/wallet/{wallet_address}/positions`：获取钱包在所有协议中的头寸
- `GET /api/v1/wallet/{wallet_address}/risk`：分析钱包风险
- `GET /api/v1/wallet/{wallet_address}/alerts`：获取钱包相关的市场警报

## 安装与运行

### 前提条件

- Python 3.8+
- 以太坊节点访问（如Infura或Alchemy）
- OpenAI API密钥（用于AI分析）

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/defi-risk-api.git
cd defi-risk-api
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
创建`.env`文件并设置以下变量：
```
DEBUG=True
WEB3_PROVIDER_URL=your_ethereum_node_url
OPENAI_API_KEY=your_openai_api_key
```

4. 运行应用
```bash
python run.py
```

5. 访问API文档
打开浏览器访问 `http://localhost:8000/docs`

## 项目结构

```
├── main.py                 # 应用入口点
├── run.py                  # 启动脚本
├── requirements.txt        # 依赖列表
├── .env                    # 环境变量配置
├── blockchain_service.py   # 区块链服务
├── risk_calculator.py      # 风险计算器
├── ai_predictor.py         # AI预测器
└── risk_modules/           # 风险分析模块
    ├── __init__.py
    ├── portfolio_risk.py   # 投资组合风险分析
    ├── market_risk.py      # 市场风险分析
    ├── investment_type_risk.py # 投资类型风险分析
    ├── liquidity_pool_risk.py  # 流动性池风险分析
    ├── mining_risk.py      # 挖矿风险分析
    ├── save_risk.py        # 存币风险分析
    ├── vault_risk.py       # 机枪池风险分析
    ├── staking_risk.py     # 质押风险分析
    └── lending_risk.py     # 借贷风险分析
```

## 使用示例

### 分析投资组合风险

```python
import requests
import json

url = "http://localhost:8000/api/v1/portfolio/analyze"
payload = {
    "wallet_address": "0x123456789abcdef123456789abcdef123456789"
}
headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())
```

### 获取资产市场数据

```python
import requests

url = "http://localhost:8000/api/v1/market/data/ETH"
response = requests.get(url)
print(response.json())
```

### 分析钱包风险

```python
import requests

wallet_address = "0x123456789abcdef123456789abcdef123456789"
url = f"http://localhost:8000/api/v1/wallet/{wallet_address}/risk"
response = requests.get(url)
print(response.json())
```

## 贡献

欢迎提交问题和拉取请求！

## 许可证

MIT
