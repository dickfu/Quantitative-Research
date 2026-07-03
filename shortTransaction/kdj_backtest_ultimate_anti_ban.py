import os
import random
import pandas as pd
import numpy as np
import time
import sys
from io import BytesIO
import requests
from datetime import datetime, timedelta

# ==========================================
# 终极防封配置：动态代理与深度伪装
# ==========================================

# 建议：在实际使用中，您可以购买付费代理池API，并在此处动态获取
# 以下为演示逻辑，您可以替换为真实的代理列表
PROXY_LIST = [
    # "http://user:pass@host:port",
]

def get_random_headers():
    """生成高度随机的浏览器请求头"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (AppleWebKit/537.36, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.188"
    ]
    return {
        'Host': 'push2his.eastmoney.com',
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': random.choice(user_agents),
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://quote.eastmoney.com/',
        'X-Requested-With': 'XMLHttpRequest'
    }

def get_proxy():
    """获取随机代理（如果有配置）"""
    if PROXY_LIST:
        p = random.choice(PROXY_LIST)
        return {"http": p, "https": p}
    return None

# ==========================================
# 核心数据抓取函数（带自适应重试）
# ==========================================

def request_with_retry(url, params, max_retries=5):
    """带自适应冷却和代理切换的请求函数"""
    for attempt in range(max_retries):
        try:
            proxy = get_proxy()
            headers = get_random_headers()
            
            # 基础延时 + 随机抖动
            time.sleep(random.uniform(1.0, 3.0))
            
            response = requests.get(url, params=params, headers=headers, proxies=proxy, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                wait_time = (attempt + 1) * 30 # 遭遇403，大幅增加等待时间
                print(f"\n[警告] 触发403封禁，进入冷却模式，等待 {wait_time}秒...")
                time.sleep(wait_time)
            else:
                print(f"\n[错误] 状态码: {response.status_code}，重试中...")
                
        except Exception as e:
            wait_time = (attempt + 1) * 10
            print(f"\n[异常] 连接失败: {e}，{wait_time}秒后重试...")
            time.sleep(wait_time)
            
    return None

def stock_zh_a_hist_safe(symbol, start_date, end_date):
    """安全获取历史行情"""
    market_code = '1' if symbol.startswith("6") else '0'
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": "101",
        "fqt": "1",
        "secid": f"{market_code}.{symbol}",
        "beg": start_date,
        "end": end_date,
        "lmt": "10000"
    }
    
    data_json = request_with_retry(url, params)
    if data_json and data_json.get("data") and data_json["data"].get("klines"):
        temp_df = pd.DataFrame([item.split(",") for item in data_json["data"]["klines"]])
        temp_df.columns = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
        for col in temp_df.columns:
            if col != '日期':
                temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
        temp_df['日期'] = pd.to_datetime(temp_df['日期']).dt.date
        return temp_df
    return pd.DataFrame()

# ==========================================
# 策略计算与回测逻辑
# ==========================================

def calculate_kdj(df, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    df_kdj = df.copy()
    low_list = df_kdj['最低'].rolling(window=n, min_periods=1).min()
    high_list = df_kdj['最高'].rolling(window=n, min_periods=1).max()
    rsv = (df_kdj['收盘'] - low_list) / (high_list - low_list) * 100
    df_kdj['k'] = rsv.ewm(com=m1 - 1, adjust=False).mean()
    df_kdj['d'] = df_kdj['k'].ewm(com=m2 - 1, adjust=False).mean()
    df_kdj['j'] = 3 * df_kdj['k'] - 2 * df_kdj['d']
    return df_kdj

def run_backtest_safe(start_date_str, end_date_str):
    """执行具备防封能力的KDJ策略回测"""
    # 1. 获取成分股
    print("正在获取上证指数成分股列表...")
    # 这里使用akshare默认接口，通常成分股列表请求频率较低，不易被封
    try:
        stocks_df = ak.index_stock_cons_csindex(symbol="000001")
    except:
        print("获取成分股失败，请检查网络。")
        return

    stock_list = stocks_df['成分券代码'].tolist()
    name_map = dict(zip(stocks_df['成分券代码'], stocks_df['成分券名称']))
    
    # 2. 设置日期
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    fetch_start = (start_date - timedelta(days=100)).strftime("%Y%m%d")
    fetch_end = end_date.strftime("%Y%m%d")

    trades = []
    print(f"开始安全回测模式: {start_date_str} 至 {end_date_str}")
    
    # 3. 遍历处理
    for i, code in enumerate(stock_list):
        # 每处理30只股票，强制休息一分钟，彻底打断抓取特征
        if i > 0 and i % 30 == 0:
            print(f"\n[维护] 已处理 {i}只，强制进入深度休眠 60秒...")
            time.sleep(60)

        df_hist = stock_zh_a_hist_safe(code, fetch_start, fetch_end)
        if df_hist.empty: continue

        df_kdj = calculate_kdj(df_hist)
        df_kdj['j_prev'] = df_kdj['j'].shift(1)
        
        # 策略逻辑：前日J<0，今日J>0
        signals = df_kdj[(df_kdj['日期'] >= start_date) & (df_kdj['j_prev'] < 0) & (df_kdj['j'] > 0)]
        
        for _, row in signals.iterrows():
            buy_date = row['日期']
            # 寻找次日收盘价
            next_day = df_kdj[df_kdj['日期'] > buy_date]
            if not next_day.empty:
                sell_row = next_day.iloc[0]
                profit = (sell_row['收盘'] - row['收盘']) / row['收盘']
                trades.append({
                    '代码': code, '名称': name_map.get(code),
                    '买入日期': buy_date, '买入价': row['收盘'],
                    '卖出日期': sell_row['日期'], '卖出价': sell_row['收盘'],
                    '收益率': profit
                })
        
        sys.stdout.write(f"\r进度: {i+1}/{len(stock_list)} | 已捕获交易: {len(trades)}")
        sys.stdout.flush()

    # 4. 结果导出
    if trades:
        res_df = pd.DataFrame(trades)
        output = f"safe_kdj_backtest_{start_date_str}.csv"
        res_df.to_csv(output, index=False, encoding='utf_8_sig')
        print(f"\n\n回测完成！胜率: {(res_df['收益率']>0).mean():.2%}, 平均收益: {res_df['收益率'].mean():.2%}")
        print(f"详细记录已保存至: {output}")
    else:
        print("\n\n未发现交易信号。")

if __name__ == "__main__":
    # 专家提示：如果依然被封，请在 PROXY_LIST 中添加有效的代理IP
    run_backtest_safe("2023-01-01", "2024-01-01")
