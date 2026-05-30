"""基金数据：日涨跌排行榜（天天基金）"""

import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://fund.eastmoney.com/"}
TIMEOUT = 15


def get_fund_rank(top_n=10):
    """
    获取开放式基金日涨幅榜/跌幅榜
    返回 (gainers, losers)
    """
    def _fetch(sort_dir):
        url = "https://fund.eastmoney.com/data/rankhandler.aspx"
        params = {
            "op": "ph", "dt": "kf", "ft": "all",
            "sc": "zzf", "st": sort_dir,
            "pi": 1, "pn": top_n, "dx": 1,
        }
        try:
            r = httpx.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            text = r.text
        except Exception as e:
            print(f"[WARN] 获取基金排行失败: {e}")
            return []

        # 天天基金返回: var rankData = {datas:["xxx,xxx,...", "xxx,..."], ...};
        m = re.search(r'datas:\s*\[(.*?)\]', text, re.DOTALL)
        if not m:
            # 尝试另一种格式
            m = re.search(r'data:\s*\[(.*?)\]', text, re.DOTALL)
        if not m:
            return []

        data_str = m.group(1).strip()
        # 逐个提取引号内的记录
        records = re.findall(r'"([^"]*?)"', data_str)
        results = []
        for rec in records:
            parts = rec.split(",")
            if len(parts) >= 8:
                code = parts[0]
                name = parts[1]
                daily_change = parts[6]
                if daily_change and daily_change != "":
                    try:
                        results.append({
                            "code": code,
                            "name": name,
                            "daily_change": float(daily_change),
                        })
                    except ValueError:
                        pass
        return results

    try:
        gainers = _fetch("desc")
        losers = _fetch("asc")
        return gainers, losers
    except Exception as e:
        print(f"[WARN] 获取基金排行失败: {e}")
        return [], []
