# -*- coding: utf-8 -*-
# madou_spider.py  —  madou.club 零依赖单文件 py 源
# Python 3.6+ / 仅标准库 / TVBox · 影视仓 · fongmi 内核通用
#
# 站点定性：WordPress 网页采集型 + 外链 embed 播放
#   列表/搜索/详情  -> 直接啃静态 HTML（服务端渲染，无需 JS）
#   播放地址        -> iframe 指向 dash.madou.club/share/<hash>，
#                      该页内嵌 JWT token + index.m3u8 路径，播放时现取
#
# 换域名：只改下面常量区的 HOST / PLAY_HOST 两行。

import os
import re
import sys
import json
from html import unescape
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError

# ============================================================
# 常量区（换站只动这里）
# ============================================================
HOST = "https://madou.club"
PLAY_HOST = "https://dash.madou.club"
NAME = "麻豆社"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
TIMEOUT = 12
PAGE_SIZE = 20          # 站点每页 20 条（实测）
HOME_TID = "/"          # 首页 = 最新发布
DEFAULT_PROXY = ""      # 留空 = 直连；也可在 ext 里填 {"proxy":"http://192.168.1.2:7890"}

# ============================================================
# 内核基类（找不到就退回内置兜底，本文件也能单跑）
# ============================================================
_KernelSpider = None
try:
    from base.spider import Spider as _KernelSpider
except Exception:
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from base.spider import Spider as _KernelSpider
    except Exception:
        _KernelSpider = None


class _FallbackSpider(object):
    """本机单跑 / 内核未提供基类时的兜底，签名与内核契约一致。"""

    def getName(self):
        return ""

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {}

    def homeVideoContent(self):
        return {}

    def categoryContent(self, tid, pg, filter, extend):
        return {}

    def detailContent(self, array):
        return {}

    def searchContent(self, key, quick, pg="1"):
        return {}

    def playerContent(self, flag, id, vipFlags):
        return {}

    def localProxy(self, param):
        return [404, "text/plain", ""]

    def getDependence(self):
        return []

    def destroy(self):
        pass


BaseSpider = _KernelSpider if _KernelSpider is not None else _FallbackSpider

# ============================================================
# 正则（全部对着实测 HTML 写）
# ============================================================
_RE_ART = re.compile(r'<article class="excerpt[^"]*">(.*?)</article>', re.S)
_RE_ART_HREF = re.compile(r'class="thumbnail"[^>]*href="([^"]+)"')
_RE_ART_IMG = re.compile(r'data-src="([^"]+)"')
_RE_ART_TITLE = re.compile(r'<h2>\s*<a[^>]*>(.*?)</a>', re.S)

_RE_TITLE = re.compile(r'<h1 class="article-title">(.*?)</h1>', re.S)
_RE_TITLE_ALT = re.compile(r'<title>(.*?)</title>', re.S)
_RE_IFRAME = re.compile(r'<iframe[^>]*?src=["\']?([^"\'\s>]+)', re.I)
_RE_SHARE_HASH = re.compile(r'/share/([0-9a-fA-F]+)')
_RE_M3U8_ANY = re.compile(r'https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*', re.I)
_RE_MP4_ANY = re.compile(r'https?://[^\s"\'<>]+?\.mp4[^\s"\'<>]*', re.I)

_RE_TOKEN = re.compile(r'var\s+token\s*=\s*"([^"]*)"')
_RE_M3U8_VAR = re.compile(r'var\s+m3u8\s*=\s*[\'"]([^\'"]+)[\'"]')
_RE_CAT = re.compile(r'<span class="item item-3">.*?<a[^>]*>(.*?)</a>', re.S)
_RE_VIEWS = re.compile(r'<span class="item item-4">(.*?)</span>', re.S)
_RE_KEYWORDS = re.compile(r'name="keywords"\s+content="([^"]*)"')
_RE_COVER = re.compile(r'<img[^>]+data-src="(https?://[^"]+?/covers/[^"]+)"')
_RE_NAV = re.compile(r'<div class="sitenav">(.*?)</div>\s*</div>', re.S)
_RE_NAV_CAT = re.compile(
    r'<a href="(https?://[^"]*?/category/[^"]+)"[^>]*>([^<]+)</a>')

_RE_TAG = re.compile(r'<[^>]+>')
_RE_WS = re.compile(r'[ \t\r\n\u3000]+')
# 搜索关键词里的危险字符会被站点 WAF 直接 403，先洗掉
_RE_BAD_KEY = re.compile(r'[&%<>#?\'"\\/|]+')


# ============================================================
# 主体
# ============================================================
class Spider(BaseSpider):

    def __init__(self):
        try:
            BaseSpider.__init__(self)
        except Exception:
            pass
        self.host = HOST
        self.play_host = PLAY_HOST
        self.name = NAME
        self.header = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self._cats = None
        self._proxy = DEFAULT_PROXY
        self._opener = None
        self._apply_proxy()

    def _apply_proxy(self):
        """配了代理就走代理，没配就走直连。"""
        proxy = (self._proxy or "").strip()
        if not proxy:
            self._opener = None
            return
        if not proxy.startswith(("http://", "https://", "socks5://")):
            self._log("代理地址格式不对（要带 http:// 前缀），按直连处理：%s" % proxy)
            self._proxy = ""
            self._opener = None
            return
        try:
            self._opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}))
        except Exception as exc:
            self._log("代理配置无效，退回直连：%s" % exc)
            self._proxy = ""
            self._opener = None

    # ---------- 内核契约 ----------
    def getName(self):
        return self.name

    def getDependence(self):
        return []

    def init(self, extend=""):
        ext = extend
        if isinstance(ext, bytes):
            try:
                ext = ext.decode("utf-8")
            except Exception:
                ext = ""
        if not ext:
            return

        if isinstance(ext, dict):
            cfg = ext
        else:
            text = str(ext).strip()
            cfg = None
            if text.startswith("{"):
                try:
                    cfg = json.loads(text)
                except Exception:
                    try:
                        cfg = json.loads(text.replace("'", '"'))
                    except Exception:
                        cfg = None
            if cfg is None:
                if text.startswith("http"):
                    self.host = text.rstrip("/")
                return

        if not isinstance(cfg, dict):
            return
        h = cfg.get("host") or cfg.get("url") or cfg.get("site")
        if h and str(h).startswith("http"):
            self.host = str(h).rstrip("/")
        p = cfg.get("play_host") or cfg.get("playHost")
        if p and str(p).startswith("http"):
            self.play_host = str(p).rstrip("/")
        n = cfg.get("name")
        if n:
            self.name = str(n)
        px = cfg.get("proxy")
        if px is not None:
            self._proxy = str(px).strip()
            self._apply_proxy()
        self.header["Referer"] = self.host + "/"

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return (".m3u8" in u) or (".mp4" in u) or (".flv" in u)

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [404, "text/plain", ""]

    def destroy(self):
        pass

    # ---------- 工具 ----------
    def _log(self, msg):
        try:
            sys.stdout.write("[madou] " + str(msg) + "\n")
        except Exception:
            pass

    def _http(self, url, referer=None, timeout=None):
        """GET 取文本，失败返回空串，不把异常抛给内核。"""
        if not url:
            return ""
        try:
            req = Request(url, headers={
                "User-Agent": UA,
                "Referer": referer or (self.host + "/"),
                "Accept": ("text/html,application/xhtml+xml,application/xml;"
                           "q=0.9,image/webp,*/*;q=0.8"),
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            resp = (self._opener.open(req, timeout=timeout or TIMEOUT)
                    if self._opener is not None
                    else urlopen(req, timeout=timeout or TIMEOUT))
            raw = resp.read()
        except (HTTPError, URLError, OSError, ValueError) as exc:
            self._log("请求失败 %s : %s" % (url, exc))
            return ""

        for enc in ("utf-8", "gbk", "big5"):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", "replace")

    def _abs(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.host + url
        return urljoin(self.host + "/", url)

    def _clean(self, text):
        if not text:
            return ""
        text = _RE_TAG.sub("", text)
        text = unescape(text)
        text = text.replace("\u2026", "").strip()
        return _RE_WS.sub(" ", text).strip()

    def _clean_key(self, key):
        """清洗搜索词：站点 WAF 对 & % < > 之类直接 403，先替换掉。"""
        k = (key or "").strip()
        k = _RE_BAD_KEY.sub(" ", k)
        return _RE_WS.sub(" ", k).strip()

    def _big_pic(self, pic):
        """列表给的是 -240x180 缩略图，去掉尺寸后缀换原图，失败就用缩略图。"""
        if not pic:
            return ""
        return re.sub(r'-\d+x\d+(\.\w+)$', r'\1', pic)

    def _parse_list(self, html):
        """从任意列表页抽条目（分类 / 搜索 / 首页 结构完全一致）。"""
        if not html:
            return []
        # 只取主列表容器，避免把侧栏的“大家在看”混进来
        m = re.search(r'<div class="excerpts">(.*?)</div>\s*<div class="sidebar"',
                      html, re.S)
        block = m.group(1) if m else html

        items = []
        seen = set()
        for chunk in _RE_ART.findall(block):
            hm = _RE_ART_HREF.search(chunk)
            if not hm:
                continue
            link = self._abs(unescape(hm.group(1)).strip())
            if not link or link in seen:
                continue
            tm = _RE_ART_TITLE.search(chunk)
            if not tm:
                continue
            name = self._clean(tm.group(1))
            if not name:
                continue
            im = _RE_ART_IMG.search(chunk)
            pic = self._abs(unescape(im.group(1)).strip()) if im else ""
            if "showcase/img/thumb" in pic:
                pic = ""
            seen.add(link)
            items.append({
                "vod_id": link,
                "vod_name": name,
                "vod_pic": self._big_pic(pic),
                "vod_remarks": "",
            })
        return items

    def _all_cats(self):
        """站内全部分类（实测 nav 里 31 个），带缓存。"""
        if self._cats is not None:
            return self._cats
        cats = [{"type_id": HOME_TID, "type_name": "最新发布"}]
        html = self._http(self.host + "/")
        navm = _RE_NAV.search(html)
        scope = navm.group(1) if navm else html
        seen = set()
        for href, label in _RE_NAV_CAT.findall(scope):
            href = unescape(href).strip()
            label = self._clean(label)
            path = href.replace(self.host, "") or "/"
            if not label or path in seen:
                continue
            seen.add(path)
            cats.append({"type_id": path, "type_name": label})
        if len(cats) < 2:
            self._log("分类抓取为空，退回首页")
        self._cats = cats
        return cats

    # ---------- 首页 ----------
    def homeContent(self, filter):
        return {"class": self._all_cats(), "filters": {}}

    def homeVideoContent(self):
        return {"list": self._parse_list(self._http(self.host + "/"))}

    # ---------- 分类 / 翻页 ----------
    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg or 1)
        except Exception:
            pg = 1

        path = (tid or HOME_TID).strip()
        if not path.startswith("/"):
            path = "/" + path
        if pg > 1:
            path = path.rstrip("/") + "/page/%d" % pg

        url = self.host + path
        items = self._parse_list(self._http(url))
        pagecount = pg if len(items) < PAGE_SIZE else pg + 1
        return {
            "list": items,
            "page": pg,
            "pagecount": pagecount,
            "limit": PAGE_SIZE,
            "total": pagecount * PAGE_SIZE,
        }

    # ---------- 详情 ----------
    def detailContent(self, array):
        if not array:
            return {"list": []}
        vid = array[0] if isinstance(array, (list, tuple)) else array
        if isinstance(vid, dict):
            vid = vid.get("vod_id") or vid.get("id") or ""
        vid = str(vid).strip()
        if not vid:
            return {"list": []}
        if not vid.startswith("http"):
            vid = self._abs(vid)

        html = self._http(vid)
        if not html:
            return {"list": []}

        tm = _RE_TITLE.search(html) or _RE_TITLE_ALT.search(html)
        name = self._clean(tm.group(1)) if tm else ""
        if name.endswith("-" + NAME):
            name = name[:-(len(NAME) + 1)]

        hashes = []
        for src in _RE_IFRAME.findall(html):
            hm = _RE_SHARE_HASH.search(src)
            if hm and hm.group(1) not in hashes:
                hashes.append(hm.group(1))

        if not hashes:
            # 万一哪天站点把 iframe 换成直链，也不至于全瞎
            for u in (_RE_M3U8_ANY.findall(html) + _RE_MP4_ANY.findall(html)):
                if u not in hashes:
                    hashes.append(u)

        play_url = ""
        if hashes:
            eps = []
            for i, h in enumerate(hashes):
                label = "正片" if len(hashes) == 1 else ("正片%d" % (i + 1))
                eps.append("%s$%s" % (label, h))
            play_url = "#".join(eps)

        pic = ""
        if hashes and not hashes[0].startswith("http"):
            pic = "%s/videos/%s/poster.jpg" % (self.play_host, hashes[0])
        if not pic:
            cm = _RE_COVER.search(html)
            pic = self._big_pic(unescape(cm.group(1))) if cm else ""

        cats = [self._clean(x) for x in _RE_CAT.findall(html)]
        cats = [c for c in cats if c]
        views = _RE_VIEWS.search(html)
        tags = ""
        km = _RE_KEYWORDS.search(html)
        if km:
            tags = unescape(km.group(1)).strip().strip(",").strip()

        intro = []
        if cats:
            intro.append("分类：" + " / ".join(cats))
        if tags:
            intro.append("标签：" + tags)
        if views:
            intro.append("热度：" + self._clean(views.group(1)))
        intro.append("线路：%s（直连 m3u8，播放时自动取 token）" % self.name)

        vod = {
            "vod_id": vid,
            "vod_name": name or self.name,
            "vod_pic": pic,
            "type_name": cats[0] if cats else self.name,
            "vod_year": "",
            "vod_area": "国语",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "\n".join(intro),
            "vod_play_from": self.name,
            "vod_play_url": play_url,
        }
        return {"list": [vod]}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg="1"):
        try:
            pg = int(pg or 1)
        except Exception:
            pg = 1
        key = self._clean_key(key)
        if not key:
            # 关键词被清空（原本就是空的 / 全是特殊字符）→ 不能放行全站列表
            return {"list": [], "page": 1, "pagecount": 0,
                    "limit": PAGE_SIZE, "total": 0}
        url = "%s/?s=%s&paged=%d" % (self.host, quote(key), pg)
        items = self._parse_list(self._http(url))
        if not items and pg == 1 and key:
            # 伪静态搜索兜底（实测 /search/关键词/ 同样可用）
            alt = "%s/search/%s/" % (self.host, quote(key))
            items = self._parse_list(self._http(alt))
        pagecount = pg if len(items) < PAGE_SIZE else pg + 1
        return {
            "list": items,
            "page": pg,
            "pagecount": pagecount,
            "limit": PAGE_SIZE,
            "total": pagecount * PAGE_SIZE,
        }

    # ---------- 播放（核心） ----------
    def playerContent(self, flag, id, vipFlags):
        target = str(id or "").strip()

        hashid = ""
        if target.startswith("http"):
            if ".m3u8" in target or ".mp4" in target:
                # 已经是直链，直接丢给播放器
                return {"parse": 0, "playUrl": "", "url": target, "header": ""}
            hm = _RE_SHARE_HASH.search(target)
            if hm:
                hashid = hm.group(1)
            else:
                # 传进来的是详情页地址，现抓一次
                html = self._http(target)
                for src in _RE_IFRAME.findall(html):
                    hm = _RE_SHARE_HASH.search(src)
                    if hm:
                        hashid = hm.group(1)
                        break
                if not hashid:
                    m = _RE_M3U8_ANY.search(html) or _RE_MP4_ANY.search(html)
                    if m:
                        return {"parse": 0, "playUrl": "", "url": m.group(0),
                                "header": ""}
        else:
            hashid = target

        if not hashid:
            self._log("取不到播放标识：%s" % target)
            return {"parse": 1, "playUrl": "", "url": target, "header": ""}

        # 现取 token + m3u8 路径（token 有效期约 100 秒，必须播放时取）
        share = self._http("%s/share/%s" % (self.play_host, hashid))
        if not share:
            return {"parse": 1, "playUrl": "", "url": target, "header": ""}

        mm = _RE_M3U8_VAR.search(share)
        if not mm:
            m = _RE_M3U8_ANY.search(share)
            if m:
                return {"parse": 0, "playUrl": "", "url": m.group(0),
                        "header": ""}
            self._log("embed 页没解析出 m3u8：%s" % hashid)
            return {"parse": 1, "playUrl": "", "url": target, "header": ""}

        m3u8 = mm.group(1).strip()
        if m3u8.startswith("http"):
            url = m3u8
        elif m3u8.startswith("//"):
            url = "https:" + m3u8
        else:
            url = self.play_host + (m3u8 if m3u8.startswith("/") else "/" + m3u8)

        tm = _RE_TOKEN.search(share)
        if tm and tm.group(1):
            url = url + ("&" if "?" in url else "?") + "token=" + tm.group(1)

        return {"parse": 0, "playUrl": "", "url": url, "header": ""}


# ============================================================
# 本机自测入口（内核里不会走到这里）
# ============================================================
if __name__ == "__main__":
    sp = Spider()
    sp.init("")
    print("== 分类 %d 个 ==" % len(sp.homeContent(False)["class"]))
    for c in sp.homeContent(False)["class"][:5]:
        print("   ", c["type_id"], c["type_name"])
    d = sp.homeVideoContent()["list"]
    print("== 首页条目 %d ==" % len(d))
    if d:
        print("   首条：", d[0]["vod_name"], d[0]["vod_pic"][:70])
        det = sp.detailContent([d[0]["vod_id"]])["list"][0]
        print("== 详情 ==")
        print("   片名：", det["vod_name"])
        print("   播放：", det["vod_play_url"][:60])
        pc = sp.playerContent("", det["vod_play_url"].split("$")[-1], 0)
        print("   parse:", pc["parse"], "url:", pc["url"][:110])
    s = sp.searchContent("苏畅", False, "1")["list"]
    print("== 搜索 苏畅 -> %d 条 ==" % len(s))
    if s:
        print("   首条：", s[0]["vod_name"])
