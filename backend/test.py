import requests
import datetime
import time


def get_today_klines(symbol, interval):
    """
    获取指定交易对当天的 K 线数据

    Args:
        symbol (str): 交易对，例如 "BTCUSDT"
        interval (str): 时间间隔，例如 "1m", "5m", "1h"

    Returns:
        list: K 线数据列表，如果请求失败返回 None
    """
    url = "https://api.binance.com/api/v3/klines"

    # 获取当天 0 点的时间戳 (UTC 时间)
    today_start_utc = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_ts = int(today_start_utc.timestamp() * 1000)

    params = {"symbol": symbol, "interval": interval, "startTime": start_ts}

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"请求失败，状态码: {response.status_code}")
        print(response.text)  # 打印错误信息，方便调试
        return None


if __name__ == "__main__":
    symbol = "ETHUSDT"  # 你想查询的交易对
    interval = "5m"  # 你想要的时间间隔

    klines_data = get_today_klines(symbol, interval)

    if klines_data:
        print(f"获取到 {symbol} {interval} 当天 K 线数据 ({len(klines_data)} 条):")
        # 打印前几条数据示例
        for kline in klines_data[:5]:
            print(kline)
    else:
        print("获取当天 K 线数据失败。")
