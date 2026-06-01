"""微信公众平台 API 封装（access_token、草稿、素材）"""

import json
import os
import time
import httpx
from html import escape

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
DRAFT_CREATE_URL = "https://api.weixin.qq.com/cgi-bin/draft/create"
MATERIAL_UPLOAD_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"


class WeChatAPI:
    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id or os.environ.get("WECHAT_APP_ID", "")
        self.app_secret = app_secret or os.environ.get("WECHAT_APP_SECRET", "")
        if not self.app_id or not self.app_secret:
            raise ValueError(
                "请配置 WECHAT_APP_ID 和 WECHAT_APP_SECRET\n"
                "可在公众号后台 → 开发 → 基本配置 中获取\n"
                "设置方式：set WECHAT_APP_ID=xxx （或写入 .env）"
            )
        self._token = ""
        self._token_expires = 0

    # ── token ──────────────────────────────────────────────

    def get_access_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        r = httpx.get(TOKEN_URL, params={
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }, timeout=10)
        data = r.json()
        if "access_token" not in data:
            raise RuntimeError(f"获取 access_token 失败: {data.get('errmsg', r.text)}")
        self._token = data["access_token"]
        self._token_expires = time.time() + data["expires_in"]
        return self._token

    # ── 素材（封面图） ──────────────────────────────────────

    def upload_image(self, image_path: str) -> str:
        """上传永久素材图片，返回 media_id（用于封面）"""
        token = self.get_access_token()
        with open(image_path, "rb") as f:
            files = {"media": (os.path.basename(image_path), f, "image/png")}
            r = httpx.post(
                MATERIAL_UPLOAD_URL,
                params={"access_token": token, "type": "image"},
                files=files,
                timeout=30,
            )
        data = r.json()
        if "media_id" not in data:
            raise RuntimeError(f"上传图片失败: {data.get('errmsg', r.text())}")
        return data["media_id"]

    # ── 草稿 ──────────────────────────────────────────────

    def create_draft(self, title: str, html_content: str,
                     digest: str = "", author: str = "基市红绿灯",
                     thumb_media_id: str = "") -> dict:
        """创建图文草稿，返回结果"""
        token = self.get_access_token()
        body = {
            "articles": [{
                "title": title,
                "author": author,
                "digest": digest,
                "content": html_content,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }]
        }
        # 只传入非空的可选字段
        if thumb_media_id:
            body["articles"][0]["thumb_media_id"] = thumb_media_id
        r = httpx.post(
            DRAFT_CREATE_URL,
            params={"access_token": token},
            json=body,
            timeout=15,
        )
        data = r.json()
        if "media_id" not in data:
            raise RuntimeError(f"创建草稿失败: {data.get('errmsg', r.text)}")
        return data
