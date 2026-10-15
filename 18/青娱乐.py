try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider:
        def init(self, extend=""):
            pass

class Spider(_BaseSpider):
    def __init__(self):
        self.rawSite = "https://qyul32.com"
        self.siteUrl = "https://qyul32.com"
        self.HOST = self.siteUrl
        self.UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
            "Accept-Encoding": "gzip, deflate",
            "Referer": self.rawSite + "/",
            "Origin": self.rawSite,
        }
        self._skip_kw = ("萝莉", "幼女", "少女", "童", "loli", "teen", "schoolgirl", "未成年")
        self._cate_map = [
            ("latest", "最近更新"),
            ("top", "最高评分"),
            ("popular", "最受欢迎"),
            ("601c6e304bc693e1bd7c4eec220a108a", "欧美"),
            ("12ec88fd4018334ab558035800fe84c9", "巨乳美胸"),
            ("3d0bc19e00144fc3ffb2997796c0fc4b", "角色扮演"),
            ("a867b8557d7d3fbb62a591f4b6ad17c0", "动漫"),
            ("3a363d9000e9be1f5c2d7a566cf12e79", "內射"),
            ("ec8a7ebe4c1a92fe72820db00081042e", "出轨"),
            ("880ecc9e43283d80fc22ecac2a4fa7d6", "口交"),
            ("32a4d3fd1983092022b571941f6870f8", "中文字幕"),
            ("415127fabe2f2dffe52d76ba2c49d17a", "人妻熟女"),
            ("07570100476ef3a1471b42eec6a777b5", "群交"),
            ("c9579e8db5642ecaf58327cb3a5e48df", "顏射"),
            ("b3ee184118f72f7276d03a2ed605e22d", "偷拍自拍"),
            ("825ba6092838b6dcf4249b0612124a81", "无码"),
            ("e7c40f52d1dc2c97ef23a6360eb6231f", "国产"),
            ("f417127ae2c9465aa980c310c4291bd3", "户外"),
            ("6a562655fa6000121ee2c7e9853846bb", "制服丝袜"),
            ("2d99f87f7522d5e9b7ff69431d64dd69", "亂倫"),
            ("876fc3bc380010657784c3dd8133576f", "日韩"),
            ("d8e7955745162047f7b91e10e3252f6c", "自慰"),
            ("a6bf823c2282ad499bfcc1a147f66f4a", "美腿"),
            ("1ca5e841046fd0b342d5e8e810674793", "足交"),
            ("dc3f3b4ec8b1519822a90752efc57f1f", "有码"),
        ]

    def getName(self):
        return "青娱乐"

    def getDependence(self):
        return ""

    def init(self, extend=""):
        if extend:
            try:
                import json
                conf = json.loads(extend) if isinstance(extend, str) else extend
                if isinstance(conf, dict):
                    if conf.get("direct"):
                        self.siteUrl = self.rawSite
                        self.HOST = self.siteUrl
                    if conf.get("proxy") or conf.get("siteUrl"):
                        self.siteUrl = conf.get("proxy") or conf.get("siteUrl")
                        self.HOST = self.siteUrl
            except Exception:
                pass
        self.headers["Referer"] = self.rawSite + "/"
        self.headers["Origin"] = self.rawSite

    def homeContent(self, *args):
        classes = [{"type_id": tid, "type_name": name} for tid, name in self._cate_map]
        filters = {tid: [] for tid, _ in self._cate_map}
        return {"class": classes, "filters": filters, "list": []}

    def homeVideoContent(self, *args):
        return self.categoryContent("latest", 1, True, {})

    def categoryContent(self, *args):
        tid = str(args[0]) if args else "latest"
        page = 1
        if len(args) > 1:
            try:
                page = int(args[1])
            except Exception:
                page = 1
        if tid in ("latest", "最近更新"):
            url = f"{self.HOST}/latest-updates/" if page <= 1 else f"{self.HOST}/latest-updates/{page}/"
        elif tid in ("top", "最高评分"):
            url = f"{self.HOST}/top-rated/" if page <= 1 else f"{self.HOST}/top-rated/{page}/"
        elif tid in ("popular", "最受欢迎"):
            url = f"{self.HOST}/most-popular/" if page <= 1 else f"{self.HOST}/most-popular/{page}/"
        else:
            url = f"{self.HOST}/categories/{tid}/" if page <= 1 else f"{self.HOST}/categories/{tid}/{page}/"
        html = self._fetch(url)
        vods = self._parse_list(html)
        pagecount = self._parse_pagecount(html, page)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
            "list": vods,
        }

    def detailContent(self, *args):
        ids = args[0] if args else []
        if isinstance(ids, str):
            ids = [ids]
        if not isinstance(ids, (list, tuple)):
            ids = [str(ids)]
        results = []
        for vod_id in ids:
            vod_id = str(vod_id).strip()
            if not vod_id:
                continue
            if "/" in vod_id:
                url = f"{self.HOST}/videos/{vod_id}/"
            else:
                url = f"{self.HOST}/videos/{vod_id}/"
            html = self._fetch(url)
            if not html:
                continue
            title = self._re_one(r'<title>([^<]+)</title>', html) or vod_id
            title = title.replace(" - 青娱乐", "").replace("青娱乐", "").strip()
            if self._is_skip(title):
                continue
            pic = self._re_one(r'data-original="(https?://[^"]+videos_screenshots[^"]+)"', html) or ""
            if not pic:
                pic = self._re_one(r'preview_url:\s*[\'"]([^\'"]+)[\'"]', html) or ""
            duration = self._re_one(r'class="duration"[^>]*>([^<]+)<', html) or ""
            play_url = self._extract_play(html)
            if not play_url:
                play_url = vod_id
            results.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": duration,
                "vod_content": title,
                "vod_play_from": "青娱乐",
                "vod_play_url": f"正片${play_url}",
            })
        return {"list": results}

    def searchContent(self, *args):
        key = ""
        page = 1
        if args:
            key = str(args[0])
            if len(args) > 1:
                try:
                    page = int(args[1])
                except Exception:
                    page = 1
            if len(args) > 2:
                try:
                    page = int(args[2])
                except Exception:
                    pass
        if not key:
            return {"page": 1, "pagecount": 1, "limit": 24, "total": 0, "list": []}
        from urllib.parse import quote
        q = quote(key)
        url = f"{self.HOST}/search/{q}/" if page <= 1 else f"{self.HOST}/search/{q}/{page}/"
        html = self._fetch(url)
        vods = self._parse_list(html)
        pagecount = self._parse_pagecount(html, page)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
            "list": vods,
        }

    def playerContent(self, *args):
        flag = args[0] if args else ""
        play_id = args[1] if len(args) > 1 else ""
        url = str(play_id)
        if url.startswith("function/0/"):
            url = url[len("function/0/"):]
        elif url.startswith("function/"):
            parts = url.split("/", 2)
            url = parts[-1] if len(parts) >= 3 else url
        if not self.isVideoFormat(url) and ("/" in url or url.isdigit()):
            detail_path = url if "/" in url else url
            html = self._fetch(f"{self.HOST}/videos/{detail_path}/")
            extracted = self._extract_play(html)
            if extracted:
                url = extracted
        if not url.startswith("http"):
            url = self.HOST.rstrip("/") + "/" + url.lstrip("/")
        header = {
            "User-Agent": self.UA,
            "Referer": self.rawSite + "/",
            "Origin": self.rawSite,
        }
        return {
            "parse": 0,
            "jx": 0,
            "url": url,
            "header": header,
            "format": "video/mp4" if ".mp4" in url else "application/x-mpegURL",
        }

    def localProxy(self, *args):
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in (".mp4", ".m3u8", ".flv", "get_file"))

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return ""

    def destroy(self):
        pass

    def _fetch(self, url):
        try:
            import requests
            r = requests.get(url, headers=self.headers, timeout=15, allow_redirects=True)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception:
            return ""

    def _parse_list(self, html):
        if not html:
            return []
        import re
        vods = []
        pattern = re.compile(
            r'<a\s+href="(https?://[^"]*?/videos/(\d+)/([^"/]+)/?)"[^>]*title="([^"]*)"[^>]*>.*?'
            r'(?:data-original|src)="(https?://[^"]+videos_screenshots[^"]+)"[^>]*>.*?'
            r'(?:class="duration"[^>]*>([^<]*)<)?',
            re.S | re.I
        )
        for m in pattern.finditer(html):
            href, vid, slug, title, pic, duration = m.groups()
            title = (title or "").strip()
            if self._is_skip(title):
                continue
            vod_id = f"{vid}/{slug}"
            vods.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic or "",
                "vod_remarks": (duration or "").strip(),
            })
        if not vods:
            items = re.findall(
                r'href="(https?://[^"]*?/videos/(\d+)/([^"/]+)/?)"[^>]*title="([^"]*)"',
                html, re.I
            )
            seen = set()
            for href, vid, slug, title in items:
                title = (title or "").strip()
                if self._is_skip(title) or vid in seen:
                    continue
                seen.add(vid)
                pic = ""
                pm = re.search(rf'videos/{vid}/[^"]+".*?data-original="(https?://[^"]+)"', html, re.S)
                if pm:
                    pic = pm.group(1)
                vods.append({
                    "vod_id": f"{vid}/{slug}",
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })
        return vods

    def _parse_pagecount(self, html, cur):
        if not html:
            return cur
        import re
        nums = re.findall(r'/(?:latest-updates|top-rated|most-popular|categories/[^/]+|search/[^/]+)/(\d+)/', html)
        if nums:
            try:
                return max(int(n) for n in nums)
            except Exception:
                pass
        if re.search(r'下一页|next|末頁|末页', html, re.I):
            return cur + 1
        return cur

    def _extract_play(self, html):
        import re
        m = re.search(r"video_url:\s*['\"]([^'\"]+)['\"]", html)
        if m:
            u = m.group(1)
            if u.startswith("function/0/"):
                u = u[len("function/0/"):]
            elif u.startswith("function/"):
                parts = u.split("/", 2)
                u = parts[-1] if len(parts) >= 3 else u
            return u
        m = re.search(r'["\'](https?://[^"\']+get_file/[^"\']+\.mp4[^"\']*)["\']', html)
        if m:
            return m.group(1)
        return ""

    def _is_skip(self, text):
        if not text:
            return False
        t = text.lower()
        for kw in self._skip_kw:
            if kw.lower() in t:
                return True
        return False

    def _re_one(self, pat, text, flags=0):
        import re
        m = re.search(pat, text, flags)
        return m.group(1).strip() if m else ""
