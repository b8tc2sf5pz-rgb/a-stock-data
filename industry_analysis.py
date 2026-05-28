#!/usr/bin/env python3
"""
行业对比数据分析
"""

import akshare as ak
import pandas as pd


def get_industry_comparison():
    """获取行业对比数据"""
    try:
        df = ak.stock_board_industry_summary_ths()
        return df
    except Exception as e:
        print(f"获取行业数据失败: {e}")
        return pd.DataFrame()


def main():
    print("="*60)
    print("行业对比数据分析")
    print("="*60)

    df = get_industry_comparison()
    if df.empty:
        print("无法获取行业数据")
        return

    print(f"\n共获取 {len(df)} 个行业数据\n")

    # 涨跌幅前10的行业
    print("--- 涨幅前10的行业 ---")
    top_gainers = df.sort_values('涨跌幅', ascending=False).head(10)
    for i, (_, row) in enumerate(top_gainers.iterrows(), 1):
        print(f"{i:2d}. {row['板块']}: 涨{row['涨跌幅']:.2f}% | 成交{row.get('总成交额', 'N/A')}亿 | 领涨{row.get('领涨股', 'N/A')}")

    print("\n--- 跌幅前10的行业 ---")
    top_losers = df.sort_values('涨跌幅', ascending=True).head(10)
    for i, (_, row) in enumerate(top_losers.iterrows(), 1):
        print(f"{i:2d}. {row['板块']}: 跌{abs(row['涨跌幅']):.2f}%")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
