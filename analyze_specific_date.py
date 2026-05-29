#!/usr/bin/env python3
"""
指定日期涨停股综合分析脚本
"""

import requests
import pandas as pd
from collections import Counter
from datetime import datetime


def ths_hot_reason(date: str) -> pd.DataFrame:
    """同花顺指定日期强势股归因"""
    url = f"http://zx.10jqka.com.cn/event/api/getharden/date/{date}/orderby/date/orderway/desc/charset/GBK/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0 Safari/537.36"}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    if data.get("errocode", 0) != 0:
        return pd.DataFrame()

    rows = data.get("data") or []
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    rename_map = {
        "name": "名称", "code": "代码", "reason": "题材归因",
        "close": "收盘价", "zhangfu": "涨幅%", "huanshou": "换手率%",
        "chengjiaoe": "成交额", "market": "市场",
    }
    df = df.rename(columns=rename_map)
    return df


def daily_dragon_tiger(trade_date: str) -> dict:
    """指定日期全市场龙虎榜"""
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
        return {"total_records": 0, "stocks": []}
    data = d["result"]["data"]
    stocks = []
    for row in data:
        net_buy = (row.get("BILLBOARD_NET_AMT") or 0) / 10000
        stocks.append({
            "code": row.get("SECURITY_CODE", ""),
            "name": row.get("SECURITY_NAME_ABBR", ""),
            "reason": row.get("EXPLANATION", ""),
            "net_buy_wan": round(net_buy, 1),
            "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
        })
    return {"total_records": len(stocks), "stocks": stocks}


def main():
    target_date = "2026-05-28"
    print(f"{'='*60}")
    print(f"{'5月28日（{target_date}）涨停股综合分析':^60}")
    print(f"{'='*60}\n")

    # 1. 强势股数据分析
    print("1. 正在获取强势股数据...")
    df_hot = ths_hot_reason(target_date)

    if not df_hot.empty:
        print(f"✓ 成功获取 {len(df_hot)} 只强势股\n")

        # 显示前30只涨停股
        print("--- 前30只强势股 ---")
        display_cols = ["代码", "名称", "涨幅%", "换手率%", "题材归因"]
        pd.set_option('display.max_colwidth', 50)
        print(df_hot[display_cols].head(30).to_string(index=False))
        print()

        # 涨幅分布
        print("--- 涨幅分布 ---")
        print(f"平均涨幅: {df_hot['涨幅%'].mean():.2f}%")
        print(f"最大涨幅: {df_hot['涨幅%'].max():.2f}%")
        print(f"最小涨幅: {df_hot['涨幅%'].min():.2f}%")
        print()

        # 题材分析
        print("--- 热门题材 TOP 20 ---")
        all_tags = []
        for r in df_hot["题材归因"].dropna():
            tags = [t.strip() for t in str(r).split("+") if t.strip()]
            all_tags.extend(tags)
        cnt = Counter(all_tags)
        for i, (tag, n) in enumerate(cnt.most_common(20), 1):
            print(f"{i:2d}. {tag}: {n} 只")
        print()

        # 高换手率股票
        print("--- 高换手率 TOP 10 ---")
        high_turnover = df_hot.sort_values('换手率%', ascending=False).head(10)
        for _, row in high_turnover.iterrows():
            print(f"{row['代码']} {row['名称']}: 换手率 {row['换手率%']:.2f}%")
        print()
    else:
        print("✗ 无法获取强势股数据\n")

    # 2. 龙虎榜数据
    print("2. 正在获取龙虎榜数据...")
    dt_data = daily_dragon_tiger(target_date)
    if dt_data["total_records"] > 0:
        print(f"✓ 成功获取 {dt_data['total_records']} 条龙虎榜记录\n")

        print("--- 龙虎榜净买入 TOP 15 ---")
        for i, s in enumerate(dt_data["stocks"][:15], 1):
            print(f"{i:2d}. {s['code']} {s['name']}: 净买{s['net_buy_wan']:>8.1f}万 | {s['reason']}")
        print()

        # 计算总净买入
        total_net = sum(s['net_buy_wan'] for s in dt_data["stocks"])
        print(f"龙虎榜总净买入: {total_net:.1f} 万元\n")

        # 龙虎榜和强势股的交集
        if not df_hot.empty:
            hot_codes = set(df_hot['代码'])
            dt_codes = set(s['code'] for s in dt_data["stocks"])
            overlap = hot_codes & dt_codes
            print(f"--- 同时出现在强势股和龙虎榜的股票 ({len(overlap)} 只) ---")
            overlap_stocks = [s for s in dt_data["stocks"] if s['code'] in overlap]
            overlap_stocks.sort(key=lambda x: -x['net_buy_wan'])
            for s in overlap_stocks:
                reason = df_hot[df_hot['代码'] == s['code']]['题材归因'].iloc[0]
                print(f"{s['code']} {s['name']}: 净买{s['net_buy_wan']:>8.1f}万 | {reason}")
    else:
        print("✗ 无龙虎榜数据\n")

    print(f"{'='*60}")
    print("分析完成")


if __name__ == "__main__":
    main()
