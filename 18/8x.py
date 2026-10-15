# -*- coding: utf-8 -*-
# 8x8x · TVBox Python 爬虫源（零依赖改写版）
# ──────────────────────────────────────────────────────
# 本版基于原脚本逻辑改写，与原版业务逻辑一致，只动了下面这几处：
#   1. 去掉第三方依赖 curl_cffi / requests —— 内核里没有 pip，装不上，
#      原版走到第二步就 No module named。改用标准库 urllib 实现，
#      同时保留「内核里要是有 curl_cffi 就优先用它」的自动探测（有则用、无则不报错）。
#   2. 域名改成明文常量 HOST，换站只改一行，不用再去解十六进制数组。
#   3. body path 动态发现逻辑保留，匹配规则放宽（原版只认 app.[hash].js，
#      现在 index-xxx.js 之类也能认），失败照样回落默认值。
#   4. 卡片/标签正则放宽引号与属性顺序，避免源站改版后静默返回空列表。
#   5. 补 strip 引号：原版 data-src / data-poster 抠出来可能带引号，会导致封面裂图。

import sys
import re
import json
import gzip
import ssl
import base64
import urllib.request
import urllib.error
from urllib.parse import quote

try:
    sys.path.append('..')
    from base.spider import Spider as _Base
except ImportError:
    # 兜底：内核没提供 base 包时也能 import 成功
    class _Base(object):
        def __init__(self):
            self.extend = ""

        def init(self, extend=""):
            self.extend = extend


# ══════════════════════════════════════════════════════
#  ★★★ 换站只改下面两行 ★★★
# ══════════════════════════════════════════════════════
HOST = "https://www.3abfug92d.com"
DEFAULT_BODY = "/cou345w"        # 首页路径前缀；自动发现失败时用这个

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CATS = {1: "大陆", 2: "日韩", 3: "欧美", 4: "动漫", 5: "三级"}
TC = None


# ──────────────────────────────────────── HTTP 层（零依赖 + 可选加速）
try:
    import curl_cffi.requests as _cr
    _HAS_CFFI = True
except Exception:
    _cr = None
    _HAS_CFFI = False

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


class _Resp(object):
    """统一响应对象，接口对齐 curl_cffi / requests，方便上层无差别调用。"""

    def __init__(self, status, body, ctype=""):
        self.status_code = status
        self.content = body
        self.headers = {"Content-Type": ctype}
        self.encoding = "utf-8"

    @property
    def text(self):
        try:
            return self.content.decode(self.encoding or "utf-8", "replace")
        except Exception:
            return self.content.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code and int(self.status_code) >= 400:
            raise Exception("HTTP %s" % self.status_code)


class _UrllibSession(object):
    """用标准库拼出来的极简 Session，接口和 requests.Session 保持兼容。"""

    def __init__(self):
        self.headers = {}
        self.verify = False
        try:
            import http.cookiejar as _cj
            self._opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(_cj.CookieJar()),
                urllib.request.HTTPSHandler(context=_SSL_CTX),
            )
        except Exception:
            self._opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=_SSL_CTX))

    def get(self, url, timeout=15, **kw):
        req = urllib.request.Request(url)
        for k, v in self.headers.items():
            req.add_header(k, v)
        req.add_header("Accept-Encoding", "gzip")
        try:
            resp = self._opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            return _Resp(e.code, e.read() or b"", "")
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        if "gzip" in enc:
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        return _Resp(resp.getcode(), raw, resp.headers.get("Content-Type", ""))


def _new_session():
    """有 curl_cffi 就用它（TLS 指纹更真，过盾概率高），没有就标准库顶上。"""
    s = _cr.Session() if _HAS_CFFI else _UrllibSession()
    try:
        s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
        s.verify = False
    except Exception:
        pass
    return s


def _kw(timeout=15):
    """curl_cffi 特有的指纹参数，标准库分支下自动忽略。"""
    return {"timeout": timeout, "impersonate": "chrome120"} if _HAS_CFFI else {"timeout": timeout}


# ──────────────────────────────────────── 动态发现 body path
def _discover_body(session):
    """从 SPA 壳里提取 body 路径前缀，失败返回默认值。"""
    try:
        r = session.get(HOST + "/", **_kw(10))
        r.raise_for_status()
        js = re.search(r'src=["\']?/?(assets/[A-Za-z0-9_.\-]+\.js)', r.text)
        if not js:
            return DEFAULT_BODY
        r2 = session.get(HOST + "/" + js.group(1), **_kw(10))
        r2.raise_for_status()
        seg = re.search(r'atob\(\s*["\']([^"\']+)["\']\s*\)', r2.text)
        if not seg:
            return DEFAULT_BODY
        path = base64.b64decode(seg.group(1)).decode("utf-8", "ignore").strip()
        if not path:
            return DEFAULT_BODY
        return path if path.startswith("/") else "/" + path
    except Exception as e:
        print("[8x8x] body discover failed: %s, using default" % e)
        return DEFAULT_BODY


def _unq(s):
    """抠出来的属性值统一去引号去空白。"""
    return (s or "").strip().strip('"').strip("'").strip()


class Spider(_Base):
    def init(self, extend=""):
        self._s = _new_session()
        self._bd = _discover_body(self._s)
        print("[8x8x] body path: %s" % self._bd)

    def getName(self):
        return "8x8x"

    def isVideoFormat(self, u):
        return ".m3u8" in u or ".mp4" in u

    def manualVideoCheck(self):
        return False

    def _get(self, url, timeout=15):
        if not url.startswith("http"):
            url = HOST + self._bd + url
        try:
            r = self._s.get(url, **_kw(timeout))
            r.raise_for_status()
            if hasattr(r, "encoding"):
                r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print("[8x8x]GET %s -> %s" % (url[:60], e))
            return ""

    def _tags(self):
        global TC
        if TC is not None:
            return TC
        h = self._get("/")
        g = {}
        if not h:
            TC = g
            return g
        for gm in re.finditer(
                r'<div\s[^>]*class=["\']?tag-group["\']?[^>]*data-group-id=\d+[^>]*>'
                r'.*?<span\s[^>]*class=["\']?tag-group-label["\']?[^>]*>([^<]+)</span>'
                r'(.*?)</div>', h, re.DOTALL):
            gn = gm.group(1)
            inner = gm.group(2)
            ts = re.findall(r'<a\s[^>]*href=["\']?(/tags/[^/]+/)["\']?[^>]*>([^<]+)</a>', inner)
            if ts:
                g[gn] = ts
        TC = g
        return g

    def _cards(self, h):
        v = []
        for m in re.finditer(r'<a\s[^>]*href=["\']?(/vd/\d+/)["\']?[^>]*>(.*?)</a>',
                             h, re.DOTALL):
            inner = m.group(2)
            tm = re.search(r'<div\s[^>]*class=["\']?card-title["\']?[^>]*>(.*?)</div>', inner)
            im = re.search(r'data-src=["\']?([^\s>"\']+)', inner)
            v.append({
                "vod_id": m.group(1),
                "vod_name": _unq(tm.group(1)) if tm else "N/A",
                "vod_pic": _unq(im.group(1)) if im else "",
                "vod_remarks": "",
            })
        return v

    def homeContent(self, filter=False):
        t = self._tags()
        cs = []
        for cid, cn in sorted(CATS.items()):
            cs.append({"type_id": str(cid), "type_name": cn})
        for gn in sorted(t.keys()):
            for url, name in t[gn]:
                cs.append({"type_id": url, "type_name": "[%s] %s" % (gn, name)})
        return {"class": cs}

    def homeVideoContent(self):
        h = self._get("/")
        return {"list": self._cards(h)[:30] if h else []}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        try:
            pn = max(int(str(pg)), 1)
            base = tid.rstrip("/") if tid.startswith("/tags/") else "/category/%d" % int(tid)
            h = self._get("%s/page/%d/" % (base, pn))
            if not h:
                return {"list": [], "page": pg, "pagecount": 1}
            mp = re.search(r'data-max=["\']?(\d+)', h)
            pc = int(mp.group(1)) if mp else pn
            v = self._cards(h)
            return {"list": v, "page": pn, "pagecount": pc,
                    "limit": len(v), "total": pc * len(v) if v else 0}
        except Exception as e:
            print("[8x8x]cat:%s" % e)
            return {"list": [], "page": pg, "pagecount": 1}

    def detailContent(self, ids):
        vid = ids[0]
        if not vid.startswith("/vd/"):
            vid = "/vd/%s/" % vid.strip("/")
        h = self._get(vid)
        if not h:
            return {"list": []}
        tm = re.search(r'<title>(.*?)</title>', h, re.DOTALL)
        title = tm.group(1).replace(" - 8x8x", "").strip() if tm else ""
        pm = re.search(r'data-poster=["\']?([^\s>"\']+)', h)
        pic = _unq(pm.group(1)) if pm else ""
        mm = re.search(r'data-m3u8=["\']?([^\s>"\']+)', h)
        if not mm:
            return {"list": [{"vod_id": ids[0], "vod_name": title, "vod_pic": pic}]}
        m3u8_path = _unq(mm.group(1))
        # 线路名与播放组在同一循环里同步 append —— 天然同长，不会错位对不上
        pf = []
        pu = []
        for i, rn in enumerate(["data-route1", "data-route2", "data-route3"], 1):
            rm = re.search(r'%s=["\']?([^\s>"\']+)' % rn, h)
            if rm:
                rt = _unq(rm.group(1)).rstrip("/")
                full_m3u8 = rt + "/" + m3u8_path.lstrip("/")
                pf.append("线路%d" % i)
                pu.append("线路%d$%s" % (i, full_m3u8))
        return {"list": [{
            "vod_id": ids[0], "vod_name": title, "vod_pic": pic,
            "type_name": "", "vod_year": "", "vod_area": "", "vod_remarks": "",
            "vod_actor": "", "vod_director": "", "vod_content": "",
            "vod_play_from": "$$$".join(pf), "vod_play_url": "$$$".join(pu),
        }]}

    def playerContent(self, flag, id, vipFlags=None):
        hdr = json.dumps({"User-Agent": UA, "Referer": HOST + "/"})
        if id and ".m3u8" in id:
            return {"url": id, "header": hdr}
        d = self.detailContent([id])
        if d and d.get("list"):
            urls = d["list"][0].get("vod_play_url", "").split("$$$")
            if urls and urls[0]:
                first = urls[0]
                if "$" in first:
                    first = first.split("$", 1)[1]
                return {"url": first, "header": hdr}
        return {"url": ""}

    def searchContent(self, key, quick=False, pg=1):
        try:
            pn = max(int(str(pg)), 1)
            # 关键词必须 quote —— 中文直接裸拼进 URL 必被源站当非法请求
            url = "%s/api/search/video?keyword=%s&page=%d" % (HOST, quote(key), pn)
            r = self._s.get(url, **_kw(15))
            r.raise_for_status()
            data = r.json()
            if data.get("code") != 0:
                return {"list": [], "page": pn, "pagecount": 1}
            dl = data.get("data") or {}
            videos = []
            for item in dl.get("list", []) or []:
                videos.append({
                    "vod_id": "/vd/%s/" % item["id"],
                    "vod_name": item.get("title", ""),
                    "vod_pic": item.get("litpic", ""),
                    "vod_remarks": item.get("typename", ""),
                })
            return {"list": videos, "page": pn,
                    "pagecount": dl.get("total_pages", pn),
                    "limit": len(videos), "total": dl.get("total", 0)}
        except Exception as e:
            print("[8x8x]search:%s" % e)
            return {"list": [], "page": pg, "pagecount": 1}

    def localProxy(self, param):
        return None