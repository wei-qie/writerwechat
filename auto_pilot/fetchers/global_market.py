"""全球市场数据：美股、日股、韩股（新浪财经为主，Yahoo Finance 备用）"""

import re
import httpx
from ..config import YAHOO_SYMBOLS

HEADERS = {"User-Agent": "Mozilla/5.0"}
SINA_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}
TIMEOUT = 15

# 新浪财经的外盘代码映射
SINA_GLOBAL = {
    "道琼斯": "gb_^dji",
    "标普500": "gb_^gspc",
    "纳斯达克": "gb_^ixic",
    "日经225": "gb_^n225",
    "韩国KOSPI": "gb_^ks11",
}


def _fetch_sina():
    """从新浪财经获取全球指数"""
    codes = ",".join(SINA_GLOBAL.values())
    url = f"https://hq.sinajs.cn/list={codes}"
    try:
        r = httpx.get(url, headers=SINA_HEADERS, timeout=TIMEOUT)
        r.encoding = "gbk"
    except Exception:
        return {}

    results = {}
    for line in r.text.strip().split("\n"):
        m = re.search(r'"(.*?)"', line)
        if not m:
            continue
        fields = m.group(1).split(",")
        if len(fields) < 8 or fields[0] == "":
            continue
        # 新浪外盘格式: 名称,今开,昨收,当前,最高,最低,...
        name = fields[0]
        price = _f(fields[3])
        prev_close = _f(fields[2])
        open_p = _f(fields[1])
        high = _f(fields[4])
        low = _f(fields[5])
        change_pct = round((price - prev_close) / prev_close * 100, 2) if price and prev_close else None

        # 查找对应的中文名
        for cn_name, sina_code in SINA_GLOBAL.items():
            if sina_code in line:
                results[cn_name] = {
                    "name": cn_name,
                    "price": price,
                    "prev_close": prev_close,
                    "change_pct": change_pct,
                    "open": open_p,
                    "high": high,
                    "low": low,
                }
                break
    return results


def _fetch_yahoo(symbol):
    """Yahoo Finance 备用"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        r = httpx.get(url, params={"range": "1d", "interval": "1d"}, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        data = r.json()
        result = (data.get("chart") or {}).get("result")
        if not result:
            return None
        meta = result[0].get("meta", {})
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        price = meta.get("regularMarketPrice")
        change_pct = round((price - prev_close) / prev_close * 100, 2) if price and prev_close else None
        return {"price": price, "prev_close": prev_close, "change_pct": change_pct}
    except Exception:
        return None


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _collect(names, source_dict):
    """从数据源收集指定名字的指数"""
    return [source_dict[n] for n in names if n in source_dict and source_dict[n].get("price")]


def get_us_indices():
    """获取美股三大指数（新浪优先，Yahoo 备用）"""
    sina = _fetch_sina()
    us_names = ["道琼斯", "标普500", "纳斯达克"]

    # 如果新浪有数据
    result = _collect(us_names, sina)
    if result:
        return result

    # 备用：Yahoo Finance
    results = []
    for name in us_names:
        sym = YAHOO_SYMBOLS.get(name)
        if not sym:
            continue
        data = _fetch_yahoo(sym)
        if data:
            results.append({"name": name, **data})
    return results


def get_asia_indices():
    """获取亚太指数"""
    sina = _fetch_sina()
    asia_names = ["日经225", "韩国KOSPI"]
    result = _collect(asia_names, sina)
    if result:
        return result

    # Yahoo 备用
    results = []
    for name in asia_names:
        sym = YAHOO_SYMBOLS.get(name)
        if not sym:
            continue
        data = _fetch_yahoo(sym)
        if data:
            results.append({"name": name, **data})
    return results
