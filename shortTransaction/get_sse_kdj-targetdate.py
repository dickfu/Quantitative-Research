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
# 专家级防封配置 (从用户代码继承)
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
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6'
    }
]


# ==========================================
# 用户提供的核心函数 (已集成)
# ==========================================

def index_stock_cons_csindex(symbol: str = "000300") -> pd.DataFrame:
    """中证指数网站-成份股目录"""
    url = f"https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/{symbol}cons.xls"
    try:
        r = requests.get(url, proxies=proxies, timeout=10)
        r.raise_for_status()  # 如果请求失败则引发HTTPError
        temp_df = pd.read_excel(BytesIO(r.content))
        temp_df.columns = ["日期", "指数代码", "指数名称", "指数英文名称", "成分券代码", "成分券名称", "成分券英文名称",
                           "交易所", "交易所英文名称"]
        temp_df["日期"] = pd.to_datetime(temp_df["日期"], format="%Y%m%d", errors="coerce").dt.date
        temp_df["指数代码"] = temp_df["指数代码"].astype(str).str.zfill(6)
        temp_df["成分券代码"] = temp_df["成分券代码"].astype(str).str.zfill(6)
        return temp_df
    except requests.exceptions.RequestException as e:
        print(f"获取成分股失败: {e}")
        return pd.DataFrame()


def stock_zh_a_hist(symbol: str, start_date: str, end_date: str, adjust: str = "qfq",
                    timeout: float = 10, period: str = "daily") -> pd.DataFrame:
    """东方财富网-行情首页-沪深京 A 股-每日行情"""
    market_code = '1' if symbol.startswith("6") else '0'
    adjust_dict = {"qfq": "1", "hfq": "2", "": "0"}
    period_dict = {"daily": "101", "weekly": "102", "monthly": "103"}
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": period_dict[period],
        "fqt": adjust_dict[adjust],
        "secid": f"{market_code}.{symbol}",
        "beg": start_date,
        "end": end_date,
        "lmt": "10000"  # 确保获取足够的数据
    }
    try:
        selected_headers = random.choice(default_headers)
        r = requests.get(url, params=params, timeout=timeout, proxies=proxies, headers=selected_headers)
        r.raise_for_status()
        data_json = r.json()
        if not (data_json.get("data") and data_json["data"].get("klines")):
            return pd.DataFrame()
        temp_df = pd.DataFrame([item.split(",") for item in data_json["data"]["klines"]])
        temp_df.columns = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额",
                           "换手率"]
        temp_df['股票代码'] = symbol
        for col in ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]:
            temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
        temp_df['日期'] = pd.to_datetime(temp_df['日期']).dt.date
        return temp_df
    except Exception as e:
        # print(f"获取股票 {symbol} 数据时出错: {e}") # 减少不必要的打印
        return pd.DataFrame()


def calculate_kdj(df, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    df_kdj = df.copy()
    low_list = df_kdj['最低'].rolling(window=n).min()
    high_list = df_kdj['最高'].rolling(window=n).max()
    rsv = (df_kdj['收盘'] - low_list) / (high_list - low_list) * 100
    df_kdj['k'] = rsv.ewm(com=m1 - 1, adjust=False).mean()
    df_kdj['d'] = df_kdj['k'].ewm(com=m2 - 1, adjust=False).mean()
    df_kdj['j'] = 3 * df_kdj['k'] - 2 * df_kdj['d']
    return df_kdj


# ==========================================
# 主逻辑：计算指定日期的KDJ
# ==========================================

def main(target_date_str: str):
    """主函数，用于计算指定日期的所有上证成分股的KDJ值"""
    # 1. 获取成分股
    print("正在获取上证指数成分股列表...")
    stocks_df = index_stock_cons_csindex(symbol="000001")
    if stocks_df.empty:
        print("未能获取到股票列表，程序终止。")
        return

    stock_list = stocks_df['成分券代码'].tolist()
    name_map = dict(zip(stocks_df['成分券代码'], stocks_df['成分券名称']))
    total_count = len(stock_list)
    print(f"成功获取 {total_count} 只成分股。")

    # 2. 设置日期范围
    # 为了计算当天的KDJ，需要获取包含当天在内的一段历史数据
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        # 向前追溯100天以确保KDJ计算的准确性
        start_date = (target_date - timedelta(days=100)).strftime("%Y%m%d")
        end_date = target_date.strftime("%Y%m%d")
    except ValueError:
        print("日期格式错误，请输入 'YYYY-MM-DD' 格式的日期。")
        return

    results = []
    print(f"开始计算 {target_date_str} 的KDJ数据...")
    start_time = time.time()

    # 3. 循环处理每只股票
    for i, code in enumerate(stock_list):
        stock_name = name_map.get(code, "未知")
        try:
            # 获取历史数据
            df_hist = stock_zh_a_hist(symbol=code,period="daily", start_date=start_date, end_date=end_date)

            if df_hist.empty or len(df_hist) < 9:
                continue

            # 计算KDJ
            df_with_kdj = calculate_kdj(df_hist)

            # 筛选出目标日期的数据
            target_day_data = df_with_kdj[df_with_kdj['日期'] == target_date]

            if not target_day_data.empty:
                latest = target_day_data.iloc[0]
                results.append({
                    "股票代码": code,
                    "股票名称": stock_name,
                    "日期": latest['日期'],
                    "K": round(latest['k'], 2),
                    "D": round(latest['d'], 2),
                    "J": round(latest['j'], 2)
                })

            # 打印进度并适当休眠
            if (i + 1) % 10 == 0:
                elapsed = time.time() - start_time
                print(f"已处理 {i + 1}/{total_count}... 耗时: {elapsed:.1f}s")

            time.sleep(random.uniform(2.5, 7.5))  # 降低请求频率
        except Exception as e:
            print(f"处理股票 {code} 时出错: {e}")

    # 4. 汇总并保存结果
    if results:
        result_df = pd.DataFrame(results)
        print(f"\n--- {target_date_str} KDJ 计算结果 (前10行) ---")
        print(result_df.head(10))

        output_file = f"doc/sse_kdj_results_{target_date_str}.csv"
        # 检查文件是否存在，决定是否写入表头
        write_header = not os.path.exists(output_file)
        # 以追加模式写入，不写入索引，指定编码
        result_df.to_csv(output_file, index=False, encoding='utf_8_sig',header=write_header)
        print(f"\n结果已全部保存至 {output_file}")
    else:
        print("未计算出任何结果，请检查日期是否为交易日。")


if __name__ == "__main__":
    # =======================================================
    # 专家提示：请在此处修改为您想查询的日期
    # =======================================================
    target_date_input = "2025-04-07"

    print(f"任务启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    main(target_date_str=target_date_input)
    print(f"任务结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")