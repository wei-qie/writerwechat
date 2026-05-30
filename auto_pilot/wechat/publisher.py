"""自动生成文章 → 创建微信草稿 一站式入口"""

import os
import sys
from datetime import datetime
from ..generator import ArticleGenerator
from .api import WeChatAPI
from .formatter import WeChatFormatter


class WeChatPublisher:
    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.api = WeChatAPI(app_id, app_secret)
        self.formatter = WeChatFormatter()

    def publish_draft(self, slot: str, data: dict) -> dict:
        """生成文章 → 创建微信草稿，返回 API 结果"""
        gen = ArticleGenerator()
        md = gen.generate(slot, data)

        # 从 markdown 提取标题、摘要
        title = "芯元财经速递"
        digest = ""
        for line in md.split("\n"):
            s = line.strip()
            if s.startswith("# ") and not s.startswith("## "):
                title = s[2:]
            elif s.startswith("> ") and not digest:
                digest = s[2:]

        html = self.formatter.format(md)
        return self.api.create_draft(title, html, digest=digest)

    @staticmethod
    def publish_from_content(title: str, html_content: str,
                             digest: str = "", thumb_media_id: str = "") -> dict:
        """如果已准备好内容，直接调用此方法"""
        api = WeChatAPI()
        return api.create_draft(title, html_content, digest=digest,
                                thumb_media_id=thumb_media_id)


def main():
    """独立命令行入口：python -m auto_pilot.wechat.publisher <slot>"""
    if len(sys.argv) < 2:
        print("用法: python -m auto_pilot.wechat.publisher <slot>")
        print("slot: morning / midday / close / us_close")
        sys.exit(1)

    slot = sys.argv[1].lower()
    if slot not in ("morning", "midday", "close", "us_close"):
        print(f"未知时段: {slot}")
        sys.exit(1)

    try:
        from ..main import fetch_all
    except ImportError:
        from auto_pilot.main import fetch_all

    t0 = datetime.now()
    print(f"[{t0.strftime('%H:%M:%S')}] 获取数据 [{slot}] ...")
    data = fetch_all(slot)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 生成并发布草稿 ...")
    pub = WeChatPublisher()
    result = pub.publish_draft(slot, data)
    elapsed = (datetime.now() - t0).total_seconds()

    print(f"[OK] 草稿已创建！media_id: {result.get('media_id')}")
    print(f"[OK] 耗时: {elapsed:.1f}s")
    print(f"[提示] 请登录微信公众号后台 → 草稿箱 查看并手动发布")


if __name__ == "__main__":
    main()
