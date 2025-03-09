const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Position {
  protocol: string;
  asset: string;
  amount: number;
  leverage?: number;
  apy?: number;
}

export interface Portfolio {
  total_value: number;
  positions: Position[];
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
  ai_predictions: {
    [key: string]: {
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
      key_levels: {
        support: number[];
        resistance: number[];
        stop_loss: number;
        take_profit: number[];
      };
    };
  };
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
  description: string;
  supported_assets: string[];
  features: string[];
}

export interface MarketPrediction {
  asset: string;
  current_price: number;
  predicted_price: number;
  trend: string;
  risk_level: string;
  volatility: number;
  recommendations: string[];
  signals: string[];
  key_price_levels: {
    support: number[];
    resistance: number[];
  };
  alerts: any[];
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
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async getPortfolio(address: string): Promise<Portfolio> {
    return this.fetchJson<Portfolio>('/analyze', {
      method: 'POST',
      body: JSON.stringify({ wallet_address: address }),
    });
  }

  async getMarketData(asset: string): Promise<MarketData> {
    return this.fetchJson<MarketData>(`/market-data/${asset}`);
  }

  async getProtocols(): Promise<{ protocols: Protocol[] }> {
    return this.fetchJson<{ protocols: Protocol[] }>('/protocols');
  }

  async predictMarket(asset: string, timeFrame: string = '24h'): Promise<MarketPrediction> {
    return this.fetchJson<MarketPrediction>('/predict/market', {
      method: 'POST',
      body: JSON.stringify({ asset, time_frame: timeFrame }),
    });
  }

  async getProtocolRisk(protocolName: string): Promise<ProtocolRisk> {
    return this.fetchJson<ProtocolRisk>(`/predict/protocol/${encodeURIComponent(protocolName)}`);
  }

  async getGasPrice(): Promise<number> {
    return this.fetchJson<number>('/gas-price');
  }

  async getAlerts(address: string): Promise<Alert[]> {
    try {
      // 检查是否处于演示模式
      const demoMode = await this.isDemoMode();

      // 如果是演示模式且没有提供地址，使用演示地址
      if (demoMode && (!address || address === '0x0')) {
        const demoAddress = await this.getDemoAddress();
        if (demoAddress) {
          return this.getDemoAlerts();
        }
      }

      const response = await fetch(`${API_BASE_URL}/alerts/${address}`);

      if (!response.ok) {
        // 如果请求失败且处于演示模式，返回演示数据
        if (demoMode) {
          return this.getDemoAlerts();
        }
        throw new Error('Failed to fetch alerts');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching alerts:', error);
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

  async getMarketAlerts(address: string): Promise<Alert[]> {
    try {
      // 检查是否处于演示模式
      const demoMode = await this.isDemoMode();

      // 如果是演示模式且没有提供地址，使用演示地址
      if (demoMode && (!address || address === '0x0')) {
        const demoAddress = await this.getDemoAddress();
        if (demoAddress) {
          address = demoAddress;
        }
      }

      const response = await fetch(`${API_BASE_URL}/market/alerts/${address}`);

      if (!response.ok) {
        // 如果请求失败且处于演示模式，返回演示数据
        if (demoMode) {
          return this.getDemoAlerts();
        }
        throw new Error('Failed to fetch market alerts');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching market alerts:', error);
      throw error;
    }
  }

  async getMarketAnalysis(asset: string): Promise<MarketAnalysis> {
    try {
      const response = await fetch(`${API_BASE_URL}/market/analysis/${asset}`);

      if (!response.ok) {
        throw new Error('Failed to fetch market analysis');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching market analysis:', error);
      throw error;
    }
  }

  async getDemoStatus(): Promise<DemoStatus> {
    try {
      const response = await fetch(`${API_BASE_URL}/demo/status`);

      if (!response.ok) {
        throw new Error('Failed to fetch demo status');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching demo status:', error);
      throw error;
    }
  }

  async refreshDemoData(): Promise<{ status: string; message: string; timestamp: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/demo/refresh`);

      if (!response.ok) {
        throw new Error('Failed to refresh demo data');
      }

      return await response.json();
    } catch (error) {
      console.error('Error refreshing demo data:', error);
      throw error;
    }
  }

  async getSystemHealth(): Promise<SystemHealth> {
    try {
      const response = await fetch(`${API_BASE_URL}/system/health`);

      if (!response.ok) {
        throw new Error('Failed to fetch system health');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching system health:', error);
      throw error;
    }
  }

  async getHackathonGuide(): Promise<HackathonGuide> {
    try {
      const response = await fetch(`${API_BASE_URL}/hackathon-guide`);

      if (!response.ok) {
        throw new Error('Failed to fetch hackathon guide');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching hackathon guide:', error);
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
}

export const apiService = new ApiService();
