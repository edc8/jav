#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色窝网 TVBox 爬虫源 —— 基于遮天法 2.0
适配站点：色窝网（WordPress + GridMax 主题）
临时域名：https://ccc.sw888.sbs/
永久域名：https://sewo.my/  https://sewo.mom/
特性：
  - 多域名自动切换（临时失效自动回退永久域名）
  - 封面图走 img.886345.xyz 代理，防盗链
  - 播放地址从 iframe /tt/t.php?url= 提取真实 m3u8
  - 本地代理过滤开头 ts 广告切片
  - 分类、搜索、详情、播放全接口
"""

import re
import json
import time
import base64
import hashlib
import threading
import random
from urllib import parse
from typing import Dict, List, Optional, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import requests
from bs4 import BeautifulSoup

# ─── 兼容 TVBox 生态 ───
try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase:
        pass


# ══════════════════════════════════════════════════════════════
# 色窝网专用配置
# ══════════════════════════════════════════════════════════════
HOSTS = [
    "https://ccc.sw888.sbs",   # 临时
    "https://sewo.my",         # 永久1
    "https://sewo.mom",        # 永久2
]

# 首页导航分类（从源码菜单提取）
CATEGORIES = [
    {"type_name": "91探花",     "type_id": "91探花"},
    {"type_name": "国产色情",   "type_id": "国产色情"},
    {"type_name": "亚洲无码",   "type_id": "亚洲无码"},
    {"type_name": "闷骚护士",   "type_id": "闷骚护士"},
    {"type_name": "台湾辣妹",   "type_id": "台湾辣妹"},
    {"type_name": "东南亚AV",   "type_id": "东南亚AV"},
    {"type_name": "传媒出品",   "type_id": "传媒出品"},
    {"type_name": "韩国御姐",   "type_id": "韩国御姐"},
    {"type_name": "女同性恋",   "type_id": "女同性恋"},
    {"type_name": "素人自拍",   "type_id": "素人自拍"},
    {"type_name": "唯美港姐",   "type_id": "唯美港姐"},
    {"type_name": "主播直播",   "type_id": "主播直播"},
    {"type_name": "自拍偷拍",   "type_id": "自拍偷拍"},
]

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/131.0.0.0 Mobile Safari/537.36",
]


# ══════════════════════════════════════════════════════════════
# 本地代理（过滤 m3u8 开头广告 ts 切片）
# ══════════════════════════════════════════════════════════════
class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class _ProxyHandler(BaseHTTPRequestHandler):
    """道宫·仙珍图：过滤广告分片 + 阵字秘 Referer 伪装"""

    def log_message(self, *args):
        pass  # 静默

    def do_GET(self):
        try:
            qs = parse.parse_qs(parse.urlparse(self.path).query)
            target = qs.get("url", [""])[0]
            if not target:
                self.send_error(400, "missing url")
                return
            target = parse.unquote(target)

            headers = {
                "User-Agent": random.choice(UA_POOL),
                "Referer": qs.get("ref", ["https://sewo.my/"])[0],
                "Accept": "*/*",
            }
            resp = requests.get(target, headers=headers, timeout=15, stream=True)
            content_type = resp.headers.get("Content-Type", "application/vnd.apple.mpegurl")

            body = resp.content
            # 仅对 m3u8 做广告清洗
            if "mpegurl" in content_type or target.endswith(".m3u8") or b"#EXTM3U" in body[:20]:
                text = body.decode("utf-8", errors="replace")
                text = self._filter_ad_ts(text, target)
                body = text.encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_error(502, str(e))

    @staticmethod
    def _filter_ad_ts(m3u8: str, base_url: str) -> str:
        """
        过滤视频开头广告 ts 切片。
        常见广告特征：
          - 时长极短（#EXTINF:1. 或 2.）且连续出现在开头
          - 路径含 ad / advert / promo / gg / 推广
          - 域名与主分片不同
        """
        lines = m3u8.splitlines()
        out = []
        i = 0
        # 收集主内容域名（取第一个正常分片的 host）
        main_host = ""
        for ln in lines:
            if ln.startswith("http") and ".ts" in ln:
                main_host = parse.urlparse(ln).netloc
                break
            if not ln.startswith("#") and ".ts" in ln:
                abs_u = parse.urljoin(base_url, ln)
                main_host = parse.urlparse(abs_u).netloc
                break

        skip_count = 0
        max_head_skip = 8  # 最多跳过开头 8 个疑似广告分片

        while i < len(lines):
            line = lines[i]
            # 广告关键词
            low = line.lower()
            is_ad_kw = any(k in low for k in ("/ad", "advert", "promo", "gg/", "推广", "adts", "ad_"))

            # 短时长 + 开头位置
            is_short = False
            if line.startswith("#EXTINF:"):
                try:
                    dur = float(line.split(":")[1].split(",")[0])
                    is_short = dur <= 3.0
                except Exception:
                    pass

            if is_ad_kw or (is_short and skip_count < max_head_skip and i < 40):
                # 跳过本 EXTINF 和下一行 uri
                skip_count += 1
                i += 1
                if i < len(lines) and not lines[i].startswith("#"):
                    i += 1
                continue

            # 跨域分片（与主 host 不同）在开头也视为广告
            if not line.startswith("#") and ".ts" in line and main_host:
                abs_u = line if line.startswith("http") else parse.urljoin(base_url, line)
                if parse.urlparse(abs_u).netloc != main_host and skip_count < max_head_skip and i < 40:
                    skip_count += 1
                    i += 1
                    continue

            out.append(line)
            i += 1

        return "\n".join(out)


class LocalProxy:
    """道宫本地代理大阵"""
    _port = 9979
    _server = None
    _lock = threading.Lock()

    @classmethod
    def start(cls) -> int:
        with cls._lock:
            if cls._server:
                return cls._port
            for port in range(9979, 9990):
                try:
                    cls._server = _ThreadingHTTPServer(("127.0.0.1", port), _ProxyHandler)
                    t = threading.Thread(target=cls._server.serve_forever, daemon=True)
                    t.start()
                    cls._port = port
                    return port
                except OSError:
                    continue
            return 0

    @classmethod
    def proxy_url(cls, real_url: str, referer: str = "") -> str:
        port = cls.start()
        if not port:
            return real_url
        q = parse.urlencode({"url": real_url, "ref": referer or "https://sewo.my/"})
        return f"http://127.0.0.1:{port}/?{q}"


# ══════════════════════════════════════════════════════════════
# 色窝网 Spider
# ══════════════════════════════════════════════════════════════
class Spider(SpiderBase):
    def __init__(self):
        # 部分加载器会调 __init__，部分只调 init，两边都初始化
        self.siteUrl = HOSTS[0]
        self._alive_host = None
        self._session = requests.Session()
        self._lock = threading.Lock()

    def init(self, extend=""):
        """TVBox 抽象方法，必须实现，否则报 Can't instantiate abstract class Spider"""
        if not hasattr(self, "_session") or self._session is None:
            self._session = requests.Session()
        if not hasattr(self, "_alive_host"):
            self._alive_host = None
        if not hasattr(self, "siteUrl"):
            self.siteUrl = HOSTS[0]
        if not hasattr(self, "_lock"):
            self._lock = threading.Lock()
        # 探测可用域名
        try:
            self._pick_host()
        except Exception:
            self.siteUrl = HOSTS[0]
            self._alive_host = HOSTS[0]
        # 预热本地代理（过滤开头广告 ts）
        try:
            LocalProxy.start()
        except Exception:
            pass
        return True

    def getName(self):
        return "色窝网"

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    # ─── 基础工具 ───
    def _ua(self) -> str:
        return random.choice(UA_POOL)

    def _headers(self, extra: Dict = None) -> Dict:
        h = {
            "User-Agent": self._ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if extra:
            h.update(extra)
        return h

    def _pick_host(self) -> str:
        """探测可用域名，缓存结果"""
        if self._alive_host:
            return self._alive_host
        for host in HOSTS:
            try:
                r = self._session.get(host, headers=self._headers(), timeout=8, allow_redirects=True)
                if r.status_code == 200 and ("色窝" in r.text or "gridmax" in r.text.lower()):
                    self._alive_host = host.rstrip("/")
                    self.siteUrl = self._alive_host
                    return self._alive_host
            except Exception:
                continue
        # 全部失败也返回第一个，后续请求会重试
        self._alive_host = HOSTS[0].rstrip("/")
        self.siteUrl = self._alive_host
        return self._alive_host

    def fetch(self, path_or_url: str, timeout: int = 12) -> str:
        host = self._pick_host()
        if path_or_url.startswith("http"):
            url = path_or_url
        else:
            url = f"{host}{path_or_url}" if path_or_url.startswith("/") else f"{host}/{path_or_url}"
        try:
            resp = self._session.get(url, headers=self._headers({"Referer": host + "/"}), timeout=timeout, allow_redirects=True)
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except Exception:
            # 当前 host 失效，清空缓存再试一次
            self._alive_host = None
            host = self._pick_host()
            if not path_or_url.startswith("http"):
                url = f"{host}{path_or_url}" if path_or_url.startswith("/") else f"{host}/{path_or_url}"
            try:
                resp = self._session.get(url, headers=self._headers({"Referer": host + "/"}), timeout=timeout)
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except Exception:
                return ""

    @staticmethod
    def fix_url(url: str, host: str) -> str:
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return host.rstrip("/") + url
        return host.rstrip("/") + "/" + url

    @staticmethod
    def clean_title(t: str) -> str:
        import html as _html
        t = _html.unescape(t or "")
        t = re.sub(r"<[^>]+>", "", t)
        return t.strip()

    # ─── 列表解析 ───
    def _parse_list(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        videos = []
        seen = set()
        # 主选择器：.gridmax-grid-post
        for post in soup.select("div.gridmax-grid-post"):
            a = post.select_one("a.gridmax-grid-post-thumbnail-link") or post.select_one("h3.gridmax-grid-post-title a")
            if not a:
                continue
            href = a.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            # 标题：优先 h3 正文，避免 title 属性带 "Permanent Link to "
            t_node = post.select_one("h3.gridmax-grid-post-title a")
            title = t_node.get_text(strip=True) if t_node else ""
            if not title:
                title = a.get("title") or a.get_text(strip=True) or ""
            title = self.clean_title(title)
            if title.lower().startswith("permanent link to "):
                title = title[18:].strip()
            if not title:
                continue
            # 封面
            img = post.select_one("img.gridmax-grid-post-thumbnail-img")
            pic = ""
            if img:
                pic = img.get("src") or img.get("data-src") or img.get("data-original") or ""
            # 相对路径补全
            pic = self.fix_url(pic, self.siteUrl)
            # vod_id 用相对路径，方便跨域名
            vod_id = href
            if href.startswith("http"):
                # 提取 /s/xxxxx.html
                m = re.search(r"(/s/\d+\.html)", href)
                if m:
                    vod_id = m.group(1)
            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })
        return videos

    # ─── TVBox 六接口 ───
    def homeContent(self, filter=False):
        self._pick_host()
        # 首页同时返回推荐列表，避免客户端只看 list 时显示「暂无数据」
        html = self.fetch("/")
        videos = self._parse_list(html)[:24]
        return {
            "class": CATEGORIES,
            "list": videos,
        }

    def homeVideoContent(self):
        """首页推荐（可选）"""
        html = self.fetch("/")
        return {"list": self._parse_list(html)[:20]}

    def categoryContent(self, tid, pg, filter, extend):
        """
        tid 为分类名（中文），WordPress 分类路径为 /s/category/{urlencoded}
        分页：/s/category/xxx/page/{n}/
        """
        self._pick_host()
        page = int(pg) if str(pg).isdigit() else 1
        # URL 编码分类名
        cat_path = parse.quote(tid)
        if page <= 1:
            path = f"/s/category/{cat_path}"
        else:
            path = f"/s/category/{cat_path}/page/{page}/"
        html = self.fetch(path)
        videos = self._parse_list(html)
        # 若路径式分页失败，尝试 ?paged=
        if not videos and page > 1:
            path = f"/s/category/{cat_path}?paged={page}"
            html = self.fetch(path)
            videos = self._parse_list(html)
        return {
            "list": videos,
            "page": page,
            "pagecount": 999 if videos else page,
            "limit": len(videos) or 20,
            "total": 99999,
        }

    def detailContent(self, ids):
        self._pick_host()
        vod_id = ids[0]
        # 支持完整 URL 或相对路径
        if vod_id.startswith("http"):
            url = vod_id
            # 统一成相对路径存
            m = re.search(r"(/s/\d+\.html)", vod_id)
            if m:
                vod_id = m.group(1)
        else:
            url = vod_id if vod_id.startswith("/") else f"/s/{vod_id}"
        html = self.fetch(url)
        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")
        # 标题
        # 顶部广告 h1「永久域名/合作联系」需跳过，真实标题在 article 内
        name = ""
        for sel in [
            "article h1.post-title.entry-title a",
            "article h1.entry-title",
            "h1.post-title.entry-title a",
            ".entry-header h1 a",
            ".entry-header h1",
        ]:
            node = soup.select_one(sel)
            if not node:
                continue
            cand = self.clean_title(node.get_text(strip=True))
            if cand and "永久域名" not in cand and "合作联系" not in cand and "色窝网" != cand:
                name = cand
                break
        if not name:
            og = soup.select_one('meta[property="og:title"]')
            if og and og.get("content"):
                name = self.clean_title(og.get("content"))
        if not name:
            name = "色窝视频"
        # 封面（详情页可能没有，用 related 第一张或空）
        pic = ""
        img = soup.select_one("img.gridmax-related-post-item-thumbnail-img") or soup.select_one("article img")
        if img:
            pic = self.fix_url(img.get("src") or "", self.siteUrl)

        # 播放地址：从 iframe src="/tt/t.php?url=真实m3u8" 提取
        play_url = ""
        iframe = soup.select_one("iframe[src*='t.php']") or soup.select_one("iframe[src*='m3u8']")
        if iframe:
            src = iframe.get("src", "")
            # /tt/t.php?url=https://xxx/index.m3u8
            m = re.search(r"[?&]url=([^&\"']+)", src)
            if m:
                play_url = parse.unquote(m.group(1))
            elif src.startswith("http") and ".m3u8" in src:
                play_url = src
        # 兜底正则
        if not play_url:
            m = re.search(r'/tt/t\.php\?url=([^"\'&\s]+)', html)
            if m:
                play_url = parse.unquote(m.group(1))
        if not play_url:
            m = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html)
            if m:
                play_url = m.group(1)

        # 分类备注
        cat_node = soup.select_one(".gridmax-entry-meta-single-cats a")
        remarks = cat_node.get_text(strip=True) if cat_node else ""

        if not play_url:
            # 无直链时把详情页本身交给嗅探
            play_from = "嗅探"
            play_url_str = f"正片${self.fix_url(url if not url.startswith('http') else url, self.siteUrl)}"
            parse_flag = 1
        else:
            play_from = "色窝直链"
            play_url_str = f"正片${play_url}"
            parse_flag = 0

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_content": name,
                "vod_remarks": remarks,
                "vod_play_from": play_from,
                "vod_play_url": play_url_str,
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        """
        返回直链 m3u8 + Header。
        Android 播放器访问不到 127.0.0.1 本地代理，故默认直出真实地址。
        """
        self._pick_host()
        url = id or ""
        headers = {
            "User-Agent": self._ua(),
            "Referer": self.siteUrl + "/",
            "Origin": self.siteUrl,
        }

        # 详情页 → 再抠 m3u8
        if "/s/" in url and ".html" in url and ".m3u8" not in url:
            html = self.fetch(url)
            m = re.search(r'/tt/t\.php\?url=([^"\'&\s]+)', html or "")
            if m:
                url = parse.unquote(m.group(1))
            else:
                m2 = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html or "")
                if m2:
                    url = m2.group(1)
                else:
                    return {"parse": 1, "url": self.fix_url(url, self.siteUrl), "header": headers}

        if ".m3u8" in url:
            return {"parse": 0, "url": url, "header": headers}

        return {"parse": 0, "url": url, "header": headers}

    def searchContent(self, key, quick, pg="1"):
        """WordPress 搜索：/?s=关键词"""
        self._pick_host()
        page = int(pg) if str(pg).isdigit() else 1
        q = parse.quote(key)
        if page <= 1:
            path = f"/?s={q}"
        else:
            path = f"/page/{page}/?s={q}"
        html = self.fetch(path)
        videos = self._parse_list(html)
        return {"list": videos}

    def localProxy(self, param):
        """TVBox 调用本地代理时启动道宫大阵"""
        port = LocalProxy.start()
        return [200, "application/json", json.dumps({
            "proxy": f"http://127.0.0.1:{port}",
            "status": "running",
            "site": self.siteUrl,
        })]


# ══════════════════════════════════════════════════════════════
# 自测入口
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    sp = Spider()
    print("=== homeContent ===")
    print(json.dumps(sp.homeContent(), ensure_ascii=False, indent=2)[:500])
    print("\n=== categoryContent (国产色情 pg=1) ===")
    cat = sp.categoryContent("国产色情", "1", False, {})
    print(f"共 {len(cat.get('list', []))} 条")
    if cat.get("list"):
        print(json.dumps(cat["list"][0], ensure_ascii=False, indent=2))
        vid = cat["list"][0]["vod_id"]
        print("\n=== detailContent ===")
        detail = sp.detailContent([vid])
        print(json.dumps(detail, ensure_ascii=False, indent=2)[:800])
        if detail.get("list"):
            play_url = detail["list"][0].get("vod_play_url", "")
            if "$" in play_url:
                real = play_url.split("$", 1)[1]
                print("\n=== playerContent ===")
                play = sp.playerContent("", real, "")
                print(json.dumps(play, ensure_ascii=False, indent=2))
    print("\n=== searchContent ===")
    se = sp.searchContent("探花", "0", "1")
    print(f"搜索结果 {len(se.get('list', []))} 条")
