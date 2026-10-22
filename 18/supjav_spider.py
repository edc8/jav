# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════
# 判型记录(卡01 第四节;跨会话可读 —— 接手先读这段,别重新判一遍)
#   RE_TARGET   : https://supjav.com (SupJav,WordPress 站,主题 supjav2)
#   RE_PATH     : 纯 HTML 正则:列表卡片(div.post)+ 详情页 .btn-server 的
#                 data-link 令牌 → lk1.supremejav.com/supjav.php?c={令牌反转}
#                 → 302 到真实 embed(streamtape 可直解 get_video,其余通用
#                 抽 m3u8/mp4,兜底交壳嗅探 parse=1)
#   RE_OBSTACLE : Cloudflare 硬封(Attention Required):机房出口全 403,
#                 家庭/浏览器出口可过(MissAV 型);图片 CDN img.supjav.com 不封
#   RE_EVIDENCE : 2026-10-22 浏览器实测导航/列表/详情/三索引页结构;
#                 Wayback 2025-09 存档详情页源码核对卡片与按钮标记;
#                 base.js 的 JumpChain 公式 + supjav.php ?l=/?c= 两跳实测 302;
#                 ST 线 streamtape robotlink 直解实测通过
#   RE_CREATED  : 2026-10-22
# ══════════════════════════════════════════════════════════════
# TVBox 源 · SupJav
# 自检:python3 shellsim.py 本文件 --run --strict
# 注意:主站对机房 IP 是 CF 硬封,本机 shellsim 的 L2/L3 会 403(与 MissAV 同),
# 解析逻辑已用存档真实源码 + 活链分段实证;请在家庭网络下用 App 终验。

import gzip
import json
import re
import sys
import time
import urllib.parse
import urllib.request

# 四壳协议(铁律):类名必须叫 Spider,继承壳提供的 BaseSpider(base.spider);
# 无壳环境(本地自检)才走回退定义。
try:
    sys.path.append("..")
    from base.spider import BaseSpider
except Exception:
    class BaseSpider:
        pass


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
TIMEOUT = 15
RETRY = 3

# 导航 1:1(2026-10-22 实测):内容分类 8 + 索引 3;站外广告位(JAVHD/Live
# Cams/AI Sex/PornDude)与语言开关不入源,Latest URL 只是网址发布页。
CATS = [
    {"type_id": "home",      "type_name": "首页"},
    {"type_id": "popular",   "type_name": "热门"},
    {"type_id": "censored",  "type_name": "有码"},
    {"type_id": "uncensored", "type_name": "无码"},
    {"type_id": "amateur",   "type_name": "素人"},
    {"type_id": "chnsub",    "type_name": "中文字幕"},
    {"type_id": "reducing",  "type_name": "薄码"},
    {"type_id": "engsub",    "type_name": "英文字幕"},
    {"type_id": "maker",     "type_name": "厂商"},
    {"type_id": "cast",      "type_name": "演员"},
    {"type_id": "genre",     "type_name": "类型"},
]

CAT_PATH = {
    "home": "",
    "popular": "/popular",
    "censored": "/category/censored-jav",
    "uncensored": "/category/uncensored-jav",
    "amateur": "/category/amateur",
    "chnsub": "/category/chinese-subtitles",
    "reducing": "/category/reducing-mosaic",
    "engsub": "/category/english-subtitles",
}

INDEX_PATH = {"maker": "/maker", "cast": "/cast", "genre": "/tag"}
INDEX_ENTRY_RE = {
    "maker": r"^/category/maker/[a-z0-9\-]+$",
    "cast": r"^/category/cast/[a-z0-9\-]+$",
    "genre": r"^/tag/[a-z0-9\-&]+$",
}

JUMP_HOSTS = ["https://lk1.supremejav.com"]


def _dec(raw):
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")


def txt_of(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(s)).strip()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Spider(BaseSpider):
    def getName(self):
        return "SupJav"

    # 壳可能不先调 init 就直接调方法 —— ext 一律懒解析
    def init(self, extend=""):
        self._ext_raw = extend
        self._ext = None

    def _get_ext(self):
        if getattr(self, "_ext", None) is None:
            raw = getattr(self, "_ext_raw", "") or ""
            try:
                self._ext = json.loads(raw) if raw else {}
            except Exception:
                self._ext = {}
            if not isinstance(self._ext, dict):
                self._ext = {}
        return self._ext

    def _host(self):
        h = self._get_ext().get("host") or "https://supjav.com"
        return h.rstrip("/")

    def _headers(self, referer=None):
        h = {"User-Agent": UA,
             "Referer": referer or (self._host() + "/"),
             "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                       "image/avif,image/webp,*/*;q=0.8",
             "Accept-Language": "en-US,en;q=0.9",
             "Upgrade-Insecure-Requests": "1",
             "Sec-Fetch-Dest": "document",
             "Sec-Fetch-Mode": "navigate",
             "Sec-Fetch-Site": "same-origin"}
        ck = self._get_ext().get("cookie")
        if ck:
            h["Cookie"] = ck
        return h

    @staticmethod
    def _is_cf_block(text):
        if not text:
            return False
        head = text[:8000]
        return ("Attention Required" in head
                or "Performing security verification" in head
                or "/cdn-cgi/challenge-platform" in head
                or "Just a moment" in head)

    def fetch(self, url, referer=None, follow=True):
        """普通 GET,返回 (文本, 最终URL);失败返回 ('', None)。
        主站被 CF 拦时(拦的是裸域)自动用 www 子域再试一次。"""
        text, final = self._fetch_once(url, referer, follow)
        if self._is_cf_block(text):
            host = urllib.parse.urlparse(url).hostname or ""
            if host == "supjav.com":
                alt = url.replace("://supjav.com", "://www.supjav.com", 1)
                t2, f2 = self._fetch_once(alt, referer, follow)
                if t2 and not self._is_cf_block(t2):
                    return t2, f2
        return text, final

    def _fetch_once(self, url, referer=None, follow=True):
        opener = urllib.request.build_opener() if follow else \
            urllib.request.build_opener(_NoRedirect())
        for attempt in range(RETRY):
            try:
                req = urllib.request.Request(url, headers=self._headers(referer))
                with opener.open(req, timeout=TIMEOUT) as r:
                    raw = r.read()
                    if raw[:2] == b"\x1f\x8b":
                        raw = gzip.decompress(raw)
                    return _dec(raw), r.geturl()
            except urllib.error.HTTPError as e:
                try:
                    raw = e.read()
                    if raw[:2] == b"\x1f\x8b":
                        raw = gzip.decompress(raw)
                    return _dec(raw), url
                except Exception:
                    return "", None
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        return "", None

    def fetch_location(self, url, referer=None):
        """不跟随跳转,返回 (状态码, Location 或正文)。"""
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            req = urllib.request.Request(url, headers=self._headers(referer))
            with opener.open(req, timeout=TIMEOUT) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return r.status, _dec(raw)
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location") if e.headers else None
            if loc:
                return e.code, loc
            try:
                return e.code, _dec(e.read())
            except Exception:
                return e.code, ""
        except Exception:
            return 0, ""

    # ── 列表解析 ──────────────────────────────────────────────
    def parse_cards(self, html):
        """div.post 卡片:详情链 /{id}.html + data-original 封面 + h3 标题。"""
        out, seen = [], set()
        if not html:
            return out
        for chunk in re.split(r'<div class="post">', html)[1:]:
            m = re.search(r'href="((?:https?://[^"/]+)?/\d+\.html)"', chunk)
            if not m:
                continue
            path = urllib.parse.urlparse(m.group(1)).path
            if path in seen:
                continue
            seen.add(path)
            pic = ""
            pm = re.search(r'data-original="([^"]+)"', chunk) or \
                re.search(r'<img[^>]+src="(https?://img\.[^"]+)"', chunk)
            if pm:
                pic = pm.group(1)
            title = ""
            tm = re.search(r'<h3[^>]*>\s*<a[^>]*title="([^"]+)"', chunk) or \
                re.search(r'<a[^>]+class="img"[^>]*title="([^"]+)"', chunk)
            if tm:
                title = txt_of(tm.group(1))
            if not title:
                tm2 = re.search(r'<h3[^>]*>\s*<a[^>]*>(.*?)</a>', chunk, re.S)
                if tm2:
                    title = txt_of(tm2.group(1))
            remark = ""
            rm = re.search(r'<div class="meta">(.*?)</div>', chunk, re.S)
            if rm:
                remark = txt_of(rm.group(1))
            out.append({"vod_id": path, "vod_name": title or path,
                        "vod_pic": pic, "vod_remarks": remark})
        return out

    def page_url(self, base_path, pg):
        pg = int(pg)
        if pg <= 1:
            return self._host() + (base_path or "/")
        return self._host() + base_path + "/page/%d" % pg

    def pagecount_of(self, html, items, pg):
        mx = int(pg)
        for m in re.finditer(r'/page/(\d+)', html or ""):
            mx = max(mx, int(m.group(1)))
        if len(items) >= 24:
            return max(mx, 9999) if mx == int(pg) else mx
        return int(pg)

    # ── TVBox 接口 ────────────────────────────────────────────
    def homeContent(self, filter):
        result = {"class": CATS}
        html, _ = self.fetch(self._host() + "/")
        result["list"] = self.parse_cards(html)
        return result

    def homeVideoContent(self):
        html, _ = self.fetch(self._host() + "/")
        return {"list": self.parse_cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        if tid in INDEX_PATH:
            html, _ = self.fetch(self.page_url(INDEX_PATH[tid], pg))
            items = self.parse_index(html, tid)
            pc = pg
            if items:
                pc = 9999 if len(items) >= 100 else pg
            return {"list": items, "page": pg, "pagecount": pc,
                    "limit": len(items), "total": 999999}
        if tid.startswith("/"):
            html, _ = self.fetch(self.page_url(tid, pg))
            items = self.parse_cards(html)
            return {"list": items, "page": pg,
                    "pagecount": self.pagecount_of(html, items, pg),
                    "limit": len(items), "total": 999999}
        path = CAT_PATH.get(tid, "")
        html, _ = self.fetch(self.page_url(path, pg))
        items = self.parse_cards(html)
        return {"list": items, "page": pg,
                "pagecount": self.pagecount_of(html, items, pg),
                "limit": len(items), "total": 999999}

    def parse_index(self, html, kind):
        """索引页:条目为「名称 (数量)」文本链接,做成 folder 文件夹卡片。"""
        out, seen = [], set()
        pat = re.compile(INDEX_ENTRY_RE[kind])
        for m in re.finditer(r'<a[^>]+href="((?:https?://[^"/]+)?[^"]+)"[^>]*>(.*?)</a>',
                             html or "", re.S):
            path = urllib.parse.urlparse(m.group(1)).path
            if not pat.match(path) or path in seen:
                continue
            name = txt_of(m.group(2))
            if "(" not in name:
                continue
            seen.add(path)
            out.append({"vod_id": path, "vod_name": name,
                        "vod_pic": "", "vod_tag": "folder",
                        "vod_remarks": ""})
        return out

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        url = vid if vid.startswith("http") else self._host() + vid
        html, _ = self.fetch(url)
        vod = {"vod_id": vid, "vod_name": "", "vod_pic": "",
               "vod_content": "", "vod_play_from": "", "vod_play_url": ""}
        if not html:
            vod["vod_name"] = vid
            return {"list": [vod]}
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        title = txt_of(m.group(1)) if m else ""
        vod["vod_name"] = title or vid
        pm = re.search(r'id="player-wrap"[^>]*background-image:\s*url\(([^)]+)\)', html) or \
            re.search(r'<img src="(https?://img\.[^"]+)" class="img"', html)
        if pm:
            vod["vod_pic"] = pm.group(1)
        info = []
        cm = re.search(r'<p class="cat"><a[^>]*>([^<]+)</a>', html)
        if cm:
            info.append("分类: " + txt_of(cm.group(1)))
        for label in ("Maker", "Cast"):
            lm = re.search(r"<span>%s : </span>(.*?)(?:</p>|<br)" % label, html, re.S)
            if lm:
                names = ", ".join(txt_of(x) for x in
                                  re.findall(r"<a[^>]*>([^<]+)</a>", lm.group(1)))
                if names:
                    info.append("%s: %s" % (label, names))
                    if label == "Cast":
                        vod["vod_actor"] = names
        tm = re.findall(r'<div class="tags">(.*?)</div>', html, re.S)
        if tm:
            tags = ", ".join(txt_of(x) for x in
                             re.findall(r"<a[^>]*>([^<]+)</a>", tm[0]))
            if tags:
                info.append("标签: " + tags)
        vod["vod_content"] = " | ".join(info)
        # 服务器/CD 分组:多 CD 时每段一个 .cd-server 块;单 CD 时整页一块
        if "cd-server" in html:
            blocks = re.split(r'class="cd-server[^"]*"', html)[1:]
        else:
            blocks = [html]
        groups = []
        for b in blocks:
            servers = []
            for am in re.finditer(r"<a[^>]*btn-server[^>]*>([^<]*)</a>", b):
                dm = re.search(r'data-link="([0-9a-fA-F]{16,})"', am.group(0))
                if dm:
                    servers.append((txt_of(am.group(1)) or "S", dm.group(1)))
            if servers:
                groups.append(servers)
        if groups:
            code = title.split(" ")[0] if title else "播放"
            names = [n for n, _ in groups[0]]
            lines_url = []
            used_names = []
            for li, lname in enumerate(names):
                eps = []
                for gi, g in enumerate(groups):
                    tok = None
                    for n2, t2 in g:
                        if n2 == lname:
                            tok = t2
                            break
                    if tok is None and li < len(g):
                        tok = g[li][1]
                    if tok:
                        ep = "%s-%d" % (code, gi + 1) if len(groups) > 1 else code
                        eps.append("%s$%s" % (ep, tok))
                if eps:
                    lines_url.append("#".join(eps))
                    used_names.append(lname)
            vod["vod_play_from"] = "$$$".join(used_names)
            vod["vod_play_url"] = "$$$".join(lines_url)
        return {"list": [vod]}

    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg or 1)
        kw = urllib.parse.quote(key)
        if pg <= 1:
            url = self._host() + "/?s=" + kw
        else:
            url = self._host() + "/page/%d/?s=%s" % (pg, kw)
        html, _ = self.fetch(url)
        items = self.parse_cards(html)
        return {"list": items, "page": pg}

    # ── 播放:令牌 → supjav.php?c={反转} → 302 embed → 分宿主解析 ──
    def playerContent(self, flag, id, vipFlags):
        header = {"User-Agent": UA, "Referer": self._host() + "/"}
        token = (id or "").strip()
        if not token:
            return {"parse": 0, "url": "", "header": header}
        jumps = []
        jx = self._get_ext().get("jump")
        if jx:
            jumps.append(jx.rstrip("/"))
        jumps += [j for j in JUMP_HOSTS if j not in jumps]
        embed = ""
        c_url = jumps[0] + "/supjav.php?c=" + token[::-1]
        for j in jumps:
            c_url = j + "/supjav.php?c=" + token[::-1]
            code, loc = self.fetch_location(c_url, referer=j + "/supjav.php")
            if code in (301, 302, 303, 307, 308) and loc.startswith("http"):
                embed = loc
                break
            if code == 200 and loc:
                fm = re.search(r'<iframe[^>]+src="([^"]+)"', loc)
                if fm:
                    embed = urllib.parse.urljoin(c_url, fm.group(1))
                    break
                embed = c_url
                break
        if not embed:
            return {"parse": 1, "url": c_url, "header": header}
        host = urllib.parse.urlparse(embed).netloc.lower()
        if "streamtape." in host or "tapecontent." in host:
            direct = self._resolve_streamtape(embed)
            if direct:
                return {"parse": 0, "url": direct,
                        "header": {"User-Agent": UA,
                                   "Referer": "https://streamtape.com/"}}
            return {"parse": 1, "url": embed, "header": header}
        direct = self._resolve_generic(embed)
        if direct:
            return {"parse": 0, "url": direct,
                    "header": {"User-Agent": UA, "Referer": embed}}
        return {"parse": 1, "url": embed, "header": header}

    def _resolve_streamtape(self, embed):
        html, _ = self.fetch(embed, referer=self._host() + "/")
        if not html:
            return ""
        m = re.search(r'get_video\?id=([A-Za-z0-9]+)&(?:amp;)?expires=(\d+)'
                      r'&(?:amp;)?ip=([^&"\'<]+)&(?:amp;)?token=([^&"\'<]+)', html)
        if not m:
            return ""
        return ("https://streamtape.com/get_video?id=%s&expires=%s&ip=%s&token=%s"
                % (m.group(1), m.group(2), m.group(3), m.group(4)))

    def _resolve_generic(self, embed):
        html, _ = self.fetch(embed, referer=self._host() + "/")
        if not html:
            return ""
        m = re.search(r'https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*', html)
        if m:
            return m.group(0)
        m = re.search(r'https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*', html)
        if m and "thumb" not in m.group(0) and "poster" not in m.group(0):
            return m.group(0)
        # VOE 等把源藏在 base64 JSON 里:粗扫长串解码后找 m3u8
        import base64
        for bm in re.finditer(r'[A-Za-z0-9+/=]{120,}', html):
            try:
                dec = base64.b64decode(bm.group(0) + "==").decode("utf-8", "ignore")
            except Exception:
                continue
            mm = re.search(r'https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*', dec)
            if mm:
                return mm.group(0)
        return ""
