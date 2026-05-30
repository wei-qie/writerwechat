"""A股数据抓取：指数 + 板块ETF + 市场概况"""

import re
import httpx
from ..config import WEEKDAY_CN, A_INDICES

TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com/"}

# 代表板块的 ETF 列表（用于板块涨跌概览）
SECTOR_ETFS = [
    ("白酒", "512690"), ("医药", "512010"), ("消费", "510150"),
    ("证券", "512880"), ("银行", "512800"), ("半导体", "512480"),
    ("新能源", "516160"), ("军工", "512660"), ("煤炭", "515220"),
    ("光伏", "515790"), ("地产", "512200"), ("有色", "512400"),
    ("通信", "515880"), ("电力", "561700"), ("人工智能", "517050"),
]


def _parse_qtgfx(text):
    """解析腾讯 qt.gtimg.cn 返回的数据（~分隔格式）"""
    results = []
    for line in text.strip().split("\n"):
        if "=" not in line:
            continue
        parts = line.split("~")
        name = parts[1] if len(parts) > 1 else ""
        code = parts[2] if len(parts) > 2 else (line.split("=")[0].split("_")[-1] if "=" in line else "")
        price = _float(parts[3]) if len(parts) > 3 else None
        prev_close = _float(parts[4]) if len(parts) > 4 else None
        open_p = _float(parts[5]) if len(parts) > 5 else None
        # 时间戳后面的两个字段是 涨跌额, 涨跌幅%
        change_amt = change_pct = None
        for i, p in enumerate(parts):
            if re.match(r"^\d{14}$", p) and i + 2 < len(parts):
                change_amt = _float(parts[i + 1])
                change_pct = _float(parts[i + 2])
                break
        # 如果没有找到时间戳，从价格计算
        if change_pct is None and price and prev_close and prev_close != 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)
        if change_amt is None and price and prev_close:
            change_amt = round(price - prev_close, 2)

        results.append({
            "name": name,
            "code": code,
            "price": price,
            "change_pct": change_pct,
            "change_amt": change_amt,
            "open": open_p,
            "pre_close": prev_close,
        })
    return results


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def get_indices():
    """获取A股主要指数行情（腾讯API）"""
    codes = ",".join(A_INDICES.values())
    try:
        r = httpx.get(f"https://qt.gtimg.cn/q={codes}", headers=HEADERS, timeout=TIMEOUT)
        r.encoding = "gbk"
        return _parse_qtgfx(r.text)
    except Exception as e:
        print(f"[WARN] 获取指数失败: {e}")
        return []


def get_sector_etf_data():
    """获取板块ETF涨跌数据（用于板块概览）"""
    # 腾讯API需要sh/sz前缀
    query_codes = ",".join("sh" + code for _, code in SECTOR_ETFS)
    try:
        r = httpx.get(f"https://qt.gtimg.cn/q={query_codes}", headers=HEADERS, timeout=TIMEOUT)
        r.encoding = "gbk"
        data = _parse_qtgfx(r.text)
        # 把ETF名映射简化为板块名
        for item in data:
            for sname, scode in SECTOR_ETFS:
                if scode == item.get("code"):
                    item["name"] = sname
                    break
        return data
    except Exception as e:
        print(f"[WARN] 获取板块ETF失败: {e}")
        return []


def get_sector_rank(top_n=10):
    """获取板块涨跌排行，返回 (涨幅榜, 跌幅榜)"""
    data = get_sector_etf_data()
    valid = [d for d in data if d.get("change_pct") is not None]
    gainers = sorted([d for d in valid if d["change_pct"] > 0], key=lambda x: x["change_pct"], reverse=True)[:top_n]
    losers = sorted([d for d in valid if d["change_pct"] < 0], key=lambda x: x["change_pct"])[:top_n]
    return gainers, losers


def format_index_change(indices):
    """生成开盘概况文本"""
    descs = []
    for idx in indices[:3]:
        o = idx.get("open")
        pc = idx.get("pre_close")
        if o and pc and pc != 0:
            diff = round((o - pc) / pc * 100, 2)
            if diff > 0.1:
                descs.append(f"{idx['name']}高开{diff:+.2f}%")
            elif diff < -0.1:
                descs.append(f"{idx['name']}低开{diff:+.2f}%")
            else:
                descs.append(f"{idx['name']}近乎平开")
    return "，".join(descs) if descs else "数据获取中"


def get_market_stats():
    """
    获取市场概况（新浪API 并发分页）
    """
    up = down = limit_up = limit_down = total_fetched = 0
    url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    h = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}

    # 先获取第一页，确定总条数
    for attempt in range(2):  # 重试一次
        try:
            r = httpx.get(url, params={"page": 1, "num": 100, "sort": "changepercent", "asc": 0, "node": "hs_a"}, headers=h, timeout=10)
            first = r.json()
            if first and len(first) > 1:
                break
        except Exception as e:
            if attempt == 1:
                print(f"[WARN] 市场统计首页失败: {e}")
                return {"up": 0, "down": 0, "flat": 0, "limit_up": 0, "limit_down": 0, "total": 0}
            first = []

    if not first or len(first) < 2:
        return {"up": 0, "down": 0, "flat": 0, "limit_up": 0, "limit_down": 0, "total": 0}

    # 用线程池并发请求50页（每页100只，共5000只，覆盖全部A股）
    from concurrent.futures import ThreadPoolExecutor, as_completed
    all_stocks = list(first)

    def fetch_page(pg):
        for retry in range(2):
            try:
                r2 = httpx.get(url, params={"page": pg, "num": 100, "sort": "changepercent", "asc": 0, "node": "hs_a"}, headers=h, timeout=10)
                if r2.status_code == 200 and len(r2.text) > 10:
                    return r2.json()
            except Exception:
                if retry == 0:
                    continue
        return []

    total_stock_count = 0
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(fetch_page, p): p for p in range(2, 56)}
        for fut in as_completed(futs):
            stocks = fut.result()
            if stocks:
                all_stocks.extend(stocks)
                total_stock_count += len(stocks)

    for s in all_stocks:
        try:
            pct = float(s.get("changepercent", 0))
        except (ValueError, TypeError):
            continue
        if pct > 0:
            up += 1
            if pct >= 9.5:
                limit_up += 1
        elif pct < 0:
            down += 1
            if pct <= -9.5:
                limit_down += 1

    total_fetched = len(all_stocks)
    return {
        "up": up,
        "down": down,
        "flat": max(0, total_fetched - up - down),
        "limit_up": limit_up,
        "limit_down": limit_down,
        "total": total_fetched,
    }
