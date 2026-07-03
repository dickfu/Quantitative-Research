import os
import random

import akshare as ak
import pandas as pd
import numpy as np
import time
import sys
from io import BytesIO, StringIO
import requests
import random
from fake_useragent import UserAgent

proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
}

# default_headers = [
#     # {
#     # 'Host': 'push2his.eastmoney.com',
#     # 'Connection': 'close',
#     # 'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
#     # 'sec-ch-ua-mobile': '?0',
#     # 'sec-ch-ua-platform': '"Windows"',
#     # 'Upgrade-Insecure-Requests': '1',
#     # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
#     # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
#     # 'Sec-Fetch-Site': 'none',
#     # 'Sec-Fetch-Mode': 'navigate',
#     # 'Sec-Fetch-User': '?1',
#     # 'Sec-Fetch-Dest': 'document',
#     # 'Accept-Language': 'zh-CN,zh;q=0.9',
#     # },
#     {
#     'Host': 'push2his.eastmoney.com',
#     'Connection': 'close',
#     'Accept': 'application/json, text/plain, */*',
#     'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0',
#     'Upgrade-Insecure-Requests': '1'
#
# }, {
#     'Host': 'push2his.eastmoney.com',
#     'Connection': 'close',
#     'sec-ch-ua': '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
#     'sec-ch-ua-mobile': '?0',
#     'sec-ch-ua-platform': '"Windows"',
#     'Upgrade-Insecure-Requests': '1',
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0',
#     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
#     'Sec-Fetch-Site': 'none',
#     'Sec-Fetch-Mode': 'navigate',
#     'Sec-Fetch-User': '?1',
#     'Sec-Fetch-Dest': 'document',
#     'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6'
# }]
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
#默认请求头

# 方法1：使用fake-useragent


def index_stock_cons_csindex(symbol: str = "000300") -> pd.DataFrame:
    """
    中证指数网站-成份股目录
    https://www.csindex.com.cn/zh-CN/indices/index-detail/000300
    :param symbol: 指数代码, 可以通过 ak.index_stock_info() 函数获取
    :type symbol: str
    :return: 最新指数的成份股
    :rtype: pandas.DataFrame
    """
    url = (
        f"https://oss-ch.csindex.com.cn/static/"
        f"html/csindex/public/uploads/file/autofile/cons/{symbol}cons.xls"
    )
    r = requests.get(url,proxies=proxies)
    temp_df = pd.read_excel(BytesIO(r.content))
    temp_df.columns = [
        "日期",
        "指数代码",
        "指数名称",
        "指数英文名称",
        "成分券代码",
        "成分券名称",
        "成分券英文名称",
        "交易所",
        "交易所英文名称",
    ]
    temp_df["日期"] = pd.to_datetime(
        temp_df["日期"], format="%Y%m%d", errors="coerce"
    ).dt.date
    temp_df["指数代码"] = temp_df["指数代码"].astype(str).str.zfill(6)
    temp_df["成分券代码"] = temp_df["成分券代码"].astype(str).str.zfill(6)
    return temp_df

def stock_zh_a_hist(
    symbol: str = "000001",
    period: str = "daily",
    start_date: str = "20250101", #股票开始时间
    end_date: str = "20500101",   ##股票结束时间
    adjust: str = "",
    timeout: float = None,
) -> pd.DataFrame:
    """
    东方财富网-行情首页-沪深京 A 股-每日行情
    https://quote.eastmoney.com/concept/sh603777.html?from=classic
    :param symbol: 股票代码
    :type symbol: str
    :param period: choice of {'daily', 'weekly', 'monthly'}
    :type period: str
    :param start_date: 开始日期
    :type start_date: str
    :param end_date: 结束日期
    :type end_date: str
    :param adjust: choice of {"qfq": "前复权", "hfq": "后复权", "": "不复权"}
    :type adjust: str
    :param timeout: choice of None or a positive float number
    :type timeout: float
    :return: 每日行情
    :rtype: pandas.DataFrame
    """
    market_code = 1 if symbol.startswith("6") else 0
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
    }

    # selected_headers = random.choice(default_headers)

    r = requests.get(url, params=params, timeout=timeout,proxies=proxies,headers=get_random_headers())
    data_json = r.json()
    if not (data_json["data"] and data_json["data"]["klines"]):
        return pd.DataFrame()
    temp_df = pd.DataFrame([item.split(",") for item in data_json["data"]["klines"]])
    temp_df["股票代码"] = symbol
    temp_df.columns = [
        "日期",
        "开盘",
        "收盘",
        "最高",
        "最低",
        "成交量",
        "成交额",
        "振幅",
        "涨跌幅",
        "涨跌额",
        "换手率",
        "股票代码",
    ]
    temp_df["日期"] = pd.to_datetime(temp_df["日期"], errors="coerce").dt.date
    temp_df["开盘"] = pd.to_numeric(temp_df["开盘"], errors="coerce")
    temp_df["收盘"] = pd.to_numeric(temp_df["收盘"], errors="coerce")
    temp_df["最高"] = pd.to_numeric(temp_df["最高"], errors="coerce")
    temp_df["最低"] = pd.to_numeric(temp_df["最低"], errors="coerce")
    temp_df["成交量"] = pd.to_numeric(temp_df["成交量"], errors="coerce")
    temp_df["成交额"] = pd.to_numeric(temp_df["成交额"], errors="coerce")
    temp_df["振幅"] = pd.to_numeric(temp_df["振幅"], errors="coerce")
    temp_df["涨跌幅"] = pd.to_numeric(temp_df["涨跌幅"], errors="coerce")
    temp_df["涨跌额"] = pd.to_numeric(temp_df["涨跌额"], errors="coerce")
    temp_df["换手率"] = pd.to_numeric(temp_df["换手率"], errors="coerce")
    temp_df = temp_df[
        [
            "日期",
            "股票代码",
            "开盘",
            "收盘",
            "最高",
            "最低",
            "成交量",
            "成交额",
            "振幅",
            "涨跌幅",
            "涨跌额",
            "换手率",
        ]
    ]
    return temp_df

def calculate_kdj(df, n=9, m1=3, m2=3):
    """
    计算KDJ指标
    n: 周期，通常为9
    m1: K值平滑因子，通常为3
    m2: D值平滑因子，通常为3
    """
    # 修正列名：'最高' -> high, '最低' -> low, '收盘' -> close
    low_list = df['最低'].rolling(window=n).min()
    high_list = df['最高'].rolling(window=n).max()
    
    # 计算RSV (Raw Stochastic Value)
    rsv = (df['收盘'] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50) # 初始值填充
    
    # 计算K, D, J
    # 标准算法：K = 2/3 * prev_K + 1/3 * RSV
    # ewm(com=m1-1) 等价于 alpha = 1/m1
    k = rsv.ewm(com=m1-1, adjust=False).mean()
    d = k.ewm(com=m2-1, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return k, d, j

def get_sse_stocks():
    """获取上证指数成分股列表"""
    print("正在获取上证指数成分股列表...")
    try:
        # 000001 是上证指数代码
        # 000002 是A股指数
        # 399001 是深证成指
        stock_info_df = index_stock_cons_csindex(symbol="000001")
        return stock_info_df
    except Exception as e:
        print(f"获取成分股失败: {e}")
        return None

def main():
    # 1. 获取成分股
    stocks_df = get_sse_stocks()
    if stocks_df is None or stocks_df.empty:
        print("未能获取到股票列表。")
        return

    stock_list = stocks_df['成分券代码'].tolist()

    # 创建一个字典，键是代码，值是名称
    # 注意：akshare返回的列名通常是 '成分券代码' 和 '成分券名称'
    name_map = dict(zip(stocks_df['成分券代码'], stocks_df['成分券名称']))
    total_count = len(stock_list)
    print(f"成功获取 {total_count} 只成分股。")

    # 为了演示，我们设置一个处理上限，或者让用户知道全量处理需要时间
    # 如果是生产环境，建议分批处理或使用多线程
    process_limit = 300 # 演示目的，取前50只。若需全量，可改为 total_count
    results = []

    print(f"开始计算前 {process_limit} 只股票的KDJ数据...")
    #todo process_limit 改为 total_count
    for i, code in enumerate(stock_list[:process_limit]):
        stock_name = name_map.get(code, "未知")  # 根据代码获取名称
        try:
            # 获取历史行情数据 (日线)
            # 获取最近30天的数据足够计算KDJ(9)
            df = stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")

            if df.empty or len(df) < 9:
                continue

            # 计算KDJ
            k, d, j = calculate_kdj(df)
            
            # 获取最新一天的值
            latest_k = k.iloc[-1]
            latest_d = d.iloc[-1]
            latest_j = j.iloc[-1]
            latest_date = df['日期'].iloc[-1]
            
            results.append({
                "股票代码": code,
                "股票名称": stock_name,
                "日期": latest_date,
                "K": round(latest_k, 2),
                "D": round(latest_d, 2),
                "J": round(latest_j, 2)
            })
            
            if (i + 1) % 10 == 0:
                print(f"已处理 {i + 1}/{process_limit}...")
            
            # 适当休眠防止被封
            time.sleep(random.randint(5, 10))
            
        except Exception as e:
            print(f"处理股票 {code} 时出错: {e}")

    # 汇总结果
    if results:
        result_df = pd.DataFrame(results)
        print("\n--- KDJ 计算结果 (前10行) ---")
        print(result_df.head(10))
        
        # 保存到文件
        output_file = "doc/sse_kdj_results-0305.csv"
        # 检查文件是否存在，决定是否写入表头
        write_header = not os.path.exists(output_file)
        # 以追加模式写入，不写入索引，指定编码
        result_df.to_csv(output_file, mode='a', index=False, encoding='utf_8_sig', header=write_header)
        print(f"\n结果已保存至 {output_file}")
    else:
        print("未获取到任何有效结果。")

if __name__ == "__main__":
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    main()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
