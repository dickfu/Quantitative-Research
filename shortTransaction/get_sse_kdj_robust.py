import akshare as ak
import pandas as pd
import numpy as np
import time
import random
import sys

def calculate_kdj(df, n=9, m1=3, m2=3):
    """
    计算KDJ指标
    n: 周期，通常为9
    m1: K值平滑因子，通常为3
    m2: D值平滑因子，通常为3
    """
    if len(df) < n:
        return pd.Series(), pd.Series(), pd.Series()
        
    # 修正列名：'最高' -> high, '最低' -> low, '收盘' -> close
    low_list = df['最低'].rolling(window=n).min()
    high_list = df['最高'].rolling(window=n).max()
    
    # 计算RSV (Raw Stochastic Value)
    rsv = (df['收盘'] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50) # 初始值填充
    
    # 计算K, D, J
    # 标准算法：K = 2/3 * prev_K + 1/3 * RSV
    k = rsv.ewm(com=m1-1, adjust=False).mean()
    d = k.ewm(com=m2-1, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return k, d, j

def get_stock_data_with_retry(code, max_retries=3):
    """带重试机制的股票数据获取函数"""
    for attempt in range(max_retries):
        try:
            # 获取历史行情数据 (日线)
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            return df
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2 + random.random()
                print(f"获取股票 {code} 失败 (第 {attempt+1} 次尝试): {e}。等待 {wait_time:.2f} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"获取股票 {code} 最终失败: {e}")
                return pd.DataFrame()

def get_sse_stocks():
    """获取上证指数成分股列表"""
    print("正在获取上证指数成分股列表...")
    try:
        # 000001 是上证指数代码
        stock_info_df = ak.index_stock_cons_csindex(symbol="000001")
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
    # 创建代码到名称的映射字典
    name_map = dict(zip(stocks_df['成分券代码'], stocks_df['成分券名称']))
    
    total_count = len(stock_list)
    print(f"成功获取 {total_count} 只成分股。")

    # 设置处理上限（您可以根据需要修改，全量处理请设为 total_count）
    process_limit = 50 
    results = []

    print(f"开始计算前 {process_limit} 只股票的KDJ数据...")
    
    start_time = time.time()
    
    for i, code in enumerate(stock_list[:process_limit]):
        # 获取数据（带重试）
        df = get_stock_data_with_retry(code)
        
        if df.empty or len(df) < 9:
            continue
        
        try:
            stock_name = name_map.get(code, "未知")
            
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
                elapsed = time.time() - start_time
                print(f"已处理 {i + 1}/{process_limit}，耗时: {elapsed:.1f}s...")
            
            # 随机休眠 0.3 到 0.8 秒，模拟人类行为，防止被封
            time.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            print(f"处理股票 {code} ({name_map.get(code, '')}) 时出错: {e}")

    # 汇总结果
    if results:
        result_df = pd.DataFrame(results)
        print("\n--- KDJ 计算结果 (前10行) ---")
        print(result_df.head(10))
        
        # 保存到文件
        output_file = "sse_kdj_results_optimized.csv"
        result_df.to_csv(output_file, index=False, encoding='utf_8_sig')
        print(f"\n结果已保存至 {output_file}")
    else:
        print("未获取到任何有效结果。")

if __name__ == "__main__":
    print(f"程序启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    main()
    print(f"程序结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
