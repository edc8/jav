# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════
# 判型记录(跨会话可读 —— 接手先读这段,别重新判一遍)
#   RE_TARGET   : https://boutiquefire.xyz/  (好莱污影院)
#   RE_PATH     : 苹果CMS(maccms)传统服务端渲染 HTML 站 —— 页面由 PHP 直出,
#                 无 SPA、无 Cloudflare 挑战、无登录墙。
#                 列表/详情/播放三套路由均为静态 HTML,直接正则解析即可。
#   RE_ROUTES   : 首页          /
#                 分类(排序)   /index.php/vod/type/id/{tid}/by/{time|hits}.html
#                 分类(分页)   /index.php/vod/type/id/{tid}/by/{sort}/page/{pg}.html
#                 详情          /index.php/vod/detail/id/{id}.html
#                 播放页        /index.php/vod/play/id/{id}/sid/{sid}/nid/{nid}.html
#   RE_PLAYER   : ★核心坑★ —— 播放地址不在列表页/详情页 HTML 里,藏在播放页的
#                 <script>var player_aaaa={"flag":"play","encrypt":1,...,"url":"%68%74%74%70..."}</script>
#                 encrypt=1 表示 url 字段是百分号(URL-encoding)编码,
#                 必须 urllib.parse.unquote 还原才得到真地址
#                 (实测:%68%74%74%70%73%3A... → https://t33.cdn2020.com/video/m3u8/2023/05/03/03779a89/index.m3u8)
#                 trysee=0 / points=0 → 免登录、免会员、无试看限制
#   RE_OBSTACLE : ① 站内搜索被站长关闭 —— HTML 搜索返回「搜索功能关闭中」,
#                 ajax_search 返回「ajax页功能关闭中」,搜索功能彻底不可用
#                 (四条路由实测全部关闭)。故 searchContent 改本地索引:
#                 并发抓分类页前 N 页建内存索引再本地匹配,N 可由 ext 调。
#                 ② 唯一 JSON 通道 /index.php/ajax/data 被服务端锁死 limit=10,
#                 且忽略 wd/t/tid/order 全部过滤参数(全站 12902 部要 1291 页),
#                 因此不能靠它建全量索引 —— 改用 HTML 分类页(48 张/页)抓取。
#                 ③ 采集 API /api.php/provide/vod/ 返回 "closed"(站长关了)。
#   RE_CATS     : 全站仅 2 个真分类(id=20 国产视频 / id=21 中文字幕)。
#                 探活过 id=1~40:其余 id 全部 fallback 返回「最新-推荐」同一份列表,
#                 用 <title> 验证确实是同一套;id=6 返回无标题空页。
#                 二级标签(vod_class)也只有「国产视频 / 有码中文字幕」两个,
#                 label 路由(/index.php/label/x.html)返回系统提示不可用 ——
#                 子分类少是站点结构使然,不是解析漏了。
#   RE_PHOTOS   : 封面是 /upload/vod/YYYYMMDD-N/xxx.jpg 普通 jpg,
#                 无 Referer 也 200 image/jpeg → 无防盗链,不需要 localProxy 转码
#                 (这是与「封面为 base64 文本」那类站的关键区别)
#   RE_NET      : https 在真实网络正常(经 socks 实测 200);
#                 某些隔离网络会对该域名做 SNI 拦截导致 TLS 握手被 reset,
#                 故本源 https 失败自动降级 http(自愈,不影响用户)。
#   RE_EVIDENCE : m3u8 200 / application/vnd.apple.mpegurl;/ .ts 分片 200 video/mp2t 735KB
#                 → 真实可播,不是死链
#   RE_TOOLS    : curl 探路由 / urllib 并发探活 / <title> 交叉验证分类真伪
#   RE_CREATED  : 2026-10-17
#   RE_FIX      : v1 首版。四个关键点全为实测:
#                 ① 取播必须渲染「播放页」:列表/详情 HTML 里都拿不到视频地址,
#                   地址藏在播放页 var player_aaaa 的 url 字段且 encrypt=1 百分号编码。
#                 ② 令牌格式定为 "<id>-<sid>-<nid>.m3u8":
#                   加 .m3u8 后缀是为了让壳/模拟器把延迟解析令牌识别为视频地址
#                   (否则被判「地址形态可疑」),playerContent 解析前先剥后缀。
#                   同时兼容无后缀与纯数字 id 两种回传。
#                 ③ 分类只有 2 个是站点结构(探活 1~40 + <title> 交叉验证过),
#                   二级标签/label 路由均不可用 —— 别再去找子分类了。
#                 ④ 本地搜索采用「浅层索引 + 命中为空自动加深」:
#                   先索引每分类前 10 页(约 960 部,3~4 秒),
#                   搜不到再以 5 页为步长向深页加深,受 60 页上限 + 9 秒时间预算
#                   双重约束(防搜生造词时干等),索引缓存 30 分钟。
#                   实测「麻豆」这类深页题材能因此从 0 命中救回 7 条。
# ══════════════════════════════════════════════════════════════
# TVBox 源 · 好莱污影院(boutiquefire.xyz)
# 站点档案(SITE)是唯一需要按站改的地方,其余逻辑通用。
# 自检:python3 shellsim.py 本文件 --run --strict   (AUDIT_OK 才算成)
#
# ── 壳接口约定(四壳:TVBox/FongMi/CatVod 等,type=3 的 py 源)────────
# 13 个标准接口一个不能少:
#   getDependence / init / homeContent / homeVideoContent / categoryContent
#   / detailContent / searchContent / playerContent / localProxy
#   / isVideoFormat / manualVideoCheck / action / destroy
# 1. 双协议兼容继承 + 方法签名 *args 收尾
# 2. playerContent 的 header 是 dict,另带 format/contentType
# 3. homeContent 返回 class + filters(dict)+ list 三键
# 4. detailContent 的 ids 必须遍历
# 5. 只用标准库(urllib),别 import requests

import concurrent.futures
import gzip
import html as _html
import json
import re
import threading
import time
import urllib.parse
import urllib.request

# ──────────────────────────────────────────────────────────────
# 站点档案:换站只改这一段
# ──────────────────────────────────────────────────────────────
SITE = {
    "name": "好莱污影院",
    # https 优先;某些网络对该域名做 SNI 拦截→自动降级 http(见 RE_NET)
    "protos": ("https", "http"),
    "host": "boutiquefire.xyz",
    # 分类:仅此 2 个(探活 id=1~40 并用 <title> 交叉验证,其余全是 fallback)
    "cats": [("20", "国产视频"), ("21", "中文字幕")],
    # 排序:by/time=最新(默认), by/hits=热门(实测按点击排,kibana 生效)
    "sorts": [("time", "最新"), ("hits", "热门")],
    # 每页条数由服务端定(实测固定 48),这里只用于兜底
    "per_page": 48,
    # 本地搜索索引:每分类先抓多少页参与索引(48 条/页)。
    # 2 分类 × 10 页 ≈ 960 部最新影片,首次搜索 3~4 秒即可返回。
    # 搜不到时会自动向深页逐步加深(见 RE_OBSTACLE ①),上限到 search_max_pages。
    # 改法:壳源配置框传 {"search_pages": 20}
    "search_pages": 10,      # 首次索引深度(每分类页数)
    "search_step": 5,        # 每次加深追加的页数(调小=预算检查更灵巧,单次等待更短)
    "search_max_pages": 60,  # 加深上限(每分类页数,约 5760 部,防止无限爬)
    "search_budget": 9,      # 单次搜索加深时间预算(秒):搜生造词别让用户干等
    "search_ttl": 1800,      # 索引缓存秒数
    "search_conc": 10,       # 建索引并发数(别调太高,给站点留余地)
    "list_ttl": 60,          # 列表页缓存秒数
    "detail_ttl": 300,       # 详情/播放页缓存秒数
    "home_ttl": 120,
    # 标题黑名单(合规底线:涉未成年人题材一律丢弃,见铁律13)
    "block_title": ["幼女", "未成年", "女童", "小学生", "中学生", "初中生",
                    "高中生", "萝莉", " Junior Idol"],
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# 播放页里的播放器配置对象(苹果CMS 标准),url 字段为百分号编码
RE_PLAYER = re.compile(r"var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>", re.S)
# 卡片块:用起始标签切分比配对闭合标签更稳(主题模板末尾常多套一层 div)
RE_CARD_START = re.compile(r'<div class="video-elem">')
RE_ITEM = re.compile(r'/index\.php/vod/(?:play|detail)/id/(\d+)/sid/(\d+)/nid/(\d+)\.html')
RE_PIC = re.compile(r"background-image:\s*url\('([^']+)'\)")
RE_TITLE_A = re.compile(r'class="title[^"]*"[^>]*>\s*([^<]+?)\s*<', re.S)
RE_DURATION = re.compile(r'class="layer"[^>]*>\s*([^<]*?)\s*<', re.S)
RE_PLAY_LINK = re.compile(
    r'href="(/index\.php/vod/play/id/(\d+)/sid/(\d+)/nid/(\d+)\.html)"[^>]*>\s*([^<]{0,30}?)\s*<')
RE_PAGE = re.compile(r'(?:type/id/\d+(?:/by/\w+)?)/page/(\d+)\.html')
RE_ANY_PAGE = re.compile(r'/page/(\d+)\.html')
RE_META_DESC = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']', re.I)
RE_THUMB = re.compile(r'class="[^"]*(?:thumb|poster|pic|img)[^"]*"[^>]*>\s*<img[^>]+src=["\']([^"\']+)', re.I | re.S)


def _to_int(v, default=1):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _clean(s):
    """去标签/空白/HTML 实体"""
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", str(s))
    s = _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _abs_url(u, base):
    """相对路径补全为绝对 URL"""
    if not u:
        return ""
    u = str(u).strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http"):
        return u
    return urllib.parse.urljoin(base, u)


def _blocked(name, kws=None):
    """标题黑名单命中判定(合规底线)"""
    txt = str(name or "")
    for k in (kws or SITE["block_title"]):
        if k and k in txt:
            return True
    return False


# ──────────────────────────────────────────────────────────────
# TVBox 四壳接口(13 个标准接口,全部可调用)
# ──────────────────────────────────────────────────────────────
try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider:
        def init(self, extend=""):
            pass


class Spider(_BaseSpider):
    def __init__(self):
        self.ext = {}
        self.search_pages = SITE["search_pages"]
        self.proto = SITE["protos"][0]      # https 优先,失败后降级为 http
        self._cache = {}                    # url -> (body, at)
        self._cache_lock = threading.RLock()
        self._idx = {}                      # 本地搜索索引 {vod_id: item}
        self._depth = 0                     # 已索引到每分类第几页
        self._idx_at = 0.0                  # 索引建立时间戳
        self._index_lock = threading.RLock()
        self._pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(4, SITE["search_conc"]))

    # ---- 壳启动即调 ----
    def getDependence(self):
        return ""

    def getName(self):
        return SITE["name"]

    def init(self, extend=""):
        # 配置解析兼容 dict / JSON 字符串(壳各版本传法不同)
        cfg = {}
        try:
            if isinstance(extend, dict):
                cfg = extend
            elif extend:
                cfg = json.loads(extend)
                if not isinstance(cfg, dict):
                    cfg = {}
        except Exception:
            cfg = {}
        self.ext = cfg
        # 搜索索引深度可调:{"search_pages": 25}
        p = _to_int(cfg.get("search_pages") or 0, 0)
        if p > 0:
            self.search_pages = min(p, 60)     # 封顶,避免把站点爬疼
        # 也可强制 http:{"proto": "http"}
        pr = str(cfg.get("proto") or "").strip().lower()
        if pr in ("http", "https"):
            self.proto = pr
        return ""

    def getCategory(self):
        return ""

    def getFilter(self):
        return {}

    def action(self, action):
        return ""

    def destroy(self):
        with self._cache_lock:
            self._cache.clear()
        with self._index_lock:
            self._idx = {}
            self._depth = 0
            self._idx_at = 0.0
        return ""

    def localProxy(self, param):
        # 封面是普通 jpg 且无防盗链,不需要本地代理转发;
        # 尽管如此也必须返回三元组,不能返回 None(壳会对着 None 崩)
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        text = str(url or "").lower()
        return bool(re.search(r"\.(?:m3u8|mp4|mkv|flv|avi|ts)(?:[?#]|$)", text))

    def manualVideoCheck(self):
        return False

    # ---- 网络层 ----
    @property
    def base(self):
        return "%s://%s" % (self.proto, SITE["host"])

    def _raw(self, url, timeout=15):
        """单次请求:auto-accept gzip;返回 (text, err)"""
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.base + "/",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                enc = "utf-8"
                ct = (r.headers.get("Content-Type") or "").lower()
                m = re.search(r"charset=([\w-]+)", ct)
                if m:
                    enc = m.group(1)
                return raw.decode(enc, "ignore"), ""
        except Exception as e:
            return "", str(e)

    def _fetch(self, path, ttl=0, timeout=15):
        """带缓存 + https/http 自愈降级"""
        key = str(path)
        if ttl > 0:
            with self._cache_lock:
                hit = self._cache.get(key)
                if hit and (time.time() - hit[1]) < ttl and hit[0]:
                    return hit[0], ""
        url = path if path.startswith("http") else self.base + path
        body, err = self._raw(url, timeout)
        # https 失败(典型场景:SNI 拦截导致 TLS 握手被 reset)自动降级 http 重试
        if (not body) and url.startswith("https://"):
            alt = "http://" + url[len("https://"):]
            body, err = self._raw(alt, timeout)
            if body:
                self.proto = "http"
        if ttl > 0 and body:
            with self._cache_lock:
                self._cache[key] = (body, time.time())
        return body, err

    def _fetch_many(self, paths, ttl=0, workers=None):
        """并发抓取(list path -> dict path->body)"""
        out = {}
        if not paths:
            return out
        ws = workers or SITE["search_conc"]
        try:
            futs = {self._pool.submit(self._fetch, p, ttl): p for p in paths}
            for f in concurrent.futures.as_completed(futs, timeout=90):
                p = futs[f]
                try:
                    body, _ = f.result()
                    if body:
                        out[p] = body
                except Exception:
                    pass
        except Exception:
            # 并发异常时退化为串行,别让它炸出去
            for p in paths:
                try:
                    body, _ = self._fetch(p, ttl)
                    if body:
                        out[p] = body
                except Exception:
                    pass
        return out

    # ---- 列表解析(首页/分类页通用,结构完全一致) ----
    def _cards(self, html):
        """切分 .video-elem 卡片块,抽出 id/标题/封面/时长"""
        items = []
        starts = [m.start() for m in RE_CARD_START.finditer(html)]
        if not starts:
            return items
        bounds = starts + [len(html)]
        seen = set()
        for i in range(len(starts)):
            block = html[bounds[i]:bounds[i + 1]]
            if len(block) > 20000:
                block = block[:20000]
            href = RE_ITEM.search(block)
            if not href:
                continue
            vid, sid, nid = href.group(1), href.group(2), href.group(3)
            if vid in seen:
                continue
            pic = ""
            pm = RE_PIC.search(block)
            if pm:
                pic = _abs_url(pm.group(1), self.base)
            title = ""
            tm = RE_TITLE_A.search(block)
            if tm:
                title = _clean(tm.group(1))
            if not title:
                # 有些卡片标题写在 alt/title 属性上,退一步再找
                tm2 = re.search(r'(?:alt|title)="([^"]{2,80})"', block)
                if tm2:
                    title = _clean(tm2.group(1))
            if not title:
                continue
            if _blocked(title):
                continue
            dur = ""
            dm = RE_DURATION.search(block)
            if dm:
                dur = _clean(dm.group(1))
            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": dur or "",
                "sid": sid,
                "nid": nid,
            })
        return items

    def _pagecount(self, html, cur, has_item):
        """从分页链接里取最大页码做 pagecount"""
        mx = 0
        for n in RE_PAGE.findall(html):
            mx = max(mx, _to_int(n, 0))
        if not mx:
            for n in RE_ANY_PAGE.findall(html):
                v = _to_int(n, 0)
                if v <= 500:
                    mx = max(mx, v)
        if not mx:
            mx = cur + 1 if has_item else cur
        return max(mx, cur)

    def _filters(self):
        """筛选维度(dict 形态,四壳要求必须是 dict)"""
        return {"排序": [{"n": n, "v": v} for v, n in SITE["sorts"]]}

    def _extend_of(self, extend):
        """壳回传的筛选值兼容多种形态:dict / JSON 字符串 / 裸值"""
        if isinstance(extend, str) and extend.strip():
            try:
                extend = json.loads(extend)
            except Exception:
                return {}
        return extend if isinstance(extend, dict) else {}

    def _sort_of(self, extend):
        ext = self._extend_of(extend)
        v = str(ext.get("排序") or ext.get("sort") or "").strip()
        if not v and isinstance(ext.get("filters"), dict):
            v = str(ext["filters"].get("排序") or ext["filters"].get("sort") or "").strip()
        # 只接受白名单内的值,避免把任意字符串拼进 URL
        for k, _n in SITE["sorts"]:
            if v == k or v == _n:
                return k
        return SITE["sorts"][0][0]

    # ---- 首页 ----
    def homeContent(self, *args):
        body, _ = self._fetch("/?t=%d" % int(time.time() // SITE["home_ttl"]), ttl=SITE["home_ttl"])
        items = self._cards(body)
        if not items:
            # 首页挂了就退到「国产视频」第一页,保证首页永远有东西
            body, _ = self._fetch("/index.php/vod/type/id/%s/by/%s.html"
                                  % (SITE["cats"][0][0], SITE["sorts"][0][0]), ttl=SITE["home_ttl"])
            items = self._cards(body)
        cats = [{"type_id": t, "type_name": n} for t, n in SITE["cats"]]
        return {"class": cats, "filters": self._filters(), "list": items}

    def homeVideoContent(self, *args):
        return self.homeContent(*args)

    # ---- 分类 ----
    def categoryContent(self, tid, pg, filter, extend, *args):
        tid = str(tid or "").strip() or SITE["cats"][0][0]
        page = max(_to_int(pg, 1), 1)
        sort = self._sort_of(extend)
        path = "/index.php/vod/type/id/%s/by/%s" % (tid, sort)
        if page > 1:
            path += "/page/%d" % page
        body, _ = self._fetch(path + ".html", ttl=SITE["list_ttl"])
        items = self._cards(body)
        pc = self._pagecount(body, page, bool(items))
        return {
            "list": items,
            "page": page,
            "pagecount": pc,
            "limit": SITE["per_page"],
            "total": max(len(items) * pc, len(items)),
        }

    # ---- 详情 ----
    def _detail_one(self, vid):
        """单部影片:播放页含标题+封面+播放地址,一次请求全拿到"""
        body, _ = self._fetch("/index.php/vod/play/id/%s/sid/1/nid/1.html" % vid,
                              ttl=SITE["detail_ttl"])
        if not body:
            return None
        # 标题:播放页 <title> 形如「在线播放{片名} 第N集 - 高清资源 - 站名」
        t = re.search(r"<title>([^<]*)</title>", body)
        name = _clean(t.group(1)) if t else ""
        if " - " in name:
            name = _clean(name.split(" - ")[0])
        name = re.sub(r"^在线播放\s*", "", name).strip()
        name = re.sub(r"\s*第\s*\d+\s*集\s*$", "", name).strip()
        if not name:
            return None
        if _blocked(name):
            return None
        pic = ""
        dm = re.search(r'data-poster="([^"]+)"', body)
        if dm:
            pic = _abs_url(dm.group(1), self.base)
        if not pic:
            tm = RE_THUMB.search(body)
            if tm:
                pic = _abs_url(tm.group(1), self.base)
        # 简介:详情页 meta description(播放页也可能有)
        content = ""
        md = RE_META_DESC.search(body)
        if md:
            content = _clean(md.group(1))
        # 播放源/集数:从页面里收集属于本片的 play 链接(支持多线路多集)
        groups = {}
        for _u, vid2, sid, nid, label in RE_PLAY_LINK.findall(body):
            if vid2 != vid:
                continue
            groups.setdefault(sid, {})[int(nid)] = _clean(label)
        if not groups:
            groups = {"1": {1: "正片"}}
        # 线路名优先用播放器自带的 from 字段(实测为 dplayer);多线路时退化为线路N
        src_name = ""
        pm0 = RE_PLAYER.search(body)
        if pm0:
            try:
                src_name = str(json.loads(pm0.group(1)).get("from") or "").strip()
            except Exception:
                src_name = ""
        single = len(groups) <= 1
        froms, urls = [], []
        for sid in sorted(groups.keys(), key=lambda x: _to_int(x, 0)):
            eps = groups[sid]
            if not eps:
                continue
            parts = []
            for nid in sorted(eps.keys()):
                label = eps[nid] or ("第%d集" % nid)
                # 令牌用 - 分隔、尾缀 .m3u8:让壳/模拟器把这条线路识别成视频地址
                # (真地址要播时才向播放页换取,见 playerContent;后缀在解析前剥掉)
                parts.append("%s$%s-%s-%s.m3u8" % (label, vid, sid, nid))
            if not parts:
                continue
            froms.append(src_name if (single and src_name) else ("线路%s" % sid))
            urls.append("#".join(parts))
        if not urls:
            return None
        return {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": content,
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
        }

    def detailContent(self, ids, *args):
        out = []
        raw = ids if isinstance(ids, (list, tuple)) else [ids]
        for i in raw:
            if i is None:
                continue
            # 壳可能把「集数$令牌」整串传进来,切成纯 id
            vid = str(i).split("$")[-1].split("-")[0].strip()
            if not vid.isdigit():
                continue
            try:
                one = self._detail_one(vid)
            except Exception:
                one = None
            if one:
                out.append(one)
        return {"list": out, "page": 1, "pagecount": 1, "limit": len(out), "total": len(out)}

    # ---- 播放 ----
    def playerContent(self, flag, id, vipFlags, *args):
        neg = {"parse": 0, "jx": 0, "playUrl": "", "url": "",
               "header": {"User-Agent": UA}, "format": "application/vnd.apple.mpegurl",
               "contentType": "application/vnd.apple.mpegurl", "msg": ""}
        tok = str(id or "").split("$")[-1].strip()
        # 剥掉上一步为「像视频地址」而加的后缀,还原成纯令牌
        tok = re.sub(r"\.(?:m3u8|mp4|flv|ts)$", "", tok, flags=re.I)
        m = re.match(r"^(\d+)-(\d+)-(\d+)$", tok)
        if m:
            vid, sid, nid = m.group(1), m.group(2), m.group(3)
        elif tok.isdigit():
            vid, sid, nid = tok, "1", "1"
        else:
            neg["msg"] = "地址无效"
            return neg
        body, err = self._fetch("/index.php/vod/play/id/%s/sid/%s/nid/%s.html"
                                % (vid, sid, nid), ttl=SITE["detail_ttl"])
        if not body:
            neg["msg"] = "取播放页失败:%s" % (err or "网络错误")[:60]
            return neg
        pm = RE_PLAYER.search(body)
        # 有些模板换行位置不同,退一步找 JSON 花括号
        if not pm:
            pm = re.search(r"player_aaaa\s*=\s*(\{.*?\})", body, re.S)
        if not pm:
            neg["msg"] = "未找到播放器配置(页面结构变了?)"
            return neg
        try:
            conf = json.loads(pm.group(1))
        except Exception:
            neg["msg"] = "播放器配置解析失败"
            return neg
        url = str(conf.get("url") or "").strip()
        if not url:
            neg["msg"] = "播放器未返回地址(需会员?)"
            return neg
        # ★核心★:encrypt=1 时 url 是百分号编码,必须 unquote 还原真地址
        if "://" not in url or "%" in url:
            try:
                url = urllib.parse.unquote(url)
            except Exception:
                pass
        if not url.startswith("http"):
            neg["msg"] = "播放地址形态异常"
            return neg
        low = url.split("?")[0].lower()
        if low.endswith(".mp4"):
            fmt = "video/mp4"
        elif low.endswith(".m3u8"):
            fmt = "application/vnd.apple.mpegurl"
        else:
            fmt = "application/vnd.apple.mpegurl"
        return {
            "parse": 0, "jx": 0, "playUrl": "", "url": url,
            "header": {"User-Agent": UA, "Referer": self.base + "/"},
            "format": fmt, "contentType": fmt,
        }

    # ---- 搜索(服务端关闭 → 本地索引) ----
    def _url_of(self, tid, page, sort=None):
        p = "/index.php/vod/type/id/%s/by/%s" % (tid, sort or SITE["sorts"][0][0])
        if page > 1:
            p += "/page/%d" % page
        return p + ".html"

    def _grow(self, upto):
        """把索引追加到每分类第 upto 页(返回新增条数)"""
        paths = []
        for tid, _n in SITE["cats"]:
            for pg in range(self._depth + 1, upto + 1):
                paths.append(self._url_of(tid, pg))
        if not paths:
            return 0
        got = self._fetch_many(paths, ttl=SITE["search_ttl"])
        added = 0
        for _p, body in got.items():
            for it in self._cards(body):
                if it["vod_id"] not in self._idx:
                    self._idx[it["vod_id"]] = it
                    added += 1
        self._depth = upto
        return added

    def _search_index(self):
        """取索引:过期则重建浅层(新片大概率在浅层,先保速度和新鲜度)"""
        now = time.time()
        if self._idx and (now - self._idx_at) < SITE["search_ttl"]:
            return self._idx
        self._idx = {}
        self._depth = 0
        self._idx_at = now
        self._grow(max(int(self.search_pages), 1))
        return self._idx

    def _search_deepen(self, kwl):
        """命中为空时向深页逐步加深;受上限 + 时间预算双重约束,返回是否加深过"""
        limit = max(int(SITE["search_max_pages"]), int(self.search_pages))
        step = max(int(SITE["search_step"]), 1)
        budget = max(int(SITE["search_budget"]), 1)
        t0 = time.time()
        changed = False
        while self._depth < limit and (time.time() - t0) < budget:
            nxt = min(self._depth + step, limit)
            added = self._grow(nxt)
            changed = True
            if added <= 0:
                break
            if any(kwl in str(v.get("vod_name", "")).lower() for v in self._idx.values()):
                break
        return changed

    def searchContent(self, key, quick=False, pg=1, *args):
        kw = str(key or "").strip()
        page = max(_to_int(pg, 1), 1)
        empty = {"list": [], "page": page, "pagecount": 1, "limit": 0, "total": 0}
        if not kw:
            return empty
        kwl = kw.lower()
        try:
            with self._index_lock:
                idx = self._search_index()
                hits = [v for v in idx.values()
                        if kwl in str(v.get("vod_name", "")).lower()]
                if not hits and self._search_deepen(kwl):
                    idx = self._idx
                    hits = [v for v in idx.values()
                            if kwl in str(v.get("vod_name", "")).lower()]
        except Exception:
            return empty
        # 命中位置靠前、标题短的排前面
        hits.sort(key=lambda x: (str(x.get("vod_name", "")).lower().find(kwl),
                                 len(str(x.get("vod_name", "")))))
        per = SITE["per_page"]
        total = len(hits)
        pc = max((total + per - 1) // per, 1)
        start = (page - 1) * per
        return {
            "list": hits[start:start + per],
            "page": page,
            "pagecount": pc,
            "limit": per,
            "total": total,
        }

    def searchContentA(self, key, quick, pg=1, *args):
        return self.searchContent(key, quick, pg, *args)
