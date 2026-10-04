# -*- coding: utf-8 -*-
"""
遮天 · 射我里面
发布页: shewo1.cc → 实际线路 shewo40/41/42.cc
"""
import sys
import re
import json
import time
import random
from urllib.parse import quote, urljoin, unquote
from html import unescape

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        def __init__(self):
            pass

try:
    import requests
    import urllib3
    urllib3.disable_warnings()
    HAS_REQ = True
except Exception:
    HAS_REQ = False
    from urllib import request as urlrequest


class Spider(BaseSpider):
    # 候选主站（发布页会跳到带随机子域的 shewo40/41/42）
    HOST_CANDIDATES = [
        "https://shewo40.cc",
        "https://shewo41.cc",
        "https://shewo42.cc",
        "https://shewo39.cc",
    ]
    host = HOST_CANDIDATES[0]
    session = None
    _debug = True
    _categories = []
    _ready = False

    AD_TITLE_FILTER = ["广告", "推广", "合作", "APP", "下载", "注册", "菠菜", "博彩", "棋牌"]
    AD_LINE_FILTER = ["广告", "推广", "APP", "下载", "合作", "菠菜", "博彩"]
    AD_DOMAIN_FILTER = ["doubleclick", "adservice", "adsystem", "adnxs", "openx", "casalemedia"]

    def _log(self, msg):
        if self._debug:
            print("[shewo] %s" % msg)

    def getName(self):
        return "射我里面"

    def isVideoFormat(self, url):
        return bool(url and (".m3u8" in url or ".mp4" in url or ".ts" in url))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session is not None:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None

    def _headers(self, referer=None):
        return {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": referer or (self.host + "/"),
        }

    def _fetch(self, url, referer=None, retries=3):
        for attempt in range(retries):
            try:
                if attempt:
                    time.sleep(random.uniform(0.3, 1.0))
                if HAS_REQ:
                    if self.session is None:
                        self.session = requests.Session()
                    r = self.session.get(
                        url,
                        headers=self._headers(referer),
                        timeout=(10, 20),
                        verify=False,
                        allow_redirects=True,
                    )
                    r.encoding = "utf-8"
                    if r.status_code == 200 and r.text:
                        return r.text
                else:
                    req = urlrequest.Request(url, headers=self._headers(referer))
                    with urlrequest.urlopen(req, timeout=20) as resp:
                        return resp.read().decode("utf-8", "replace")
            except Exception as e:
                self._log("fetch %s %s" % (url, e))
        return ""

    def _probe_host(self):
        """探测可用主站：含 voddetail / pornkvideos 即成功"""
        for h in self.HOST_CANDIDATES:
            html = self._fetch(h + "/")
            if html and ("pornkvideos" in html or "/voddetail/" in html or "/vodtype/" in html):
                self.host = h
                self._log("host ok %s len=%s" % (h, len(html)))
                return html
            # 带发布目录试一次
            for folder in ("力争上游", "奋发图强", "持之以恒"):
                html = self._fetch(h + "/" + quote(folder) + "/")
                if html and ("pornkvideos" in html or "/voddetail/" in html):
                    self.host = h
                    self._log("host ok %s/%s" % (h, folder))
                    return html
        # 仍失败则用默认
        self.host = self.HOST_CANDIDATES[0]
        return self._fetch(self.host + "/")

    def _parse_categories(self, html):
        cats = []
        if not html:
            return cats
        # 站内分类常见在 listlinks / 侧栏 vodtype
        for href, text in re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.S):
            m = re.search(r"/vodtype/(\d+)\.html", href)
            if not m:
                continue
            # 排除外链
            if href.startswith("http") and "shewo" not in href:
                continue
            tid = m.group(1)
            name = re.sub(r"<[^>]+>", "", text).strip()
            if not name or len(name) > 20:
                continue
            if name in ("首页", "搜索", "全部", "更多", "排行", "留言", "帮助", "返回首页", "发布页", "传送门"):
                continue
            if any(k in name for k in self.AD_TITLE_FILTER):
                continue
            cats.append({"type_id": tid, "type_name": name})
        # 去重
        seen, out = set(), []
        for c in cats:
            if c["type_id"] not in seen:
                seen.add(c["type_id"])
                out.append(c)
        return out

    def _fallback_cats(self):
        return [
            {"type_id": "55", "type_name": "国产精品"},
            {"type_id": "63", "type_name": "华语精品"},
            {"type_id": "58", "type_name": "黑料吃瓜"},
            {"type_id": "60", "type_name": "欧美大屌"},
            {"type_id": "57", "type_name": "动漫禁漫"},
            {"type_id": "65", "type_name": "学生合集"},
            {"type_id": "64", "type_name": "乱伦精品"},
            {"type_id": "61", "type_name": "探花约炮"},
            {"type_id": "86", "type_name": "日本无码"},
            {"type_id": "80", "type_name": "日本有码"},
            {"type_id": "81", "type_name": "主播网红"},
            {"type_id": "12", "type_name": "国产色情"},
            {"type_id": "21", "type_name": "自拍偷拍"},
            {"type_id": "22", "type_name": "人妻熟女"},
            {"type_id": "24", "type_name": "欧美精品"},
            {"type_id": "69", "type_name": "卡通动漫"},
            {"type_id": "75", "type_name": "中文字幕"},
        ]

    def init(self, extend=""):
        self._log("init")
        self.destroy()
        if HAS_REQ:
            self.session = requests.Session()
        html = self._probe_host()
        cats = self._parse_categories(html) if html else []
        self._categories = cats if cats else self._fallback_cats()
        self._ready = True
        self._log("cats %s host %s" % (len(self._categories), self.host))
        return True

    def _parse_video_list(self, html):
        items = []
        if not html:
            return items
        # 卡片
        blocks = re.findall(
            r'<div[^>]+class="[^"]*pornkvideos[^"]*"[^>]*>([\s\S]*?)(?=<div[^>]+class="[^"]*pornkvideos|$)',
            html,
        )
        if not blocks:
            # 兜底：直接扫 voddetail
            for m in re.finditer(
                r'href="(/voddetail/(\d+)\.html)"[\s\S]{0,500}?data-src="([^"]+)"[\s\S]{0,400}?<h2[^>]*>([\s\S]*?)</h2>',
                html,
            ):
                blocks.append(m.group(0))
        seen = set()
        for block in blocks:
            link = re.search(r'href="(/voddetail/(\d+)\.html)"', block)
            if not link:
                continue
            vid = link.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            img_m = re.search(r'data-src="(https?://[^"]+)"', block)
            if not img_m:
                img_m = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', block)
            title_m = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", block)
            title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else vid
            title = unescape(re.sub(r"\s+", " ", title))
            if any(k in title for k in self.AD_TITLE_FILTER):
                continue
            img = img_m.group(1) if img_m else ""
            remarks = ""
            vl = re.search(r'class="vlength"[^>]*>([\s\S]*?)</div>', block)
            if vl:
                remarks = re.sub(r"<[^>]+>", "", vl.group(1)).strip()
            items.append(
                {
                    "vod_id": vid,
                    "vod_name": title[:80] or vid,
                    "vod_pic": img,
                    "vod_remarks": remarks,
                }
            )
        return items

    def homeContent(self, filter=False):
        try:
            if not self._ready:
                self.init()
            html = self._fetch(self.host + "/")
            if not html or "pornkvideos" not in html:
                html = self._probe_host()
            items = self._parse_video_list(html) if html else []
            cats = self._categories or self._fallback_cats()
            self._log("home list %s" % len(items))
            return {"class": cats, "list": items}
        except Exception as e:
            self._log("home %s" % e)
            return {"class": self._fallback_cats(), "list": []}

    def homeVideoContent(self):
        html = self._fetch(self.host + "/")
        return {"list": self._parse_video_list(html) if html else []}

    def categoryContent(self, tid, pg, filter=False, extend=""):
        try:
            if not self._ready:
                self.init()
            page = int(pg) if str(pg).isdigit() else 1
            if page > 1:
                url = "%s/vodtype/%s-%s.html" % (self.host, tid, page)
            else:
                url = "%s/vodtype/%s.html" % (self.host, tid)
            html = self._fetch(url)
            items = self._parse_video_list(html) if html else []
            total_pages = page
            if html:
                nums = re.findall(r"/vodtype/%s[-_](\d+)\.html" % re.escape(str(tid)), html)
                if nums:
                    total_pages = max(int(x) for x in nums)
                else:
                    total_pages = page + (1 if items else 0)
            self._log("cate %s p%s n=%s" % (tid, page, len(items)))
            return {
                "list": items,
                "page": page,
                "pagecount": max(total_pages, page),
                "limit": 24,
                "total": 99999 if items else 0,
            }
        except Exception as e:
            self._log("cate %s" % e)
            return {"list": [], "page": 1, "pagecount": 1, "limit": 24, "total": 0}

    def _extract_m3u8(self, html):
        urls = []
        if not html:
            return urls
        # player_aaaa= {...}  （无 var）
        m = re.search(r"player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>", html)
        if not m:
            m = re.search(r"var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;", html)
        if m:
            raw = m.group(1)
            try:
                data = json.loads(raw)
                u = (data.get("url") or "").replace("\\/", "/")
                if u.startswith("http"):
                    urls.append(unquote(u))
            except Exception:
                um = re.search(r'"url"\s*:\s*"([^"]+)"', raw)
                if um:
                    urls.append(unquote(um.group(1).replace("\\/", "/")))
        for u in re.findall(r"https?:\\?/\\?/[^\s\"'<>]+\\.m3u8[^\s\"'<>]*", html):
            urls.append(u.replace("\\/", "/"))
        for u in re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html):
            urls.append(u)
        seen, clean = set(), []
        for u in urls:
            u = u.replace("\\/", "/")
            if not u.startswith("http"):
                continue
            if any(ad in u.lower() for ad in self.AD_DOMAIN_FILTER):
                continue
            if u not in seen:
                seen.add(u)
                clean.append(u)
        return clean

    def detailContent(self, ids):
        try:
            if not self._ready:
                self.init()
            vid = str(ids[0] if isinstance(ids, list) else ids)
            html = self._fetch("%s/voddetail/%s.html" % (self.host, vid))
            if not html:
                return {"list": []}

            title = ""
            m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html)
            if m:
                title = unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())
            if not title:
                m = re.search(r"<title>([^<]+)</title>", html)
                if m:
                    title = m.group(1).split("_")[0].strip()

            cover = ""
            m = re.search(r'data-src="(https?://[^"]+)"', html)
            if m:
                cover = m.group(1)
            if not cover:
                m = re.search(r'property="og:image"\s+content="([^"]+)"', html)
                if m:
                    cover = m.group(1)

            play_links = re.findall(
                r'href="(/vodplay/\d+-\d+-\d+\.html)"[^>]*>([\s\S]*?)</a>', html
            )
            if not play_links:
                play_links = [( "/vodplay/%s-1-1.html" % vid, "播放" )]

            from_lines, url_lines = [], []
            cache = {}
            for href, btn in play_links:
                name = re.sub(r"<[^>]+>", "", btn).strip() or "播放"
                if any(k in name for k in self.AD_LINE_FILTER):
                    continue
                if href not in cache:
                    play_html = self._fetch(urljoin(self.host, href))
                    cache[href] = self._extract_m3u8(play_html)
                m3u8s = cache[href]
                if m3u8s:
                    from_lines.append(name)
                    url_lines.append("#".join("%s$%s" % (name if i == 0 else "%s_%s" % (name, i + 1), u) for i, u in enumerate(m3u8s)))
                else:
                    from_lines.append(name)
                    url_lines.append("%s$%s" % (name, urljoin(self.host, href)))

            if not from_lines:
                # 直接试默认播放页
                play_html = self._fetch("%s/vodplay/%s-1-1.html" % (self.host, vid))
                m3u8s = self._extract_m3u8(play_html)
                if m3u8s:
                    from_lines = ["线路1"]
                    url_lines = ["播放$%s" % m3u8s[0]]
                else:
                    return {"list": []}

            return {
                "list": [
                    {
                        "vod_id": vid,
                        "vod_name": title[:80] or vid,
                        "vod_pic": cover,
                        "vod_play_from": "$$$".join(from_lines),
                        "vod_play_url": "$$$".join(url_lines),
                    }
                ]
            }
        except Exception as e:
            self._log("detail %s" % e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            url = (id or "").replace("\\/", "/")
            if any(ad in url.lower() for ad in self.AD_DOMAIN_FILTER):
                return {"parse": 0, "url": "", "header": {}}
            header = {
                "User-Agent": self._headers()["User-Agent"],
                "Referer": self.host + "/",
            }
            if url.startswith("http") and any(x in url for x in [".m3u8", ".mp4", ".flv"]):
                return {"parse": 0, "url": url, "header": header}
            # 播放页再解
            if "/vodplay/" in url or url.isdigit():
                if url.isdigit():
                    url = "%s/vodplay/%s-1-1.html" % (self.host, url)
                elif not url.startswith("http"):
                    url = urljoin(self.host, url)
                html = self._fetch(url)
                m3u8s = self._extract_m3u8(html)
                if m3u8s:
                    return {"parse": 0, "url": m3u8s[0], "header": header}
                return {"parse": 1, "url": url, "header": header}
            return {"parse": 1, "url": url, "header": header}
        except Exception as e:
            self._log("player %s" % e)
            return {"parse": 1, "url": id, "header": {}}

    def searchContent(self, key, quick, pg="1"):
        try:
            if not self._ready:
                self.init()
            page = int(pg) if str(pg).isdigit() else 1
            url = "%s/vodsearch/-------------.html?wd=%s&page=%s" % (
                self.host,
                quote(key),
                page,
            )
            html = self._fetch(url)
            items = self._parse_video_list(html) if html else []
            return {"list": items, "page": page, "pagecount": page + (1 if items else 0)}
        except Exception as e:
            self._log("search %s" % e)
            return {"list": [], "page": 1, "pagecount": 1}

    def localProxy(self, param):
        return [200, "text/plain", b"ok"]
