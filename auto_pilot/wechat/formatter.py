"""文章内容转微信图文 HTML"""

import re
from html import escape


class WeChatFormatter:
    """将 Markdown 格式转为微信公众号文章兼容的 HTML"""

    def format(self, md_text: str) -> str:
        lines = md_text.split("\n")
        parts = ["<section>"]

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                parts.append("<p style='margin:0;'>&nbsp;</p>")
                i += 1
                continue

            if line.startswith("# ") and not line.startswith("## "):
                text = self._inline(line[2:])
                parts.append(
                    f"<h1 style='font-size:18px;font-weight:bold;margin:16px 0 8px;'>{text}</h1>"
                )

            elif line.startswith("## "):
                text = self._inline(line[3:])
                parts.append(
                    f"<h2 style='font-size:16px;font-weight:bold;margin:14px 0 6px;'>{text}</h2>"
                )

            elif line.startswith("> "):
                text = self._inline(line[2:])
                parts.append(
                    f"<blockquote style='border-left:3px solid #ddd;padding:8px 12px;margin:8px 0;color:#888;'>"
                    f"<p style='margin:0;'>{text}</p></blockquote>"
                )

            elif "|" in line and line.startswith("|"):
                rows = self._collect_table(lines, i)
                if rows:
                    parts.append(self._table_html(rows))
                    i += len(rows) - 1

            elif line.startswith("- "):
                text = self._inline(line[2:])
                parts.append(f"<p style='margin:4px 0;padding-left:1em;line-height:1.75;'>• {text}</p>")

            elif line == "---":
                parts.append("<hr style='border:none;border-top:1px solid #eee;margin:16px 0;'>")

            elif line.startswith("**") and line.endswith("**") and len(line) > 4:
                text = self._inline(line)
                parts.append(f"<p style='font-weight:bold;margin:8px 0;line-height:1.75;'>{text}</p>")

            else:
                text = self._inline(line)
                parts.append(f"<p style='margin:6px 0;line-height:1.75;'>{text}</p>")

            i += 1

        parts.append("</section>")
        return "\n".join(parts)

    # ── 内部工具 ───────────────────────────────────────────

    @staticmethod
    def _inline(text: str) -> str:
        """**粗体** → <strong>，同时 HTML 转义"""
        text = escape(text)
        return re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)

    @staticmethod
    def _collect_table(lines, start):
        rows = []
        for j in range(start, len(lines)):
            line = lines[j].strip()
            if not line or not line.startswith("|"):
                break
            if re.search(r"^[\|:\-\s]+$", line):
                continue  # 跳过对齐行
            cells = [c.strip() for c in line.split("|")[1:-1]]
            rows.append(cells)
        return rows

    @staticmethod
    def _table_html(rows) -> str:
        if not rows:
            return ""
        parts = ['<table style="border-collapse:collapse;width:100%;margin:8px 0;">']
        for r_idx, row in enumerate(rows):
            parts.append("<tr>")
            tag = "th" if r_idx == 0 else "td"
            for cell in row:
                text = escape(cell)
                style = "border:1px solid #ddd;padding:8px 12px;text-align:center;font-size:14px;"
                parts.append(f"<{tag} style='{style}'>{text}</{tag}>")
            parts.append("</tr>")
        parts.append("</table>")
        return "\n".join(parts)
