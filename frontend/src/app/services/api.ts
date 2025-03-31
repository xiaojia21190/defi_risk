// 添加process类型定义
declare const process: {
  env: {
    NEXT_PUBLIC_API_URL?: string;
  };
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface Position {
  protocol: string;
  asset: string;
  amount?: number;
  leverage?: number;
  apy?: number;
  invest_type?: number;
  tokenList?: Array<{
    tokenSymbol: string;
    tokenLogo: string;
    coinAmount: string;
    currencyAmount: string;
    tokenPrecision: string;
    tokenAddress: string;
    network: string;
  }>;
}

export interface ProtocolPosition {
  protocol: string;
  total_assets: number;
  total_debts: number;
  leverage: number;
  positions: Position[];
}

export interface Portfolio {
  wallet_address: string;
  total_value: number;
  total_value_usd: number;
  position_count: number;
  protocol_count: number;
  positions: Position[];
  protocols: Protocol[];
  risk_level: string;
  recommendations: string[];
  market_analysis: {
    [key: string]: {
      current_price: number;
      volume_24h: number;
      market_cap: number;
      price_change_24h: number;
      volatility_30d: number;
    };
  };
  timestamp: string;
  is_demo_data: boolean;
}

export interface MarketData {
  asset: string;
  price: number;
  volume_24h: number;
  price_change_24h: number;
  market_cap: number;
}

export interface Protocol {
  name: string;
  description?: string;
  chain?: string;
  tvl?: number;
  supported_assets?: string[];
  features?: string[];
}

export interface MarketPrediction {
  trend: string;
  trend_strength: string;
  risk_level: string;
  predicted_price_range: {
    "24h": [number, number];
    "7d": [number, number];
  };
  technical_analysis: {
    ma_trend: string;
    macd_signal: string;
    bollinger_signal: string;
    volume_analysis: string;
  };
  recommendations: string[];
  trading_signals: string[];
  key_levels?: {
    support: number[];
    resistance: number[];
    stop_loss?: number;
    take_profit?: number[];
  };
  alerts?: Array<{ message: string }>;
}

export interface ProtocolRisk {
  risk_score: number;
  risk_level: string;
  security_score: number;
  liquidity_score: number;
  centralization_risk: string;
  audit_status: {
    score: number;
    last_audit_date: string;
    audit_firms: string[];
  };
  risk_factors: string[];
  recommendations: string[];
}

export interface Alert {
  id?: string;
  type: string;
  severity: string;
  message: string;
  timestamp: number;
  protocol: string;
  asset: string;
  details?: {
    value?: number;
    threshold?: number;
    recommendation?: string;
    rsi?: number;
    current_price?: number;
    previous_price?: number;
    price_change_24h?: number;
    volatility?: number;
    leverage?: number;
    safe_leverage?: number;
    risk_ratio?: number;
    position_size?: number;
    current_apy?: number;
    previous_apy?: number;
    apy_change?: number;
    correlation?: number;
    period?: string;
    ma7?: number;
    ma20?: number;
    analysis?: string;
    high_price?: number;
    low_price?: number;
    weighted_avg_price?: number;
    volume?: number;
  };
}

export interface RiskAssessment {
  risk_level: string;
  liquidation_risk: number;
  impermanent_loss_risk: number;
  market_volatility_risk: number;
  recommendations: string[];
  timestamp: string;
}

export interface MarketAnalysis {
  asset: string;
  current_price: number;
  predicted_price: number;
  price_change_prediction: number;
  volatility: number;
  rsi: number;
  trend: string;
  risk_level: string;
  signals: string[];
}

// 钱包风险评估接口
export interface WalletRiskAssessment {
  wallet_address: string;
  risk_score: number;
  risk_level: string;
  risk_factors: Array<{
    name: string;
    score: number;
    weight: number;
    description: string;
    trend: string;
  }>;
  risk_metrics: {
    [key: string]: number | string;
  };
  recommendations: string[];
  warnings: string[];
  monitoring_points: string[];
  analysis_timestamp: string;
  positions_summary?: {
    total_value: number;
    position_count: number;
    protocols: string[];
    assets: string[];
  };
  ai_enhanced?: boolean;
  timestamp?: string;
  is_demo_data?: boolean;
}

export interface DemoStatus {
  demo_mode: boolean;
  timestamp: string;
  environment: {
    network: string;
    chain_id: string;
    web3_connected: boolean;
  };
  demo_accounts: {
    address: string;
    type: string;
  }[];
  supported_assets: string[];
  refresh_interval: string;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  components: {
    web3: {
      status: string;
      provider: string;
      network: string;
    };
    assets: Record<string, boolean>;
    api_version: string;
    demo_mode: boolean;
  };
}

export interface HackathonGuide {
  title: string;
  description: string;
  network: {
    name: string;
    chainId: number;
    rpcUrl: string;
    blockExplorer: string;
  };
  demoMode: boolean;
  steps: {
    step: number;
    title: string;
    endpoint: string;
    description: string;
    parameters?: string[];
  }[];
  demoAccounts: {
    address: string;
    description: string;
  }[];
  supportedAssets: string[];
  websiteUrl: string;
}

import { demoProtocols } from './protocols';

class ApiService {
  // 检查是否处于演示模式
  private _demoMode: boolean | null = null;
  private _demoAddress: string | null = null;

  // 获取演示模式状态
  async isDemoMode(): Promise<boolean> {
    if (this._demoMode !== null) {
      return this._demoMode;
    }

    try {
      const status = await this.getDemoStatus();
      this._demoMode = status.demo_mode;
      if (status.demo_accounts && status.demo_accounts.length > 0) {
        this._demoAddress = status.demo_accounts[0].address;
      }
      return this._demoMode;
    } catch (error) {
      console.error('Error checking demo mode:', error);
      return false;
    }
  }

  // 获取演示账户地址
  async getDemoAddress(): Promise<string | null> {
    if (this._demoAddress !== null) {
      return this._demoAddress;
    }

    try {
      const status = await this.getDemoStatus();
      if (status.demo_accounts && status.demo_accounts.length > 0) {
        this._demoAddress = status.demo_accounts[0].address;
        return this._demoAddress;
      }
      return null;
    } catch (error) {
      console.error('Error getting demo address:', error);
      return null;
    }
  }

  private async fetchJson<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`API Error (${response.status}): ${errorText}`);
        throw new Error(`API Error: ${response.statusText}`);
      }

      return response.json();
    } catch (error) {
      console.error(`请求失败 (${endpoint}):`, error);
      throw error;
    }
  }

  async getPortfolio(address: string): Promise<Portfolio> {
    if (!address || address === '') {
      throw new Error('未提供钱包地址');
    }

    try {
      // 只获取钱包头寸
      const positionsResponse = await this.fetchJson<any>(`/wallet/${address}/positions`);

      // 初始化portfolio对象
      const portfolio: Portfolio = {
        wallet_address: address,
        total_value: positionsResponse.portfolio_summary?.total_value || 0,
        total_value_usd: positionsResponse.portfolio_summary?.total_value_usd || 0,
        position_count: positionsResponse.positions?.length || 0,
        protocol_count: positionsResponse.positions?.length || 0,
        positions: [],
        protocols: [],
        risk_level: "", // 初始为空，需要单独加载
        recommendations: [],
        market_analysis: {},
        timestamp: positionsResponse.timestamp || "",
        is_demo_data: positionsResponse.is_demo_data || false
      };

      // 转换头寸数据
      if (positionsResponse && positionsResponse.positions) {
        const positions: Position[] = [];

        for (const protocolPosition of positionsResponse.positions) {
          for (const position of protocolPosition.positions) {
            positions.push({
              protocol: protocolPosition.protocol,
              asset: position.asset,
              amount: position.amount,
              leverage: protocolPosition.leverage,
              apy: position.apy,
              invest_type: position.invest_type,
              tokenList: position.tokenList
            });
          }
        }

        portfolio.positions = positions;
      }

      return portfolio;
    } catch (error) {
      console.error('获取投资组合数据失败:', error);
      throw error;
    }
  }

  // 钱包风险评估接口
  async getWalletRiskAssessment(address: string): Promise<WalletRiskAssessment> {
    if (!address || address === '') {
      throw new Error('未提供钱包地址');
    }

    try {
      const response = await this.fetchJson<any>(`/wallet/${address}/risk`);

      // 格式化响应数据为WalletRiskAssessment类型
      return {
        wallet_address: address,
        risk_score: response.risk_score || 0,
        risk_level: response.risk_level || "中等",
        risk_factors: response.risk_factors || [],
        risk_metrics: response.risk_metrics || {},
        recommendations: response.recommendations || [],
        warnings: response.warnings || [],
        monitoring_points: response.monitoring_points || [],
        analysis_timestamp: response.analysis_timestamp || new Date().toISOString(),
        positions_summary: response.positions_summary,
        ai_enhanced: response.ai_enhanced || false,
        timestamp: response.timestamp,
        is_demo_data: response.is_demo_data || false
      };
    } catch (error) {
      console.error('获取钱包风险评估失败:', error);
      throw error;
    }
  }

  // 新方法：获取投资组合资产的市场分析
  async getPortfolioMarketAnalysis(assets: string[]): Promise<Record<string, any>> {
    if (!assets || assets.length === 0) {
      return {};
    }

    try {
      const marketAnalysis: Record<string, any> = {};

      for (const asset of assets) {
        try {
          const marketData = await this.getMarketData(asset);
          marketAnalysis[asset] = {
            current_price: marketData.price,
            volume_24h: marketData.volume_24h,
            market_cap: marketData.market_cap,
            price_change_24h: marketData.price_change_24h,
            volatility_30d: Math.abs(marketData.price_change_24h) // 简化处理
          };
        } catch (error) {
          console.error(`获取${asset}市场数据失败:`, error);
        }
      }

      return marketAnalysis;
    } catch (error) {
      console.error('获取投资组合市场分析失败:', error);
      return {};
    }
  }

  async getMarketData(asset: string): Promise<MarketData> {
    try {
      // 使用后端的市场数据API
      const response = await this.fetchJson<any>(`/market/data/${asset}`);

      // 将后端响应转换为前端期望的MarketData格式
      return {
        asset: response.asset,
        price: response.price,
        volume_24h: response.volume_24h,
        price_change_24h: response.price_change_24h,
        market_cap: response.market_cap
      };
    } catch (error) {
      console.error(`获取${asset}市场数据失败:`, error);
      throw error;
    }
  }

  async predictMarket(asset: string, timeFrame: string = '24h'): Promise<MarketPrediction> {
    try {
      // 使用后端的市场预测API
      const response = await this.fetchJson<any>(`/market/predict/${asset}?time_frame=${timeFrame}`);

      // 将后端响应转换为前端期望的MarketPrediction格式
      return {
        trend: response.trend || "neutral",
        trend_strength: response.trend_strength || "medium",
        risk_level: response.risk_level || "medium",
        predicted_price_range: response.predicted_price_range || {
          "24h": [0, 0],
          "7d": [0, 0]
        },
        technical_analysis: response.technical_analysis || {
          ma_trend: "neutral",
          macd_signal: "neutral",
          bollinger_signal: "neutral",
          volume_analysis: "normal"
        },
        recommendations: response.recommendations || [],
        trading_signals: response.trading_signals || [],
        key_levels: response.key_levels
      };
    } catch (error) {
      console.error(`获取${asset}市场预测失败:`, error);
      throw error;
    }
  }

  async getGasPrice(): Promise<number> {
    try {
      // 使用后端的gas价格API
      const response = await this.fetchJson<any>('/market/gas');
      return response || 0;
    } catch (error) {
      console.error('获取Gas价格失败:', error);
      return 0;
    }
  }

  async getAlerts(address: string): Promise<Alert[]> {
    try {
      const data = await this.fetchJson<Alert[]>(`/wallet/${address}/alerts`);
      return data;
    } catch (error) {
      console.error('Error fetching alerts:', error);
      return [];
    }
  }

  async analyzeWalletRisk(address: string): Promise<any> {
    try {
      const data = await this.fetchJson<any>(`/wallet/${address}/risk`);
      return data;
    } catch (error) {
      console.error('Error analyzing wallet risk:', error);
      throw error;
    }
  }

  async analyzeProtocolRisk(protocolName: string): Promise<any> {
    try {
      const data = await this.fetchJson<any>(`/protocol/risk/${protocolName}`);
      return data;
    } catch (error) {
      console.error('Error analyzing protocol risk:', error);
      throw error;
    }
  }

  async getDemoAlerts(): Promise<Alert[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/demo/alerts`);

      if (!response.ok) {
        throw new Error('Failed to fetch demo alerts');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching demo alerts:', error);
      throw error;
    }
  }

  async getMarketAnalysis(asset: string): Promise<MarketAnalysis> {
    try {
      // 使用predict/market端点获取市场分析数据
      const prediction = await this.predictMarket(asset);
      const marketData = await this.getMarketData(asset);

      // 将预测数据和市场数据转换为市场分析格式
      return {
        asset,
        current_price: marketData.price,
        predicted_price: prediction.predicted_price_range["24h"][1], // 使用24小时预测区间的上限作为预测价格
        price_change_prediction: ((prediction.predicted_price_range["24h"][1] / marketData.price) - 1) * 100,
        volatility: marketData.price_change_24h,
        rsi: 50, // 默认值，因为新接口不再提供RSI
        trend: prediction.trend,
        risk_level: prediction.risk_level,
        signals: prediction.trading_signals
      };
    } catch (error) {
      console.error('获取市场分析数据失败:', error);
      throw error;
    }
  }

  async getDemoStatus(): Promise<DemoStatus> {
    try {
      // 注意：后端暂时没有实现此端点，返回模拟数据
      console.warn('Demo status API endpoint is not implemented in the backend');

      // 返回模拟数据
      return {
        demo_mode: true,
        timestamp: new Date().toISOString(),
        environment: {
          network: "Sepolia",
          chain_id: "11155111",
          web3_connected: true
        },
        demo_accounts: [
          {
            address: "0xAbCdEf123456789AbCdEf123456789AbCdEf1234",
            type: "demo"
          }
        ],
        supported_assets: ["ETH", "USDC", "DAI", "BTC"],
        refresh_interval: "30m"
      };
    } catch (error) {
      console.error('获取演示状态失败:', error);
      throw error;
    }
  }

  async refreshDemoData(): Promise<{ status: string; message: string; timestamp: string }> {
    try {
      // 注意：后端暂时没有实现此端点，返回模拟数据
      console.warn('Demo refresh API endpoint is not implemented in the backend');

      // 返回模拟数据
      return {
        status: "success",
        message: "演示数据已刷新",
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('刷新演示数据失败:', error);
      throw error;
    }
  }

  async getSystemHealth(): Promise<SystemHealth> {
    try {
      // 注意：后端暂时没有实现此端点，返回模拟数据
      console.warn('System health API endpoint is not implemented in the backend');

      // 返回模拟数据
      return {
        status: "healthy",
        timestamp: new Date().toISOString(),
        components: {
          web3: {
            status: "connected",
            provider: "Alchemy",
            network: "Sepolia"
          },
          assets: {
            "ETH": true,
            "USDC": true,
            "DAI": true,
            "BTC": true
          },
          api_version: "1.0.0",
          demo_mode: true
        }
      };
    } catch (error) {
      console.error('获取系统健康状态失败:', error);
      throw error;
    }
  }

  async getHackathonGuide(): Promise<HackathonGuide> {
    try {
      // 注意：后端暂时没有实现此端点，返回模拟数据
      console.warn('Hackathon guide API endpoint is not implemented in the backend');

      // 返回模拟数据
      return {
        title: "DeFi风险分析API指南",
        description: "本指南将帮助您了解如何使用DeFi风险分析API进行开发",
        network: {
          name: "Sepolia",
          chainId: 11155111,
          rpcUrl: "https://eth-sepolia.g.alchemy.com/v2/demo",
          blockExplorer: "https://sepolia.etherscan.io"
        },
        demoMode: true,
        steps: [
          {
            step: 1,
            title: "连接钱包",
            endpoint: "/",
            description: "连接您的以太坊钱包以开始使用API",
            parameters: []
          },
          {
            step: 2,
            title: "分析投资组合",
            endpoint: "/analyze",
            description: "分析您的DeFi投资组合风险",
            parameters: ["wallet_address"]
          },
          {
            step: 3,
            title: "获取市场预测",
            endpoint: "/predict/market",
            description: "获取特定资产的市场预测",
            parameters: ["asset", "time_frame"]
          }
        ],
        demoAccounts: [
          {
            address: "0xAbCdEf123456789AbCdEf123456789AbCdEf1234",
            description: "演示账户，包含多种DeFi头寸"
          }
        ],
        supportedAssets: ["ETH", "USDC", "DAI", "BTC"],
        websiteUrl: "https://defi-risk-monitor.example.com"
      };
    } catch (error) {
      console.error('获取黑客松指南失败:', error);
      throw error;
    }
  }

  async quickTest(): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/test`);

      if (!response.ok) {
        throw new Error('API test failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Error running quick test:', error);
      throw error;
    }
  }

  // 添加一个通用的错误处理方法
  async safeApiCall<T>(apiCall: () => Promise<T>, fallback: T): Promise<T> {
    try {
      return await apiCall();
    } catch (error) {
      console.error('API调用失败:', error);
      return fallback;
    }
  }

  // 添加一个健康检查方法
  async checkApiHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/health`);
      return response.ok;
    } catch (error) {
      console.error('API健康检查失败:', error);
      return false;
    }
  }

  async getProtocols(walletAddress?: string): Promise<{ protocols: Protocol[] }> {
    try {
      // 使用后端的协议列表API，如果提供了钱包地址，则添加到查询参数中
      const endpoint = walletAddress
        ? `/protocol/list?wallet_address=${walletAddress}`
        : '/protocol/list';

      const response = await this.fetchJson<any>(endpoint);

      // 将后端响应转换为前端期望的Protocol[]格式
      const protocols: Protocol[] = response.protocols.map((p: any) => ({
        name: p.name,
        description: p.description || `${p.name}是一个DeFi协议，总锁仓价值(TVL)为$${(p.tvl / 1000000000).toFixed(2)}B`,
        supported_assets: p.supported_assets || ["ETH", "USDC", "DAI"],
        features: p.features || ["借贷", "流动性挖矿"]
      }));

      return { protocols };
    } catch (error) {
      console.error('获取协议列表失败:', error);
      // 出错时返回演示数据
      return { protocols: demoProtocols };
    }
  }
}

export const apiService = new ApiService();
