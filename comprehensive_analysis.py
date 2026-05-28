#!/usr/bin/env python3
"""
昨日涨停股综合分析脚本
结合强势股数据、龙虎榜数据和行业对比数据
"""

import requests
import pandas as pd
from collections import Counter
from datetime import datetime, timedelta


def ths_hot_reason(date: str = None) -> pd.DataFrame:
    """同花顺当日强势股归因"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

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


def daily_dragon_tiger(trade_date: str = None) -> dict:
    """全市场龙虎榜"""
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
        "columns": "ALL",
        "filter": f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
        "pageNumber": "1", "pageSize": "500",
        "sortTypes": "-1", "sortColumns": "BILLBOARD_NET_AMT",
        "source": "WEB", "client": "WEB",
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
            "net_buy_wan": round(net_buy, 1),
        })
    return {"total_records": len(stocks), "stocks": stocks}


def main():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"{'='*60}")
    print(f"{'昨日（{yesterday}）涨停股综合分析':^60}")
    print(f"{'='*60}\n")

    # 1. 强势股数据分析
    df_hot = ths_hot_reason(yesterday)
    if df_hot.empty:
        df_hot = ths_hot_reason()

    if not df_hot.empty:
        print(f"📊 强势股概况: {len(df_hot)} 只股票\n")

        # 涨幅分布
        print("--- 涨幅分布 ---")
        print(f"平均涨幅: {df_hot['涨幅%'].mean():.2f}%")
        print(f"最大涨幅: {df_hot['涨幅%'].max():.2f}%")
        print(f"最小涨幅: {df_hot['涨幅%'].min():.2f}%")
        print()

        # 市场分布
        print("--- 市场分布 ---")
        market_dist = df_hot['市场'].value_counts()
        for market, count in market_dist.items():
            print(f"{market}: {count} 只")
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

    # 2. 龙虎榜数据综合
    dt_data = daily_dragon_tiger(yesterday)
    if dt_data["total_records"] > 0:
        print("💰 龙虎榜资金流向\n")

        # 计算总净买入
        total_net = sum(s['net_buy_wan'] for s in dt_data["stocks"])
        print(f"总净买入: {total_net:.1f} 万元\n")

        # 龙虎榜和强势股的交集
        if not df_hot.empty:
            hot_codes = set(df_hot['代码'])
            dt_codes = set(s['code'] for s in dt_data["stocks"])
            overlap = hot_codes & dt_codes
            print(f"--- 同时出现在强势股和龙虎榜的股票 ({len(overlap)} 只) ---")
            overlap_stocks = [s for s in dt_data["stocks"] if s['code'] in overlap]
            overlap_stocks.sort(key=lambda x: -x['net_buy_wan'])
            for s in overlap_stocks:
                # 找到对应的题材
                reason = df_hot[df_hot['代码'] == s['code']]['题材归因'].iloc[0]
                print(f"{s['code']} {s['name']}: 净买{s['net_buy_wan']:>8.1f}万 | {reason}")

    print(f"\n{'='*60}")
    print("分析完成")


if __name__ == "__main__":
    main()
