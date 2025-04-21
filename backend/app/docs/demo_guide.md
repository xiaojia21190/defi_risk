# DeFi风险分析系统 - 演示指南

## 1. 演示模式概述

DeFi风险分析系统内置了完整的演示模式，无需真实区块链数据或外部API连接即可展示系统的核心功能。演示模式提供了一套预定义的演示账户、模拟数据和示例场景，使您能够全面体验系统的风险分析能力。

本指南将帮助您设置和使用演示模式，展示系统的关键功能，以及准备一个有效的黑客松演示。

## 2. 演示模式设置

### 2.1 启用演示模式

演示模式可以通过以下方式启用：

1. **环境变量配置**：
   - 设置环境变量`DEMO_MODE=True`
   - 在`.env`文件中添加`DEMO_MODE=True`

2. **运行时配置**：
   ```bash
   # 启动应用并启用演示模式
   DEMO_MODE=True python -m app.main
   ```

3. **Docker配置**：
   ```bash
   # 使用Docker启动并启用演示模式
   docker run -e DEMO_MODE=True -p 8000:8000 defi-risk-api
   ```

### 2.2 配置演示账户

系统提供了多个预设的演示账户，每个账户代表不同的风险特征和投资组合：

- `0xdemo1...` - 高风险投资组合（大量小市值代币和新协议）
- `0xdemo2...` - 平衡型投资组合（主流和新兴资产混合）
- `0xdemo3...` - 保守型投资组合（主要是大型稳定币和顶级协议）

这些演示账户在`config/demo_accounts.yaml`中定义：

```yaml
DEMO_ACCOUNTS:
  - name: "高风险演示账户"
    address: "0xdemo1..."
    description: "高风险DeFi投资组合，包含多个投机性资产和高风险协议。"
    risk_profile: "high"

  - name: "平衡型演示账户"
    address: "0xdemo2..."
    description: "平衡型DeFi投资组合，风险与回报适中。"
    risk_profile: "medium"

  - name: "保守型演示账户"
    address: "0xdemo3..."
    description: "保守型DeFi投资组合，主要使用稳定币和低风险协议。"
    risk_profile: "low"
```

您可以添加自定义演示账户或修改现有账户的特征。

## 3. 演示核心功能

### 3.1 获取演示状态和账户

演示前，可以先展示系统的演示模式状态和可用账户：

```bash
# 获取演示模式状态
curl http://localhost:8000/api/v1/demo/status

# 获取演示账户列表
curl http://localhost:8000/api/v1/demo/accounts
```

这将返回可用的演示账户信息，包括账户地址和描述。

### 3.2 钱包风险分析演示

钱包风险分析是系统的核心功能，可以通过以下步骤展示：

1. **获取钱包头寸**：
   ```bash
   curl http://localhost:8000/api/v1/wallet/0xdemo1.../positions
   ```

   此请求将返回演示钱包的投资头寸，包括：
   - 各协议中的资产
   - 资产价值和APY
   - 使用的协议列表和特征

2. **分析钱包风险**：
   ```bash
   curl http://localhost:8000/api/v1/wallet/0xdemo1.../risk
   ```

   此请求将返回全面的风险分析，包括：
   - 整体风险评分和等级
   - 五大风险维度的分解
   - 详细风险因子分析
   - 风险缓解建议
   - 监控重点

3. **获取钱包预警**：
   ```bash
   curl http://localhost:8000/api/v1/wallet/0xdemo1.../alerts
   ```

   此请求将返回针对钱包的风险预警，包括：
   - 价格波动预警
   - 协议风险预警
   - 流动性风险预警
   - 相关性风险预警

### 3.3 市场场景模拟演示

场景模拟功能可以展示钱包在不同市场条件下的表现：

```bash
# 市场崩盘场景
curl http://localhost:8000/api/v1/wallet/0xdemo1.../scenario-simulation?scenario=market_crash

# 流动性冲击场景
curl http://localhost:8000/api/v1/wallet/0xdemo1.../scenario-simulation?scenario=liquidity_shock

# 协议漏洞利用场景
curl http://localhost:8000/api/v1/wallet/0xdemo1.../scenario-simulation?scenario=protocol_exploit

# 监管打击场景
curl http://localhost:8000/api/v1/wallet/0xdemo1.../scenario-simulation?scenario=regulatory_crackdown
```

每个场景将返回：
- 模拟后的投资组合价值
- 价值变化百分比
- 最受影响和最不受影响的资产
- 针对该场景的风险缓解建议

### 3.4 协议风险分析演示

可以展示针对特定DeFi协议的风险分析：

```bash
# 获取协议信息
curl http://localhost:8000/api/v1/protocol/Aave

# 分析协议风险
curl http://localhost:8000/api/v1/protocol/risk/Aave
```

协议风险分析将返回：
- 协议风险评分和等级
- 智能合约风险因子
- 经济模型风险因子
- 治理风险因子
- 风险缓解建议

### 3.5 市场数据演示

可以展示系统对市场数据的分析：

```bash
# 获取资产市场数据
curl http://localhost:8000/api/v1/market/asset/ETH

# 获取资产价格历史
curl http://localhost:8000/api/v1/market/history/ETH?days=30&interval=1d

# 获取Gas价格
curl http://localhost:8000/api/v1/market/gas
```

## 4. 黑客松演示场景

以下是几个为黑客松准备的演示场景，每个场景展示系统的不同方面：

### 4.1 场景一：投资组合风险对比

这个场景展示不同风险特征的投资组合分析：

1. 获取高风险账户的风险分析
2. 获取保守型账户的风险分析
3. 对比两者的风险评分、风险因子和建议
4. 强调系统的风险评分透明性和多维度风险分析

**脚本示例**：
```bash
#!/bin/bash
echo "高风险投资组合分析..."
curl -s http://localhost:8000/api/v1/wallet/0xdemo1.../risk | jq .data.overall_risk

echo "保守型投资组合分析..."
curl -s http://localhost:8000/api/v1/wallet/0xdemo3.../risk | jq .data.overall_risk

echo "风险因子对比..."
# 这里可以展示特定风险因子的对比
```

### 4.2 场景二：市场崩盘模拟

这个场景展示系统的场景模拟能力：

1. 展示平衡型账户的当前状态
2. 运行市场崩盘场景模拟
3. 展示模拟后的投资组合状态
4. 展示系统生成的风险缓解建议

**脚本示例**：
```bash
#!/bin/bash
echo "当前投资组合状态..."
curl -s http://localhost:8000/api/v1/wallet/0xdemo2.../positions | jq .data.total_value_usd

echo "市场崩盘模拟..."
curl -s http://localhost:8000/api/v1/wallet/0xdemo2.../scenario-simulation?scenario=market_crash | jq .data.simulated_portfolio

echo "风险缓解建议..."
curl -s http://localhost:8000/api/v1/wallet/0xdemo2.../scenario-simulation?scenario=market_crash | jq .data.recommendations
```

### 4.3 场景三：协议风险分析

这个场景展示系统的协议风险分析能力：

1. 展示流行协议的基本信息
2. 展示协议的风险分析
3. 重点展示智能合约风险和治理风险
4. 展示针对使用该协议的用户的建议

**脚本示例**：
```bash
#!/bin/bash
echo "协议基本信息..."
curl -s http://localhost:8000/api/v1/protocol/Aave | jq .data

echo "协议风险分析..."
curl -s http://localhost:8000/api/v1/protocol/risk/Aave | jq .data.risk_factors

echo "使用建议..."
curl -s http://localhost:8000/api/v1/protocol/risk/Aave | jq .data.recommendations
```

## 5. 前端演示

虽然演示主要基于API调用，但可以使用以下工具提供更直观的视觉展示：

### 5.1 API交互工具

- **Swagger UI**: 系统自带的API文档界面，访问`http://localhost:8000/docs`
- **Postman**: 可以创建预设的请求集合，方便演示
- **curl + jq**: 在终端中格式化展示JSON响应

### 5.2 数据可视化

可以准备一些预设的数据可视化图表来展示系统分析的结果：

- 风险因子雷达图
- 资产价格和风险相关性热图
- 市场场景模拟前后的投资组合价值变化条形图

## 6. 演示常见问题解答

### 如何刷新演示数据？

演示数据可以通过API刷新：

```bash
curl -X POST http://localhost:8000/api/v1/demo/refresh
```

这将重新生成所有演示数据，使每次演示都有一些变化。

### 演示数据与真实数据有何不同？

演示数据在结构上与真实数据完全相同，但值是模拟生成的。所有API响应中的`is_demo_data`字段标记了数据的来源。

### 如何在演示中切换不同账户？

只需在API请求中更改钱包地址，使用不同的演示账户地址：

```bash
# 高风险账户
curl http://localhost:8000/api/v1/wallet/0xdemo1.../risk

# 平衡型账户
curl http://localhost:8000/api/v1/wallet/0xdemo2.../risk

# 保守型账户
curl http://localhost:8000/api/v1/wallet/0xdemo3.../risk
```

### 如何展示系统的即时响应能力？

可以准备多个终端窗口，同时运行不同的API请求，展示系统能够并行处理多种风险分析任务。

## 7. 演示提示和技巧

1. **准备脚本**：提前准备好演示脚本，避免在演示过程中输入长命令
2. **分步展示**：从基础功能逐步展示到高级功能，遵循自然理解曲线
3. **突出亮点**：重点强调系统的创新点和竞争优势
4. **对比展示**：使用不同风险特征的账户对比展示风险分析结果
5. **故事线**：创建一个故事线，如"投资者如何使用系统识别并缓解风险"
6. **准备备用方案**：如果演示环境有限制，准备预录制的API响应样本

---

通过本演示指南，您应该能够有效地展示DeFi风险分析系统的核心能力和价值主张，向评委和观众清晰地传达系统如何解决DeFi投资风险管理的实际问题。
