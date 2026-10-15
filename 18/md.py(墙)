# -*- coding: utf-8 -*-
# madou_spider.py  —  madou.club 零依赖单文件 py 源   v2「全站导航版」
# Python 3.6+ / 仅标准库 / TVBox · 影视仓 · fongmi 内核通用
#
# 站点定性：WordPress 网页采集型 + 外链 embed 播放
#   列表/搜索/详情  -> 直接啃静态 HTML（服务端渲染，无需 JS）
#   播放地址        -> iframe 指向 dash.madou.club/share/<hash>，
#                      该页内嵌 JWT token + index.m3u8 路径，播放时现取
#
# v2 改了什么：
#   1. 导航类型不再只靠首页抓（首页只挂了 31 个），改成「内置全站 45 个分类
#      + 点赞排行 + 50 个热门标签」，整站写进源里，断网也点得出来
#   2. 首页抓到的导航作为「补漏」合并进去 —— 站方以后新加分类，照样自动出现
#   3. 列表容器正则修正（原来那段匹配不上，会把侧栏条目混进来）
#   4. 翻页地址统一 /page/N/；点赞排行是单页，不再给假分页
#   5. 播放请求带上 UA + 站点 Referer，更容易过播放侧防盗链
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

INCLUDE_TAGS = True     # 是否把 50 个热门标签也列进导航（不想要就改 False）
PLAY_HEADER = True      # 播放时是否带 UA/Referer 头（个别播放器不认就改 False）
NO_PAGE_TID = ("/likes",)   # 这些入口是单页，不做翻页

# ============================================================
# 内置全站导航（逐个实测过，名称取分类页官方标题）
# ============================================================
# 榜单/聚合页
RANK_PAGES = [
    ("/likes", "点赞排行"),
]

# 全站分类：45 个
CATEGORIES = [
    ("/category/%e9%ba%bb%e8%b1%86%e4%bc%a0%e5%aa%92", "麻豆传媒"),
    ("/category/%e9%ba%bb%e8%b1%86%e7%95%aa%e5%a4%96%e7%af%87", "麻豆番外篇"),
    ("/category/%e9%ba%bb%e8%b1%86%e8%8a%b1%e7%b5%ae", "麻豆花絮"),
    ("/category/%e9%ba%bb%e8%b1%86%e5%af%bc%e6%bc%94%e7%b3%bb%e5%88%97", "麻豆导演系列"),
    ("/category/hongkongdoll", "HongKongDoll"),
    ("/category/psychoporntw", "PsychopornTW"),
    ("/category/91%e5%88%b6%e7%89%87%e5%8e%82", "91制片厂"),
    ("/category/%e6%9e%9c%e5%86%bb%e4%bc%a0%e5%aa%92", "果冻传媒"),
    ("/category/%e8%9c%9c%e6%a1%83%e5%bd%b1%e5%83%8f", "蜜桃影像"),
    ("/category/%e5%a4%a9%e7%be%8e%e4%bc%a0%e5%aa%92", "天美传媒"),
    ("/category/%e7%9a%87%e5%ae%b6%e5%8d%8e%e4%ba%ba", "皇家华人"),
    ("/category/%e5%85%94%e5%ad%90%e5%85%88%e7%94%9f", "兔子先生"),
    ("/category/%e6%98%9f%e7%a9%ba%e6%97%a0%e9%99%90%e4%bc%a0%e5%aa%92", "星空无限传媒"),
    ("/category/%e7%b2%be%e4%b8%9c%e5%bd%b1%e4%b8%9a", "精东影业"),
    ("/category/%e7%8c%ab%e7%88%aa%e5%bd%b1%e5%83%8f", "猫爪影像"),
    ("/category/%e5%a4%a7%e8%b1%a1%e4%bc%a0%e5%aa%92", "大象传媒"),
    ("/category/%e5%a4%a9%e9%a9%ac%e4%bc%a0%e5%aa%92", "天马传媒"),
    ("/category/%e6%89%a3%e6%89%a3%e4%bc%a0%e5%aa%92", "扣扣传媒"),
    ("/category/%e6%b8%a1%e8%be%b9%e4%bc%a0%e5%aa%92", "渡边传媒"),
    ("/category/%e4%b9%8c%e9%b8%a6%e4%bc%a0%e5%aa%92", "乌鸦传媒"),
    ("/category/%e8%b1%9a%e8%b1%9a%e5%88%9b%e5%aa%92", "豚豚创媒"),
    ("/category/%e5%bc%80%e5%bf%83%e9%ac%bc%e4%bc%a0%e5%aa%92", "开心鬼传媒"),
    ("/category/%e7%88%b1%e6%b1%a1%e4%bc%a0%e5%aa%92", "爱污传媒"),
    ("/category/mini%e4%bc%a0%e5%aa%92", "Mini传媒"),
    ("/category/sa%e5%9b%bd%e9%99%85%e4%bc%a0%e5%aa%92", "SA国际传媒"),
    ("/category/%e8%b5%b7%e7%82%b9%e4%bc%a0%e5%aa%92-%e6%80%a7%e8%a7%86%e7%95%8c%e4%bc%a0%e5%aa%92", "起点传媒/性视界传媒"),
    ("/category/%e4%b9%90%e6%92%ad%e4%bc%a0%e5%aa%92", "乐播传媒"),
    ("/category/%e4%b9%90%e5%a4%a9", "乐天"),
    ("/category/%e6%9d%8f%e5%90%a7", "杏吧"),
    ("/category/%e7%88%b1%e8%b1%86", "爱豆"),
    ("/category/%e6%8a%96%e9%98%b4", "抖阴"),
    ("/category/%e8%8d%89%e8%8e%93", "草莓"),
    ("/category/%e9%a6%99%e8%95%89%e8%a7%86%e9%a2%91", "香蕉视频"),
    ("/category/%e5%a4%a9%e4%bd%bf%e6%98%a0%e7%94%bb", "天使映画"),
    ("/category/%e5%8f%ae%e5%8f%ae%e6%98%a0%e7%94%bb", "叮叮映画"),
    ("/category/%e6%80%a7%e6%a2%a6%e8%80%85", "性梦者"),
    ("/category/kiss%e7%b3%96%e6%9e%9c%e5%b1%8b", "KISS糖果屋"),
    ("/category/%e6%83%85%e8%b6%a3k%e6%ad%8c%e6%88%bf", "情趣K歌房"),
    ("/category/%e5%b0%8f%e9%b9%8f%e5%a5%87%e5%95%aa%e8%a1%8c", "小鹏奇啪行"),
    ("/category/%e7%aa%81%e8%a2%ad%e5%a5%b3%e4%bc%98%e5%ae%b6", "突袭女优家"),
    ("/category/%e5%a5%b3%e7%a5%9e%e7%be%9e%e7%be%9e%e7%a0%94%e7%a9%b6%e6%89%80", "女神羞羞研究所"),
    ("/category/%e5%a5%b3%e4%bc%98%e6%b7%ab%e5%a8%83%e5%9f%b9%e8%ae%ad%e8%90%a5", "女优淫娃培训营"),
    ("/category/%e6%b7%ab%e6%ac%b2%e6%b8%b8%e6%88%8f%e7%8e%8b", "淫欲游戏王"),
    ("/category/%e5%a4%a7%e9%b8%9f%e5%8d%81%e5%85%ab", "大鸟十八"),
    ("/category/%e4%b9%8c%e6%89%98%e9%82%a6", "乌托邦"),
]

# 热门标签：50 个（来自 /tags，导航里前面带 # 以便和分类区分）
TAGS = [
    ("/tag/%e7%99%bd%e8%99%8e", "白虎"),
    ("/tag/%e5%90%8e%e5%85%a5", "后入"),
    ("/tag/%e5%b0%91%e5%a6%87", "少妇"),
    ("/tag/%e6%97%a0%e5%a5%97", "无套"),
    ("/tag/%e5%8f%a3%e4%ba%a4", "口交"),
    ("/tag/%e4%b9%b1%e4%bc%a6", "乱伦"),
    ("/tag/%e9%bb%91%e4%b8%9d", "黑丝"),
    ("/tag/%e7%97%b4%e5%a5%b3", "痴女"),
    ("/tag/%e7%88%86%e4%b9%b3", "爆乳"),
    ("/tag/%e5%b7%a8%e4%b9%b3", "巨乳"),
    ("/tag/%e9%aa%91%e4%b9%98%e4%bd%8d", "骑乘位"),
    ("/tag/%e4%ba%ba%e5%a6%bb", "人妻"),
    ("/tag/%e7%be%8e%e8%87%80", "美臀"),
    ("/tag/%e6%97%a5%e6%9c%ac", "日本"),
    ("/tag/%e5%86%85%e5%b0%84", "内射"),
    ("/tag/%e5%88%b6%e6%9c%8d", "制服"),
    ("/tag/%e4%b8%9d%e8%a2%9c", "丝袜"),
    ("/tag/%e5%be%a1%e5%a7%90", "御姐"),
    ("/tag/%e7%be%8e%e4%b9%b3", "美乳"),
    ("/tag/%e5%bc%80%e8%a3%86", "开裆"),
    ("/tag/ntr", "NTR"),
    ("/tag/%e7%ba%a6%e7%82%ae", "约炮"),
    ("/tag/%e8%b4%ab%e4%b9%b3", "贫乳"),
    ("/tag/%e8%87%aa%e6%85%b0", "自慰"),
    ("/tag/%e5%a5%b3%e4%bc%98", "女优"),
    ("/tag/%e9%ab%98%e6%bd%ae", "高潮"),
    ("/tag/%e8%b0%83%e6%95%99", "调教"),
    ("/tag/%e4%bc%81%e5%88%92", "企划"),
    ("/tag/%e7%86%9f%e5%a5%b3", "熟女"),
    ("/tag/%e5%85%84%e5%a6%b9", "兄妹"),
    ("/tag/%e5%8f%8d%e5%b7%ae%e5%a9%8a", "反差婊"),
    ("/tag/%e5%88%9b%e6%84%8f", "创意"),
    ("/tag/%e6%b8%85%e7%ba%af", "清纯"),
    ("/tag/%e8%bf%91%e4%ba%b2", "近亲"),
    ("/tag/%e7%be%8e%e5%b0%91%e5%a5%b3", "美少女"),
    ("/tag/ol", "OL"),
    ("/tag/3p", "3P"),
    ("/tag/%e7%99%bd%e4%b8%9d", "白丝"),
    ("/tag/%e5%a5%b3%e6%95%99%e5%b8%88", "女教师"),
    ("/tag/%e5%a7%90%e5%bc%9f", "姐弟"),
    ("/tag/%e5%bc%ba%e5%a5%b8", "强奸"),
    ("/tag/%e8%b6%b3%e4%ba%a4", "足交"),
    ("/tag/%e6%96%91%e6%96%91", "斑斑"),
    ("/tag/%e5%a5%b3%e5%8f%8b", "女友"),
    ("/tag/%e6%96%b0%e4%ba%ba", "新人"),
    ("/tag/%e5%b8%88%e7%94%9f", "师生"),
    ("/tag/%e4%b8%ad%e5%87%ba", "中出"),
    ("/tag/69", "69"),
    ("/tag/%e8%bf%b7%e5%a5%b8", "迷奸"),
    ("/tag/%e5%8f%8c%e9%a9%ac%e5%b0%be", "双马尾"),
]

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

# 列表容器：<div class="excerpts-wrapper"><div class="excerpts">…</div></div>
# 一直啃到 pagination（单页无分页就啃到 </section>），别把侧栏/页脚混进来
_RE_BLOCK_PAG = re.compile(r'<div class="excerpts">(.*?)<div class="pagination"', re.S)
_RE_BLOCK_SEC = re.compile(r'<div class="excerpts">(.*?)</section>', re.S)
_RE_BLOCK_ANY = re.compile(r'<div class="excerpts">(.*)', re.S)
_RE_HAS_NEXT = re.compile(r'class="next-page">\s*<a', re.I)

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
# 抓不到 sitenav 时，退一步全页找分类链接
_RE_ANY_CAT = re.compile(
    r'<a href="([^"]*?/category/[^"]+)"[^>]*>([^<]{1,40})</a>')

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
        self._with_tags = INCLUDE_TAGS
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
        tg = cfg.get("tags")
        if tg is not None:
            self._with_tags = bool(tg)
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

    def _list_block(self, html):
        """只圈出主列表容器，避免侧栏/页脚条目混进来。"""
        if not html:
            return ""
        for rx in (_RE_BLOCK_PAG, _RE_BLOCK_SEC, _RE_BLOCK_ANY):
            m = rx.search(html)
            if m:
                return m.group(1)
        return html

    def _parse_list(self, html):
        """从任意列表页抽条目（分类 / 标签 / 榜单 / 搜索 / 首页 结构一致）。"""
        if not html:
            return []
        block = self._list_block(html)

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

    # ---------- 导航（核心改动） ----------
    def _scrape_nav(self):
        """首页实时抓一遍导航，用来补站方新加的分类；抓不到就返回空。"""
        html = self._http(self.host + "/")
        if not html:
            return []
        navm = _RE_NAV.search(html)
        scope = navm.group(1) if navm else html
        found = _RE_NAV_CAT.findall(scope)
        if not found:
            found = _RE_ANY_CAT.findall(html)

        out = []
        seen = set()
        for href, label in found:
            href = unescape(href).strip()
            if href.startswith("//"):
                href = "https:" + href
            if href.startswith("http"):
                path = href.replace(self.host, "") or "/"
            else:
                path = href if href.startswith("/") else "/" + href
            label = self._clean(label)
            if not label or path in seen:
                continue
            seen.add(path)
            out.append((path, label))
        return out

    def _all_cats(self):
        """导航 = 内置全站（榜单 + 45 分类 + 标签） + 首页实时抓的补漏，带缓存。"""
        if self._cats is not None:
            return self._cats

        cats = [{"type_id": HOME_TID, "type_name": "最新发布"}]
        seen = set([HOME_TID])

        for path, label in list(RANK_PAGES) + list(CATEGORIES):
            if not path or path in seen:
                continue
            seen.add(path)
            cats.append({"type_id": path, "type_name": label})

        # 站方以后新加的分类，照样能自动出现
        for path, label in self._scrape_nav():
            if path in seen:
                continue
            seen.add(path)
            cats.append({"type_id": path, "type_name": label})

        if self._with_tags:
            for path, label in TAGS:
                if path in seen:
                    continue
                seen.add(path)
                cats.append({"type_id": path, "type_name": "#" + label})

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
        if path.startswith("http"):
            path = path.replace(self.host, "") or "/"
        if not path.startswith("/"):
            path = "/" + path

        single = path.rstrip("/") in NO_PAGE_TID
        if pg > 1 and not single:
            path = path.rstrip("/") + "/page/%d/" % pg

        url = self.host + path
        html = self._http(url)
        items = self._parse_list(html)

        if single:
            pagecount = pg
        elif len(items) < PAGE_SIZE:
            pagecount = pg
        elif _RE_HAS_NEXT.search(html or ""):
            pagecount = pg + 1
        else:
            pagecount = pg
        if pagecount < pg:
            pagecount = pg

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

        # 封面优先用主站的（播放域国内直连不稳，走它容易裂图）
        pic = ""
        cm = _RE_COVER.search(html)
        if cm:
            pic = self._big_pic(unescape(cm.group(1)))
        if not pic and hashes and not hashes[0].startswith("http"):
            pic = "%s/videos/%s/poster.jpg" % (self.play_host, hashes[0])

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
        html = self._http(url)
        items = self._parse_list(html)
        if not items and pg == 1 and key:
            # 伪静态搜索兜底（实测 /search/关键词/ 同样可用）
            alt = "%s/search/%s/" % (self.host, quote(key))
            html = self._http(alt)
            items = self._parse_list(html)
        if len(items) < PAGE_SIZE:
            pagecount = pg
        elif _RE_HAS_NEXT.search(html or ""):
            pagecount = pg + 1
        else:
            pagecount = pg
        if pagecount < pg:
            pagecount = pg
        return {
            "list": items,
            "page": pg,
            "pagecount": pagecount,
            "limit": PAGE_SIZE,
            "total": pagecount * PAGE_SIZE,
        }

    # ---------- 播放（核心） ----------
    def _play_header(self):
        if not PLAY_HEADER:
            return ""
        try:
            return json.dumps({"User-Agent": UA, "Referer": self.host + "/"})
        except Exception:
            return ""

    def playerContent(self, flag, id, vipFlags):
        target = str(id or "").strip()

        hashid = ""
        if target.startswith("http"):
            if ".m3u8" in target or ".mp4" in target:
                # 已经是直链，直接丢给播放器
                return {"parse": 0, "playUrl": "", "url": target,
                        "header": self._play_header()}
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
                                "header": self._play_header()}
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
                        "header": self._play_header()}
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

        return {"parse": 0, "playUrl": "", "url": url,
                "header": self._play_header()}
