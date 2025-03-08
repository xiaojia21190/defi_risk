const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Position {
  protocol: string;
  asset: string;
  amount: number;
  leverage?: number;
  apy?: number;
}

export interface Portfolio {
  positions: Position[];
  totalValue: number;
  riskScore: number;
}

export interface Alert {
  id: string;
  type: string;
  severity: string;
  message: string;
  timestamp: string;
  protocol: string;
  asset: string;
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

export interface Protocol {
  name: string;
  version: string;
  supported_assets: string[];
  features: string[];
}

class ApiService {
  async getPortfolio(address: string): Promise<Portfolio> {
    try {
      const response = await fetch(`${API_BASE_URL}/portfolio/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ wallet_address: address }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch portfolio data');
      }

      const data = await response.json();
      return this.transformPortfolioData(data);
    } catch (error) {
      console.error('Error fetching portfolio:', error);
      throw error;
    }
  }

  async getAlerts(address: string): Promise<Alert[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts/${address}`);

      if (!response.ok) {
        throw new Error('Failed to fetch alerts');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching alerts:', error);
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

  async getSupportedProtocols(): Promise<{ protocols: Protocol[] }> {
    try {
      const response = await fetch(`${API_BASE_URL}/protocols`);

      if (!response.ok) {
        throw new Error('Failed to fetch supported protocols');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching supported protocols:', error);
      throw error;
    }
  }

  private transformPortfolioData(data: any): Portfolio {
    // 转换后端数据为前端所需格式
    return {
      positions: data.position_assessments?.map((pa: any) => ({
        protocol: pa.position.protocol,
        asset: pa.position.asset,
        amount: pa.position.amount,
        leverage: pa.position.leverage,
        apy: pa.position.apy,
      })) || [],
      totalValue: data.total_value || 0,
      riskScore: data.total_risk || 0,
    };
  }
}

export const apiService = new ApiService();
