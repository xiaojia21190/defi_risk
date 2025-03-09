export interface Protocol {
  id: string;
  name: string;
  description?: string;
  category: string;
  tvl?: number;
  riskScore?: number;
}

export async function fetchSupportedProtocols(): Promise<Protocol[]> {
  try {
    const response = await fetch('/api/protocols');
    if (!response.ok) {
      throw new Error('Failed to fetch protocols');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching protocols:', error);
    throw error;
  }
}
