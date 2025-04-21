# DeFi风险分析系统 - API文档

## API概述

DeFi风险分析系统提供REST API接口，允许客户端获取DeFi资产、协议和钱包的风险分析和相关数据。所有API路径都以`/api/v1`为前缀。

### 基本信息

- **基础URL**: `/api/v1`
- **响应格式**: JSON
- **认证方式**: 目前不需要认证

### 通用响应格式

所有API端点返回统一的响应格式:

```json
{
  "status": "success", // 或 "error"
  "data": { ... },     // 业务数据
  "message": "...",    // 成功/错误消息
  "timestamp": "2023-05-01T08:30:00.123456Z",
  "is_demo_data": false, // 标识是否为演示数据
  "meta": { ... }      // 元数据，如分页信息
}
```

### 错误处理

API错误使用HTTP状态码指示问题类型:

- **400** - 错误请求(参数无效等)
- **404** - 资源未找到
- **500** - 服务器内部错误

## API端点分类

API端点按功能分为以下几类:

1. 钱包分析API
2. 协议分析API
3. 市场数据API
4. 演示功能API

## 1. 钱包分析API

### 1.1 获取钱包头寸

获取指定钱包地址在各协议中的投资头寸信息。

- **路径**: `/wallet/{wallet_address}/positions`
- **方法**: GET
- **参数**:
  - `wallet_address` (路径参数): 要分析的钱包地址

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "positions": [
      {
        "protocol": "Aave",
        "asset": "ETH",
        "amount": 2.5,
        "value_usd": 7500,
        "apy": 3.2
      },
      {
        "protocol": "Compound",
        "asset": "USDC",
        "amount": 10000,
        "value_usd": 10000,
        "apy": 4.1
      }
    ],
    "total_value_usd": 17500,
    "position_count": 2,
    "protocols": [
      {
        "name": "Aave",
        "chain": "Ethereum",
        "tvl": 5000000000,
        "supported_assets": ["ETH", "USDC", "DAI"],
        "features": ["借贷", "流动性挖矿"]
      },
      {
        "name": "Compound",
        "chain": "Ethereum",
        "tvl": 3000000000,
        "supported_assets": ["ETH", "USDC", "DAI"],
        "features": ["借贷"]
      }
    ],
    "protocol_count": 2
  },
  "message": "获取钱包头寸成功",
  "timestamp": "2023-05-01T08:30:00.123456Z",
  "is_demo_data": false
}
```

### 1.2 分析钱包风险

获取指定钱包的全面风险分析结果。

- **路径**: `/wallet/{wallet_address}/risk`
- **方法**: GET
- **参数**:
  - `wallet_address` (路径参数): 要分析的钱包地址

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "wallet_address": "0x1234...",
    "overall_risk": {
      "score": 65,
      "level": "高风险",
      "summary": "此钱包投资组合存在较高风险，主要由市场波动性和协议集中度风险构成。"
    },
    "risk_breakdown": {
      "market_risk": {
        "score": 70,
        "level": "高风险",
        "factors": [
          {
            "name": "价格波动风险",
            "score": 75,
            "description": "投资组合中80%资产价格波动率高于行业平均水平。"
          },
          {
            "name": "市值风险",
            "score": 65,
            "description": "投资组合中40%资产市值低于10亿美元，存在中等市值风险。"
          }
        ]
      },
      "smart_contract_risk": {
        "score": 60,
        "level": "中等风险",
        "factors": [...]
      },
      "liquidity_risk": {
        "score": 55,
        "level": "中等风险",
        "factors": [...]
      },
      "protocol_risk": {
        "score": 75,
        "level": "高风险",
        "factors": [...]
      },
      "correlation_risk": {
        "score": 65,
        "level": "高风险",
        "factors": [...]
      }
    },
    "recommendations": [
      "建议分散投资，减少单一协议的敞口",
      "考虑增加大市值资产的配置以降低市场波动风险",
      "监控协议X的安全更新，其审计状况存在一定问题"
    ],
    "monitoring_points": [
      "关注资产A的价格波动，当日波动超过15%时应考虑调整",
      "关注协议B的TVL变化，如短期下降超过20%应评估风险"
    ]
  },
  "message": "风险分析完成",
  "timestamp": "2023-05-01T09:15:00.123456Z",
  "is_demo_data": false
}
```

### 1.3 获取钱包预警

获取指定钱包的风险预警信息。

- **路径**: `/wallet/{wallet_address}/alerts`
- **方法**: GET
- **参数**:
  - `wallet_address` (路径参数): 要分析的钱包地址

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "wallet_address": "0x1234...",
    "alert_count": 3,
    "alerts": [
      {
        "type": "PRICE_VOLATILITY",
        "severity": "HIGH",
        "asset": "ETH",
        "description": "ETH价格在过去24小时内波动超过15%",
        "timestamp": "2023-05-01T07:30:00Z"
      },
      {
        "type": "PROTOCOL_RISK",
        "severity": "MEDIUM",
        "protocol": "Protocol X",
        "description": "协议X发现了新的安全漏洞，正在修复中",
        "timestamp": "2023-05-01T05:45:00Z"
      },
      {
        "type": "LIQUIDITY_RISK",
        "severity": "LOW",
        "asset": "Token Y",
        "description": "Token Y的流动性降低了20%",
        "timestamp": "2023-05-01T02:15:00Z"
      }
    ]
  },
  "message": "获取预警信息成功",
  "timestamp": "2023-05-01T09:30:00.123456Z",
  "is_demo_data": false
}
```

### 1.4 市场场景模拟

模拟不同市场场景下钱包的表现。

- **路径**: `/wallet/{wallet_address}/scenario-simulation`
- **方法**: GET
- **参数**:
  - `wallet_address` (路径参数): 要分析的钱包地址
  - `scenario` (查询参数): 场景类型，可选值: `market_crash`, `liquidity_shock`, `protocol_exploit`, `regulatory_crackdown`，默认为`market_crash`

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "wallet_address": "0x1234...",
    "scenario": "market_crash",
    "scenario_description": "模拟主要加密资产价格下跌50%的市场崩盘场景",
    "current_portfolio": {
      "total_value_usd": 17500,
      "assets": [...]
    },
    "simulated_portfolio": {
      "total_value_usd": 10250,
      "assets": [...]
    },
    "impact_summary": {
      "value_change_pct": -41.4,
      "most_affected_assets": [
        {"asset": "ETH", "change_pct": -50.0},
        {"asset": "TokenZ", "change_pct": -75.0}
      ],
      "least_affected_assets": [
        {"asset": "USDC", "change_pct": -0.5},
        {"asset": "DAI", "change_pct": -2.0}
      ]
    },
    "recommendations": [
      "考虑增加稳定币比例以降低市场崩盘风险",
      "评估高波动性资产的配置是否符合您的风险承受能力"
    ]
  },
  "message": "场景模拟完成",
  "timestamp": "2023-05-01T10:00:00.123456Z",
  "is_demo_data": false
}
```

## 2. 协议分析API

### 2.1 获取协议信息

获取指定协议的详细信息。

- **路径**: `/protocol/{protocol_name}`
- **方法**: GET
- **参数**:
  - `protocol_name` (路径参数): 协议名称

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "name": "Aave",
    "description": "Aave是一个去中心化借贷平台，允许用户存款赚取利息或借款。",
    "website": "https://aave.com",
    "tvl": 5000000000,
    "supported_assets": ["ETH", "USDC", "DAI", "USDT", "WBTC", "LINK"],
    "features": ["借贷", "流动性挖矿", "闪电贷"],
    "risk_score": 85,
    "audit_reports": [
      "https://example.com/aave-audit1",
      "https://example.com/aave-audit2"
    ],
    "chains": ["Ethereum", "Polygon", "Avalanche"]
  },
  "message": "获取协议信息成功",
  "timestamp": "2023-05-01T10:30:00.123456Z",
  "is_demo_data": false
}
```

### 2.2 分析协议风险

获取指定协议的风险分析结果。

- **路径**: `/protocol/risk/{protocol_name}`
- **方法**: GET
- **参数**:
  - `protocol_name` (路径参数): 协议名称

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "protocol": "Aave",
    "risk_score": 85,
    "risk_level": "低",
    "risk_factors": [
      {
        "factor": "智能合约风险",
        "score": 90,
        "description": "协议经过多次审计，且漏洞历史修复良好。"
      },
      {
        "factor": "经济模型风险",
        "score": 80,
        "description": "协议经济模型稳健，但在极端市场条件下可能面临挑战。"
      },
      {
        "factor": "治理风险",
        "score": 85,
        "description": "协议治理较为分散，但大持有者仍有较大影响力。"
      }
    ],
    "recommendations": [
      "关注协议安全更新和审计报告",
      "了解协议治理机制和决策流程",
      "在使用前熟悉协议的风险参数"
    ]
  },
  "message": "风险分析完成",
  "timestamp": "2023-05-01T11:00:00.123456Z",
  "is_demo_data": false
}
```

### 2.3 获取钱包所用协议列表

获取指定钱包使用的所有协议列表。

- **路径**: `/protocol/list/{wallet_address}`
- **方法**: GET
- **参数**:
  - `wallet_address` (路径参数): 钱包地址

**响应示例**:

```json
{
  "status": "success",
  "data": [
    {
      "name": "Aave",
      "chain": "Ethereum",
      "tvl": 5000000000,
      "position_count": 2,
      "total_value_usd": 7500
    },
    {
      "name": "Compound",
      "chain": "Ethereum",
      "tvl": 3000000000,
      "position_count": 1,
      "total_value_usd": 10000
    }
  ],
  "message": "获取协议列表成功",
  "timestamp": "2023-05-01T11:30:00.123456Z",
  "is_demo_data": false
}
```

## 3. 市场数据API

### 3.1 获取资产市场数据

获取指定资产的市场数据。

- **路径**: `/market/asset/{asset}`
- **方法**: GET
- **参数**:
  - `asset` (路径参数): 资产符号，如 ETH、USDC 等

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "asset": "ETH",
    "price": 3000.25,
    "price_change_24h": 2.5,
    "volume_24h": 15000000000,
    "market_cap": 360000000000,
    "timestamp": "2023-05-01T12:00:00Z"
  },
  "message": "获取市场数据成功",
  "timestamp": "2023-05-01T12:00:30.123456Z",
  "is_demo_data": false
}
```

### 3.2 获取资产价格历史

获取指定资产的历史价格数据。

- **路径**: `/market/history/{asset}`
- **方法**: GET
- **参数**:
  - `asset` (路径参数): 资产符号
  - `days` (查询参数): 历史数据天数，默认30天
  - `interval` (查询参数): 数据间隔，可选值: `1h`, `4h`, `1d`，默认`1d`

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "asset": "ETH",
    "interval": "1d",
    "days": 30,
    "prices": [
      {
        "timestamp": "2023-04-01T00:00:00Z",
        "price": 2850.75
      },
      {
        "timestamp": "2023-04-02T00:00:00Z",
        "price": 2900.50
      },
      // ... 更多历史数据点
      {
        "timestamp": "2023-05-01T00:00:00Z",
        "price": 3000.25
      }
    ],
    "summary": {
      "min_price": 2750.25,
      "max_price": 3100.75,
      "avg_price": 2925.50,
      "volatility": 12.5
    }
  },
  "message": "获取历史价格数据成功",
  "timestamp": "2023-05-01T12:30:00.123456Z",
  "is_demo_data": false
}
```

### 3.3 获取Gas价格

获取当前ETH网络的Gas价格。

- **路径**: `/market/gas`
- **方法**: GET

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "base_fee_gwei": 20.5,
    "priority_fee_gwei": 2.0,
    "total_gwei": 22.5,
    "timestamp": "2023-05-01T13:00:00Z"
  },
  "message": "获取Gas价格成功",
  "timestamp": "2023-05-01T13:00:30.123456Z",
  "is_demo_data": false
}
```

## 4. 演示功能API

### 4.1 获取演示账户列表

获取可用的演示账户列表。

- **路径**: `/demo/accounts`
- **方法**: GET

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "accounts": [
      {
        "name": "高风险演示账户",
        "address": "0xdemo1...",
        "description": "高风险DeFi投资组合，包含多个投机性资产和高风险协议。"
      },
      {
        "name": "平衡型演示账户",
        "address": "0xdemo2...",
        "description": "平衡型DeFi投资组合，风险与回报适中。"
      },
      {
        "name": "保守型演示账户",
        "address": "0xdemo3...",
        "description": "保守型DeFi投资组合，主要使用稳定币和低风险协议。"
      }
    ]
  },
  "message": "获取演示账户成功",
  "timestamp": "2023-05-01T14:00:00.123456Z",
  "is_demo_data": true
}
```

### 4.2 获取演示状态

获取系统的演示模式状态。

- **路径**: `/demo/status`
- **方法**: GET

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "demo_mode": true,
    "api_version": "1.0.0",
    "last_refresh": "2023-05-01T08:00:00Z",
    "demo_accounts": [
      {"name": "高风险账户", "address": "0xdemo1..."},
      {"name": "平衡型账户", "address": "0xdemo2..."},
      {"name": "保守型账户", "address": "0xdemo3..."}
    ]
  },
  "message": "获取演示状态成功",
  "timestamp": "2023-05-01T14:30:00.123456Z",
  "is_demo_data": true
}
```

### 4.3 刷新演示数据

刷新系统的演示数据。

- **路径**: `/demo/refresh`
- **方法**: POST

**响应示例**:

```json
{
  "status": "success",
  "data": {
    "status": "success",
    "message": "演示数据已刷新",
    "timestamp": "2023-05-01T15:00:00Z"
  },
  "message": "刷新演示数据成功",
  "timestamp": "2023-05-01T15:00:30.123456Z",
  "is_demo_data": true
}
```

## API使用示例

### Python示例

```python
import requests

# 获取钱包风险分析
wallet_address = "0x1234..."
url = f"http://api.example.com/api/v1/wallet/{wallet_address}/risk"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print(f"钱包风险评分: {data['data']['overall_risk']['score']}")
    print(f"风险等级: {data['data']['overall_risk']['level']}")

    # 打印建议
    for i, rec in enumerate(data['data']['recommendations'], 1):
        print(f"建议 {i}: {rec}")
else:
    print(f"请求失败: {response.status_code}")
```

### JavaScript示例

```javascript
// 获取资产市场数据
const asset = 'ETH';
const url = `http://api.example.com/api/v1/market/asset/${asset}`;

fetch(url)
  .then(response => response.json())
  .then(data => {
    if (data.status === 'success') {
      console.log(`${asset} 当前价格: $${data.data.price}`);
      console.log(`24小时变化: ${data.data.price_change_24h}%`);
      console.log(`市值: $${data.data.market_cap}`);
    } else {
      console.error(`请求失败: ${data.message}`);
    }
  })
  .catch(error => console.error('API请求错误:', error));
```
