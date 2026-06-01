import os
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 从 .env 加载（如果存在）
_env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.isfile(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# A股指数参数（腾讯财经格式）
A_INDICES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "科创50": "sh000688",
}

INDEX_FIELDS = "f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18"

# A股全市场（沪深 + 创业板 + 科创板）
STOCK_MARKET_FS = "m:0+t:6,m:1+t:2,m:1+t:23,m:0+t:81"
STOCK_FIELDS = "f2,f3,f12,f14,f15,f16"

# 行业板块
SECTOR_FIELDS = "f2,f3,f4,f12,f14"
SECTOR_FS_BK = "m:90+t:2"
SECTOR_FS_GN = "m:90+t:3"

# 国际市场（Yahoo Finance Symbol）
YAHOO_SYMBOLS = {
    "道琼斯": "^DJI",
    "标普500": "^GSPC",
    "纳斯达克": "^IXIC",
    "日经225": "^N225",
    "韩国KOSPI": "^KS11",
}

# 时段配置
SLOTS = {
    "morning":  {"name": "盘前预览", "time": "09:30"},
    "midday":   {"name": "午间收盘", "time": "11:30"},
    "close":    {"name": "收盘总结", "time": "15:00"},
    "us_close": {"name": "美股收盘", "time": "05:00"},
}

WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]

# 微信公众平台配置（创建草稿用）
# 从环境变量读取，本地可 set WECHAT_APP_ID=xxx
WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "")
