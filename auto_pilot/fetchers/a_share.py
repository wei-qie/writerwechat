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
    获取市场概况 — 二分查找法，只需 ~10 次请求
    新浪 API 按涨跌幅降序排列，定位由正转负的分界点即可
    """
    import time

    url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    h = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}
    TOTAL_PAGES = 56  # A股 ~5300只，每页100

    def _page(pg):
        for _ in range(2):
            try:
                r = httpx.get(url, params={"page": pg, "num": 100, "sort": "changepercent",
                                           "asc": 0, "node": "hs_a"}, headers=h, timeout=10)
                if r.status_code == 200 and len(r.text) > 10:
                    return r.json()
            except Exception:
                time.sleep(0.3)
        return []

    # 取首页确定范围
    first = _page(1)
    if not first or len(first) < 2:
        return {"up": 0, "down": 0, "flat": 0, "limit_up": 0, "limit_down": 0, "total": 0}

    # 首页最后一只的涨幅
    try:
        tail_pct = float(first[-1].get("changepercent", 0))
    except (TypeError, ValueError):
        tail_pct = -999

    # 如果首页最后一只是绿的 → 所有涨幅榜在前100内
    if tail_pct <= 0:
        pos_pages = [1]
    else:
        # 二分查找：找到最后一只涨幅为正的页码
        lo, hi = 2, TOTAL_PAGES
        while lo <= hi:
            mid = (lo + hi) // 2
            data = _page(mid)
            if not data:
                hi = mid - 1
                continue
            try:
                pct = float(data[0].get("changepercent", 0))
            except (TypeError, ValueError):
                pct = -999
            if pct > 0:
                lo = mid + 1
            else:
                hi = mid - 1
            time.sleep(0.15)
        pos_pages = list(range(1, lo))  # 1 ~ lo-1 页都是正涨幅

    # 统计正涨幅页面中的个股
    up = limit_up = 0
    flat = down = limit_down = 0
    seen = 0

    for pg in pos_pages:
        data = _page(pg)
        if not data:
            continue
        for s in data:
            try:
                pct = float(s.get("changepercent", 0))
            except (TypeError, ValueError):
                continue
            seen += 1
            if pct > 0:
                up += 1
                if pct >= 9.5:
                    limit_up += 1
            elif pct == 0:
                flat += 1
            else:
                down += 1
                if pct <= -9.5:
                    limit_down += 1

    total = seen
    # 再取1-2页跌幅榜确认尾部数据
    for pg in range(lo, min(lo + 2, TOTAL_PAGES + 1)):
        data = _page(pg)
        if not data:
            continue
        for s in data:
            try:
                pct = float(s.get("changepercent", 0))
            except (TypeError, ValueError):
                continue
            total += 1
            if pct > 0:
                up += 1
            elif pct == 0:
                flat += 1
            else:
                down += 1
                if pct <= -9.5:
                    limit_down += 1
        time.sleep(0.15)

    return {
        "up": up,
        "down": down,
        "flat": flat,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "total": total,
    }
