# coding=utf-8
# -*- coding: utf-8 -*-
"""
vjav.com -> TVBox / 影视仓 / fongmi 单文件 py 源

零第三方依赖：只用 Python 标准库（内核精简环境无 pip，第三方库会
直接 No module named，所以这里不碰 requests / pyquery / lxml）。

接入方式：配置 JSON 里 type 填 3，api 指向本文件直链。

换站：只改下面 HOST 一行（也可以在 extend 里传 {"host": "https://xxx"} 覆盖）。
业务逻辑与站点结构解耦，站点改版时只需要动 _parse_list / _parse_detail。
"""

import sys
import json
import re
import ssl
import gzip
import urllib.request
import urllib.parse
import urllib.error

sys.path.append('..')
from base.spider import Spider


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """禁止自动跟随 302，用来自取 CDN 重定向地址。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Spider(Spider):

    # ==================================================================
    # 站点配置（换站唯一要改的地方）
    # ==================================================================
    HOST = "https://vjav.com"
    API = "/api/json/videos2"
    VIDEOfILE = "/api/videofile.php"
    SEARCH_API = "/api/videos2.php"
    CAT_API = "/api/json/categories/14400/str.all.en.json"

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    COUNT = 60          # 每页条数（站点上限 60）
    TIMEOUT = 15

    # 站点把播放路径做了 base64 变体编码，字母表里混了 5 个西里尔同形字
    # (А В С Е М) 来防止被直接识别成 base64。照抄，别手打。
    ALPHA = ("\u0410\u0412\u0421D\u0415FGHIJKL\u041cNOPQRSTUVWXYZ"
             "abcdefghijklmnopqrstuvwxyz0123456789.,~")

    SORTS = [
        ("latest-updates", "最新"),
        ("most-popular", "最热"),
        ("top-rated", "评分"),
        ("most-commented", "评论"),
        ("longest", "最长"),
    ]

    DEFAULT_CATS = [
        ("japanese", "日本"), ("asian", "亚洲"), ("hd", "高清"),
        ("jav-censored", "有码"), ("jav-uncensored", "无码"),
        ("brunette", "黑发"), ("blonde", "金发"), ("big-tits", "巨乳"),
        ("amateur", "素人"), ("milf", "熟女"), ("vr", "VR"),
    ]

    CAT_CN = {
        "asian": "亚洲", "japanese": "日本", "hd": "高清",
        "jav-censored": "有码", "jav-uncensored": "无码", "uncensored": "无码",
        "brunette": "黑发", "blonde": "金发", "big-tits": "巨乳",
        "amateur": "素人", "milf": "熟女", "vr": "VR",
        "jav-idols": "JAV女优", "party": "派对", "cuckold": "绿帽",
        "lesbian": "女同", "threesome": "3P", "anal": "肛",
        "creampie": "中出", "school-girl": "学生", "nurse": "护士",
        "office-lady": "OL", "teacher": "教师", "housewife": "人妻",
        "swimsuit": "泳装", "cosplay": "COS", "massage": "按摩",
        "pov": "第一人称", "4k": "4K", "hd-1080p": "1080P",
        "small-tits": "贫乳", "mature": "成熟", "gangbang": "多P",
        "bdsm": "调教", "public": "户外", "office": "办公室",
        "outdoor": "野外", "toys": "道具", "masturbation": "自慰",
        "squirt": "潮吹", "footjob": "足交", "handjob": "手交",
        "blowjob": "口交", "deepthroat": "深喉", "piss": "放尿",
        "lingerie": "内衣", "stockings": "丝袜", "glasses": "眼镜",
    }

    # ==================================================================
    # 生命周期
    # ==================================================================

    def getName(self):
        return "vjav"

    def init(self, extend=""):
        self._cats = None
        self._last_error = ""
        try:
            if extend:
                cfg = extend if isinstance(extend, dict) else json.loads(extend)
                host = (cfg.get("host") or "").strip()
                if host:
                    if not host.startswith("http"):
                        host = "https://" + host
                    self.HOST = host.rstrip("/")
        except Exception:
            pass
        return self

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return None

    # ==================================================================
    # HTTP（标准库实现，接口与 requests 的常用子集对齐）
    # ==================================================================

    def _headers(self, referer=None, ajax=True):
        h = {
            "User-Agent": self.UA,
            "Referer": referer or (self.HOST + "/"),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip",
        }
        if ajax:
            h["X-Requested-With"] = "XMLHttpRequest"
        return h

    def _open(self, url, headers=None, timeout=None):
        req = urllib.request.Request(url, headers=headers or self._headers())
        t = timeout or self.TIMEOUT
        try:
            return urllib.request.urlopen(req, timeout=t)
        except ssl.SSLError:
            # 部分内核的 Python 缺根证书，降级到不校验（目标站固定，风险可控）
            ctx = ssl._create_unverified_context()
            req2 = urllib.request.Request(url, headers=headers or self._headers())
            return urllib.request.urlopen(req2, timeout=t, context=ctx)

    def _get(self, url, referer=None, timeout=None):
        """GET 取文本。失败返回空串，并把原因记在 self._last_error。"""
        try:
            resp = self._open(url, self._headers(referer), timeout)
            raw = resp.read()
            if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            self._last_error = "HTTP %s %s" % (e.code, url)
        except Exception as e:
            self._last_error = "%s %s" % (e.__class__.__name__, url)
        return ""

    def _get_json(self, url, referer=None):
        txt = self._get(url, referer)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            self._last_error = "bad json %s" % url
            return None

    def _resolve_cdn(self, url):
        """跟着 302 拿最终 CDN 直链；拿不到就返回空，由调用方回退原址。"""
        hdr = self._headers()
        hdr["Range"] = "bytes=0-0"
        try:
            op = urllib.request.build_opener(_NoRedirect())
            req = urllib.request.Request(url, headers=hdr)
            try:
                resp = op.open(req, timeout=self.TIMEOUT)
                loc = resp.headers.get("Location")
                if loc:
                    return urllib.parse.urljoin(url, loc)
                return resp.geturl()
            except urllib.error.HTTPError as e:
                loc = e.headers.get("Location") if e.headers else None
                if loc:
                    return urllib.parse.urljoin(url, loc)
        except Exception:
            pass
        return ""

    # ==================================================================
    # 播放地址解码（站点自定义 base64 变体）
    # ==================================================================

    def _vb64(self, s):
        if not s:
            return ""
        table = self.ALPHA
        s = re.sub(r"[^\u0410\u0412\u0421\u0415\u041cA-Za-z0-9.,~]", "", s)
        out = []
        i = 0
        n = len(s)
        while i < n:
            c0 = table.find(s[i]); i += 1
            c1 = table.find(s[i]) if i < n else 64; i += 1
            c2 = table.find(s[i]) if i < n else 64; i += 1
            c3 = table.find(s[i]) if i < n else 64; i += 1
            if c0 < 0:
                c0 = 0
            if c1 < 0:
                c1 = 0
            b1 = ((c0 << 2) | (c1 >> 4)) & 0xFF
            b2 = (((c1 & 15) << 4) | ((c2 if c2 > 0 else 0) >> 2)) & 0xFF
            b3 = (((c2 if c2 > 0 else 0) & 3) << 6 | (c3 if c3 > 0 else 0)) & 0xFF
            out.append(b1)
            if c2 != 64:
                out.append(b2)
            if c3 != 64:
                out.append(b3)
        try:
            raw = bytes(out).decode("latin-1")
        except Exception:
            return ""
        return urllib.parse.unquote(raw, encoding="latin-1")

    # ==================================================================
    # 数据映射
    # ==================================================================

    def _abs_pic(self, u):
        if not u:
            return ""
        u = str(u).strip().strip('"').strip("'")
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return self.HOST + u
        return u

    def _vod(self, v):
        vid = str(v.get("video_id") or "").strip()
        title = (v.get("title") or v.get("title_jp") or vid).strip()
        pic = self._abs_pic(v.get("scr") or v.get("thumb") or v.get("thumbsrc"))
        dur = str(v.get("duration") or "").strip()
        views = str(v.get("video_viewed") or "").strip()
        remark = dur
        if views.isdigit() and int(views) > 0:
            remark = ("%s · %s" % (dur, self._fmt_num(int(views)))).strip(" ·")
        return {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": remark,
        }

    @staticmethod
    def _fmt_num(n):
        if n >= 100000000:
            return "%.1f亿次" % (n / 100000000.0)
        if n >= 10000:
            return "%.1f万次" % (n / 10000.0)
        return "%d次" % n

    def _paged(self, data, pg):
        vids = (data or {}).get("videos") or []
        total = 0
        pages = 0
        try:
            total = int(data.get("total_count") or 0)
        except Exception:
            total = 0
        try:
            pages = int(data.get("pages") or 0)
        except Exception:
            pages = 0
        if not pages and vids:
            pages = pg if len(vids) >= self.COUNT else pg
        return {
            "list": [self._vod(v) for v in vids if v.get("video_id")],
            "page": pg,
            "pagecount": pages,
            "limit": self.COUNT,
            "total": total,
        }

    def _load_cats(self):
        if self._cats is not None:
            return self._cats
        cats = []
        data = self._get_json(self.HOST + self.CAT_API)
        for c in ((data or {}).get("categories") or []):
            d = (c.get("dir") or "").strip()
            t = (c.get("title") or "").strip()
            if not d:
                continue
            name = self.CAT_CN.get(d.lower(), t or d)
            cats.append({"type_id": "cat:" + d, "type_name": name})
            if len(cats) >= 30:
                break
        if not cats:
            cats = [{"type_id": "cat:" + d, "type_name": n}
                    for d, n in self.DEFAULT_CATS]
        self._cats = cats
        return cats

    def _sort_filter(self):
        return [{
            "key": "sort",
            "name": "排序",
            "value": [{"n": n, "v": v} for v, n in self.SORTS],
        }]

    # ==================================================================
    # 内核接口
    # ==================================================================

    def homeContent(self, filter):
        classes = [{"type_id": "sort:" + v, "type_name": n}
                   for v, n in
                   [("latest-updates", "最新更新"),
                    ("most-popular", "最热"),
                    ("top-rated", "评分最高"),
                    ("most-commented", "评论最多"),
                    ("longest", "时长最长")]]
        classes += self._load_cats()
        filters = {}
        for c in classes:
            if c["type_id"].startswith("cat:"):
                filters[c["type_id"]] = self._sort_filter()
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        res = self.categoryContent("sort:latest-updates", 1, None, None)
        return {"list": res.get("list") or []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1

        tid = str(tid or "")
        sort = "latest-updates"
        section = ""
        object_id = ""

        if tid.startswith("sort:"):
            sort = tid[5:] or sort
        elif tid.startswith("cat:"):
            section = "categories"
            object_id = tid[4:]
        elif tid.isdigit():
            section = "categories"
            object_id = tid
        elif tid:
            section = "categories"
            object_id = tid

        if isinstance(extend, str) and extend:
            try:
                extend = json.loads(extend)
            except Exception:
                extend = None
        if isinstance(extend, dict):
            s = (extend.get("sort") or "").strip()
            if s:
                sort = s

        url = "%s%s/86400/str/%s/%d/%s.%s.%d.all...json" % (
            self.HOST, self.API, sort, self.COUNT, section, object_id, pg)
        data = self._get_json(url)
        if data is None:
            return {"list": [], "page": pg, "pagecount": pg,
                    "limit": self.COUNT, "total": 0}
        return self._paged(data, pg)

    def searchContent(self, key, quick, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        kw = urllib.parse.quote(str(key or ""), safe="")
        params = "86400/str/relevance/%d/search..%d.all..." % (self.COUNT, pg)
        url = "%s%s?params=%s&s=%s" % (self.HOST, self.SEARCH_API, params, kw)
        data = self._get_json(url)
        if data is None:
            return {"list": [], "page": pg, "pagecount": pg,
                    "limit": self.COUNT, "total": 0}
        return self._paged(data, pg)

    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0]) if ids else ""
        else:
            vid = str(ids or "")
        vid = re.sub(r"[^0-9]", "", vid)
        if not vid:
            return {"list": []}

        v = {}
        try:
            n = int(vid)
        except Exception:
            n = 0
        url = "%s/api/json/video/86400/%d/%d/%s.json" % (
            self.HOST, 1000000 * (n // 1000000), 1000 * (n // 1000), vid)
        data = self._get_json(url)
        if data and isinstance(data.get("video"), dict):
            v = data["video"]

        title = (v.get("title") or v.get("title_jp") or vid).strip()
        pic = self._abs_pic(v.get("thumbsrc") or v.get("thumb") or "")
        desc = (v.get("description") or "").strip()

        cats = v.get("categories") or {}
        cat_names = []
        if isinstance(cats, dict):
            for item in cats.values():
                if isinstance(item, dict) and item.get("title"):
                    cat_names.append(str(item["title"]))
        st = v.get("statistics") or {}
        lines = []
        if desc:
            lines.append(desc)
        if cat_names:
            lines.append("分类: " + " / ".join(cat_names))
        if st:
            seen = st.get("viewed") or st.get("viewed_count")
            if seen:
                lines.append("观看: " + str(seen))
            lk = st.get("likes")
            if lk:
                lines.append("点赞: %s  收藏: %s" % (lk, st.get("dislikes") or 0))
        usr = v.get("user") or {}
        if usr.get("username"):
            lines.append("上传: " + str(usr["username"]))
        if v.get("post_date"):
            lines.append("发布: " + str(v["post_date"]))

        play_url = "正片$" + vid
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_year": str(v.get("post_date") or "")[:4],
                "vod_area": "JP",
                "vod_remarks": str(v.get("duration") or ""),
                "vod_actor": str(v.get("models") or ""),
                "vod_content": "\n".join(lines) if lines else title,
                "vod_play_from": "vjav",
                "vod_play_url": play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        header = {
            "User-Agent": self.UA,
            "Referer": self.HOST + "/",
        }
        raw_id = str(id or "").strip()

        # 已经是直链就直接放行
        if raw_id.startswith("http"):
            return {"parse": 0, "playUrl": raw_id, "header": header,
                    "url": raw_id}

        vid = re.sub(r"[^0-9]", "", raw_id)
        if not vid:
            return {"parse": 0, "playUrl": "", "header": header,
                    "msg": "invalid video id: " + raw_id}

        url = "%s%s?video_id=%s&lifetime=86400000" % (
            self.HOST, self.VIDEOfILE, vid)
        data = self._get_json(url, referer=self.HOST + "/videos/" + vid + "/")

        candidates = []
        if isinstance(data, list):
            for it in data:
                if not isinstance(it, dict):
                    continue
                path = self._vb64(it.get("video_url") or "")
                if not path:
                    continue
                if path.startswith("http"):
                    full = path
                elif path.startswith("/"):
                    full = self.HOST + path
                else:
                    full = self.HOST + "/" + path
                fmt = str(it.get("format") or "")
                hq = 0 if ("_hq" in fmt or it.get("is_default")) else 1
                candidates.append((hq, full))

        if not candidates:
            return {"parse": 0, "playUrl": "", "header": header,
                    "msg": self._last_error or "no playable source"}

        candidates.sort(key=lambda x: x[0])
        play = candidates[0][1]

        # 先跟一次 302 拿 CDN 直链，拿不到就交原址让播放器自己跳
        cdn = self._resolve_cdn(play)
        final = cdn or play

        return {
            "parse": 0,
            "playUrl": final,
            "url": final,
            "header": header,
        }
