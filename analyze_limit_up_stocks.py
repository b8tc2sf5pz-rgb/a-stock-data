#!/usr/bin/env python3
"""
昨日涨停股分析脚本
使用同花顺热点接口、龙虎榜数据和行业对比数据
"""

import requests
import pandas as pd
from collections import Counter
from datetime import datetime, timedelta


def ths_hot_reason(date: str = None) -> pd.DataFrame:
    """
    同花顺当日强势股归因
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    url = (
        f"http://zx.10jqka.com.cn/event/api/getharden/"
        f"date/{date}/orderby/date/orderway/desc/charset/GBK/"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    if data.get("errocode", 0) != 0:
        print(f"同花顺热点接口错误: {data.get('errormsg', '')}")
        return pd.DataFrame()

    rows = data.get("data") or []
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    rename_map = {
        "name": "名称", "code": "代码", "reason": "题材归因",
        "close": "收盘价", "zhangdie": "涨跌额", "zhangfu": "涨幅%",
        "huanshou": "换手率%", "chengjiaoe": "成交额",
        "chengjiaoliang": "成交量", "ddejingliang": "大单净量",
        "market": "市场",
    }
    df = df.rename(columns=rename_map)
    return df


def daily_dragon_tiger(trade_date: str = None, min_net_buy: float = None) -> dict:
    """
    全市场龙虎榜
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
        "columns": "ALL",
        "filter": f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
        "pageNumber": "1",
        "pageSize": "500",
        "sortTypes": "-1",
        "sortColumns": "BILLBOARD_NET_AMT",
        "source": "WEB",
        "client": "WEB",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/",
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    d = r.json()
    if not d.get("success") or not d.get("result") or not d["result"].get("data"):
        return {"date": trade_date, "total_records": 0, "stocks": [],
                "note": "无数据（非交易日或盘后未更新）"}
    data = d["result"]["data"]
    actual_date = data[0].get("TRADE_DATE", "")[:10] if data else trade_date
    stocks = []
    for row in data:
        net_buy = (row.get("BILLBOARD_NET_AMT") or 0) / 10000
        if min_net_buy is not None and net_buy < min_net_buy:
            continue
        stocks.append({
            "code": row.get("SECURITY_CODE", ""),
            "name": row.get("SECURITY_NAME_ABBR", ""),
            "reason": row.get("EXPLANATION", ""),
            "close": row.get("CLOSE_PRICE") or 0,
            "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
            "net_buy_wan": round(net_buy, 1),
            "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0) / 10000, 1),
            "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0) / 10000, 1),
            "turnover_pct": round(float(row.get("TURNOVERRATE") or 0), 2),
        })
    return {"date": actual_date, "total_records": len(stocks), "stocks": stocks}


def main():
    # 昨日日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"=== 分析 {yesterday} 涨停股 ===\n")

    # 1. 获取强势股数据
    print("1. 正在获取昨日强势股数据...")
    df_hot = ths_hot_reason(yesterday)
    if df_hot.empty:
        print(f"无法获取 {yesterday} 的数据，尝试获取最近可用的数据...")
        df_hot = ths_hot_reason()  # 尝试今日数据

    if not df_hot.empty:
        print(f"✓ 成功获取 {len(df_hot)} 只强势股\n")

        # 显示前20只涨停股
        print("--- 前20只强势股 ---")
        display_cols = ["代码", "名称", "涨幅%", "换手率%", "题材归因"]
        pd.set_option('display.max_colwidth', 40)
        print(df_hot[display_cols].head(20).to_string(index=False))
        print()

        # 分析题材分布
        print("--- 题材分布分析 ---")
        all_tags = []
        for r in df_hot["题材归因"].dropna():
            tags = [t.strip() for t in str(r).split("+") if t.strip()]
            all_tags.extend(tags)

        cnt = Counter(all_tags)
        print("热门题材 TOP 15:")
        for tag, n in cnt.most_common(15):
            print(f"  {tag}: {n} 只")
        print()
    else:
        print("✗ 无法获取强势股数据\n")

    # 2. 获取龙虎榜数据
    print("2. 正在获取昨日龙虎榜数据...")
    dt_data = daily_dragon_tiger(yesterday)
    if dt_data["total_records"] > 0:
        print(f"✓ 成功获取 {dt_data['total_records']} 条龙虎榜记录\n")

        print("--- 龙虎榜净买入 TOP 15 ---")
        for i, s in enumerate(dt_data["stocks"][:15], 1):
            print(f"{i:2d}. {s['code']} {s['name']}: 净买{s['net_buy_wan']:>8.1f}万 | {s['reason']}")
        print()
    else:
        print(f"✗ {dt_data.get('note', '无龙虎榜数据')}\n")


if __name__ == "__main__":
    main()
