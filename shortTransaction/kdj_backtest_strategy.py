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
# 沿用用户提供的防封配置
# ==========================================
proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
}

default_headers = [
    {
        'Host': 'push2his.eastmoney.com',
        'Connection': 'close',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0',
        'Upgrade-Insecure-Requests': '1'
    }, {
        'Host': 'push2his.eastmoney.com',
        'Connection': 'close',
        'sec-ch-ua': '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    }
]

# ==========================================
# 数据获取与指标计算函数
# ==========================================

def index_stock_cons_csindex(symbol: str = "000001") -> pd.DataFrame:
    """获取中证指数成份股"""
    url = f"https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/{symbol}cons.xls"
    try:
        r = requests.get(url, proxies=proxies, timeout=10)
        r.raise_for_status()
        temp_df = pd.read_excel(BytesIO(r.content))
        temp_df.columns = ["日期", "指数代码", "指数名称", "指数英文名称", "成分券代码", "成分券名称", "成分券英文名称", "交易所", "交易所英文名称"]
        temp_df["成分券代码"] = temp_df["成分券代码"].astype(str).str.zfill(6)
        return temp_df
    except requests.exceptions.RequestException as e:
        print(f"获取成分股失败: {e}")
        return pd.DataFrame()

def stock_zh_a_hist(symbol: str, start_date: str, end_date: str, adjust: str = "qfq", timeout: float = 10) -> pd.DataFrame:
    """获取A股历史行情数据"""
    market_code = '1' if symbol.startswith("6") else '0'
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": "101", # 日线
        "fqt": {"qfq": "1", "hfq": "2", "": "0"}[adjust],
        "secid": f"{market_code}.{symbol}",
        "beg": start_date,
        "end": end_date,
        "lmt": "10000"
    }
    try:
        r = requests.get(url, params=params, timeout=timeout, proxies=proxies, headers=random.choice(default_headers))
        r.raise_for_status()
        data_json = r.json()
        if not (data_json.get("data") and data_json["data"].get("klines")):
            return pd.DataFrame()
        temp_df = pd.DataFrame([item.split(",") for item in data_json["data"]["klines"]])
        temp_df.columns = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
        for col in temp_df.columns:
            if col != '日期':
                temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
        temp_df['日期'] = pd.to_datetime(temp_df['日期']).dt.date
        return temp_df
    except Exception:
        return pd.DataFrame()

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

# ==========================================
# 策略回测主逻辑
# ==========================================

def run_backtest(start_date_str: str, end_date_str: str):
    """执行KDJ策略回测"""
    # 1. 获取成分股
    print("正在获取上证指数成分股列表...")
    stocks_df = index_stock_cons_csindex(symbol="000001")
    if stocks_df.empty: return

    stock_list = stocks_df['成分券代码'].tolist()
    name_map = dict(zip(stocks_df['成分券代码'], stocks_df['成分券名称']))
    print(f"成功获取 {len(stock_list)} 只成分股。")

    # 2. 设置回测日期范围
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    # 为KDJ计算预留足够数据
    fetch_start_date = (start_date - timedelta(days=100)).strftime("%Y%m%d")
    fetch_end_date = end_date.strftime("%Y%m%d")

    trades = []
    print(f"开始回测 {start_date_str} 到 {end_date_str} 的KDJ策略...")
    start_time = time.time()

    # 3. 遍历每只股票进行回测
    for i, code in enumerate(stock_list):
        # 获取历史数据
        df_hist = stock_zh_a_hist(symbol=code, start_date=fetch_start_date, end_date=fetch_end_date)
        if df_hist.empty or len(df_hist) < 10: continue

        # 计算KDJ
        df_with_kdj = calculate_kdj(df_hist)
        df_with_kdj['j_prev'] = df_with_kdj['j'].shift(1)

        # 筛选出在回测期内的交易日
        df_backtest_period = df_with_kdj[df_with_kdj['日期'] >= start_date]

        # 寻找买入信号
        buy_signals = df_backtest_period[(df_backtest_period['j_prev'] < 0) & (df_backtest_period['j'] > 0)]

        for _, row in buy_signals.iterrows():
            buy_date = row['日期']
            buy_price = row['收盘'] # 假设按当天收盘价买入

            # 寻找卖出日期（买入后的下一个交易日）
            sell_date_row = df_with_kdj[df_with_kdj['日期'] > buy_date]
            if not sell_date_row.empty:
                sell_date = sell_date_row.iloc[0]['日期']
                sell_price = sell_date_row.iloc[0]['收盘']
                profit = (sell_price - buy_price) / buy_price
                trades.append({
                    '股票代码': code,
                    '股票名称': name_map.get(code, '未知'),
                    '买入日期': buy_date,
                    '买入价格': buy_price,
                    '卖出日期': sell_date,
                    '卖出价格': sell_price,
                    '收益率': profit
                })
        
        if (i + 1) % 20 == 0:
            print(f"已分析 {i + 1}/{len(stock_list)} 只股票... 耗时: {time.time() - start_time:.1f}s")
        time.sleep(random.uniform(0.1, 0.2))

    # 4. 分析并展示回测结果
    if not trades:
        print("\n回测期间未产生任何交易信号。")
        return

    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    winning_trades = trades_df[trades_df['收益率'] > 0]
    losing_trades = trades_df[trades_df['收益率'] <= 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
    avg_profit = trades_df['收益率'].mean()
    total_profit = (1 + trades_df['收益率']).prod() - 1

    print("\n--- KDJ策略回测结果 ---")
    print(f"回测周期: {start_date_str} 到 {end_date_str}")
    print(f"总交易次数: {total_trades}")
    print(f"胜率: {win_rate:.2%}")
    print(f"平均单次收益率: {avg_profit:.2%}")
    print(f"总策略收益率 (基于复利): {total_profit:.2%}")
    print(f"盈利次数: {len(winning_trades)}")
    print(f"亏损次数: {len(losing_trades)}")
    print(f"平均盈利: {winning_trades['收益率'].mean():.2%}" if not winning_trades.empty else "平均盈利: N/A")
    print(f"平均亏损: {losing_trades['收益率'].mean():.2%}" if not losing_trades.empty else "平均亏损: N/A")

    output_file = f"kdj_backtest_trades_{start_date_str}_to_{end_date_str}.csv"
    trades_df.to_csv(output_file, index=False, encoding='utf_8_sig')
    print(f"\n详细交易记录已保存至: {output_file}")

if __name__ == "__main__":
    # =======================================================
    # 专家提示：请在此处设置您的回测周期
    # =======================================================
    backtest_start_date = "2023-01-01"
    backtest_end_date = "2024-01-01"
    
    run_backtest(start_date_str=backtest_start_date, end_date_str=backtest_end_date)
