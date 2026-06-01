"""
基市红绿灯 - 自动生产系统

用法: python -m auto_pilot.main <slot>
slot: morning / midday / close / us_close
"""

import sys
from datetime import datetime
from .fetchers.a_share import get_indices, get_market_stats, get_sector_rank
from .fetchers.global_market import get_us_indices, get_asia_indices
from .fetchers.fund import get_fund_rank
from .generator import ArticleGenerator


def is_weekday():
    """周末不生成"""
    return datetime.now().weekday() < 5


def fetch_all(slot: str) -> dict:
    data = {}
    data["indices"] = get_indices()
    data["sectors_gain"], data["sectors_lose"] = get_sector_rank()

    if slot in ("morning", "midday", "close"):
        data["stats"] = get_market_stats()

    if slot == "morning":
        data["us_indices"] = get_us_indices()
        data["asia_indices"] = get_asia_indices()
    elif slot == "midday":
        gain, lose = get_fund_rank(10)
        data["fund_gain"] = [f for f in gain if f.get("daily_change", 0) > 0]
        data["fund_lose"] = [f for f in lose if f.get("daily_change", 0) < 0]
    elif slot == "close":
        gain, lose = get_fund_rank(10)
        data["fund_gain"] = [f for f in gain if f.get("daily_change", 0) > 0]
        data["fund_lose"] = [f for f in lose if f.get("daily_change", 0) < 0]
    elif slot == "us_close":
        data["us_indices"] = get_us_indices()

    return data


def main():
    if len(sys.argv) < 2:
        print("用法: python -m auto_pilot.main <slot> [--wechat]")
        print("slot: morning / midday / close / us_close")
        sys.exit(1)

    slot = sys.argv[1].lower()
    valid = {"morning", "midday", "close", "us_close"}
    if slot not in valid:
        print(f"未知时段: {slot}")
        sys.exit(1)

    publish_wechat = "--wechat" in sys.argv

    if not is_weekday():
        print(f"[SKIP] 今天是周末，仅交易日生成。")
        sys.exit(0)

    t0 = datetime.now()
    print(f"[{t0.strftime('%H:%M:%S')}] 开始生成 [{slot}] ...")

    try:
        data = fetch_all(slot)
        gen = ArticleGenerator()
        content = gen.generate(slot, data)
        docx_path = gen.save(slot, content)
        elapsed = (datetime.now() - t0).total_seconds()
        print(f"[OK] 已生成: {docx_path}")
        print(f"[OK] 耗时: {elapsed:.1f}s | 字数: {len(content)}")

        if publish_wechat:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 发布到微信草稿箱 ...")
            from .wechat.publisher import WeChatPublisher
            pub = WeChatPublisher()
            result = pub.publish_draft(slot, data)
            print(f"[OK] 微信草稿已创建！media_id: {result.get('media_id')}")
            wc_elapsed = (datetime.now() - t0).total_seconds()
            print(f"[OK] 总耗时: {wc_elapsed:.1f}s")

    except Exception as e:
        print(f"[ERROR] 生成失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
