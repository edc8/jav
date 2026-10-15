try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider:
        def init(self, extend=""):
            pass

class Spider(_BaseSpider):
    def __init__(self):
        self.rawSite = "https://www.nfyingshi.com"
        self.siteUrl = "https://www.nfyingshi.com"
        self.HOST = self.siteUrl
        self.UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.AES_KEY = b"c4c9967c1c0b2ca0"
        self.AES_IV = b"1234567890983456"
        self._cate_map = [
            ("meiju", "美剧"),
            ("hanju", "韩剧"),
            ("riju", "日剧"),
            ("%e8%8b%b1%e5%89%a7", "英剧"),
            ("dianying", "电影"),
            ("%e5%8a%a8%e7%94%bb", "动画"),
            ("%e7%9c%9f%e4%ba%ba%e7%a7%80", "真人秀"),
            ("jilupian", "纪录片"),
        ]
        self._sess = None

    def getName(self):
        return "奈菲影视"

    def getDependence(self):
        return ""

    def init(self, extend=""):
        self._sess = None

    def homeContent(self, *args):
        classes = [{"type_id": tid, "type_name": name} for tid, name in self._cate_map]
        filters = {tid: [] for tid, _ in self._cate_map}
        return {"class": classes, "filters": filters, "list": []}

    def homeVideoContent(self, *args):
        return self.categoryContent("meiju", 1, True, {})

    def categoryContent(self, *args):
        tid = str(args[0]) if args else "meiju"
        page = 1
        if len(args) > 1:
            try:
                page = int(args[1])
            except Exception:
                page = 1
        if page <= 1:
            url = f"{self.HOST}/movie_bt_series/{tid}"
        else:
            url = f"{self.HOST}/movie_bt_series/{tid}/page/{page}"
        html = self._fetch(url)
        vods = self._parse_list(html)
        pagecount = self._parse_pagecount(html, page)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20,
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
            html = self._fetch(f"{self.HOST}/movie/{vod_id}.html")
            if not html:
                continue
            title = self._re_one(r'<h1[^>]*>([^<]+)</h1>', html) or self._re_one(r"<title>([^<]+)</title>", html) or vod_id
            title = title.split("_")[0].split("&#8211;")[0].strip()
            title = title.replace("《", "").replace("》", "").strip()
            pic = self._re_one(r'data-original="(https?://[^"]+)"', html) or self._re_one(r'class="dyimg[^"]*"[^>]*>\s*<img[^>]+src="([^"]+)"', html) or ""
            if not pic:
                pic = self._re_one(r'<img[^>]+src="(https?://[^"]+uploads[^"]+)"', html) or ""
            import re
            plays = re.findall(
                r'href="(https?://[^"]*?/v_play/([^"]+)\.html)"[^>]*>([^<]+)<',
                html,
            )
            if not plays:
                plays = re.findall(
                    r'href="(/v_play/([^"]+)\.html)"[^>]*>([^<]+)<',
                    html,
                )
            eps = []
            seen = set()
            for full, b64, name in plays:
                name = name.strip()
                key = b64
                if key in seen:
                    continue
                seen.add(key)
                eps.append(f"{name}${b64}")
            if not eps:
                continue
            results.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
                "vod_content": title,
                "vod_play_from": "奈菲",
                "vod_play_url": "#".join(eps),
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
            return {"page": 1, "pagecount": 1, "limit": 20, "total": 0, "list": []}
        from urllib.parse import quote
        url = f"{self.HOST}/?s={quote(key)}"
        if page > 1:
            url = f"{self.HOST}/page/{page}/?s={quote(key)}"
        html = self._fetch(url)
        vods = self._parse_list(html)
        pagecount = self._parse_pagecount(html, page)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20,
            "list": vods,
        }

    def playerContent(self, *args):
        play_id = str(args[1] if len(args) > 1 else "")
        header = {
            "User-Agent": self.UA,
            "Referer": self.rawSite + "/",
            "Origin": self.rawSite,
        }
        if not play_id:
            return {"parse": 0, "jx": 0, "url": "", "header": header, "msg": "缺少播放标识"}
        if play_id.startswith("http") and (".m3u8" in play_id or ".mp4" in play_id):
            return {"parse": 0, "jx": 0, "url": play_id, "header": header, "format": "application/x-mpegURL" if ".m3u8" in play_id else "video/mp4"}
        url = f"{self.HOST}/v_play/{play_id}.html"
        html = self._fetch(url)
        real = self._extract_play_url(html)
        if not real:
            return {"parse": 1, "jx": 0, "url": url, "header": header}
        return {
            "parse": 0,
            "jx": 0,
            "url": real,
            "header": header,
            "format": "application/x-mpegURL" if ".m3u8" in real else "video/mp4",
            "playUrl": "",
        }

    def localProxy(self, *args):
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in (".m3u8", ".mp4", ".flv"))

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return ""

    def destroy(self):
        self._sess = None

    def _session(self):
        import requests
        if self._sess is None:
            self._sess = requests.Session()
            self._sess.headers.update({
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
        return self._sess

    def _fetch(self, url):
        try:
            r = self._session().get(url, headers={"Referer": self.rawSite + "/"}, timeout=20, allow_redirects=True)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception:
            return ""

    def _extract_play_url(self, html):
        if not html:
            return ""
        import re, base64
        m = re.search(r'var\s+\w+\s*=\s*"([A-Za-z0-9+/=]{80,})"', html)
        if not m:
            m = re.search(r'=\s*"([A-Za-z0-9+/]{80,}={0,2})"', html)
        if not m:
            urls = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html)
            return urls[0] if urls else ""
        data = m.group(1)
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            raw = base64.b64decode(data)
            cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV), backend=default_backend())
            dec = cipher.decryptor()
            pt = dec.update(raw) + dec.finalize()
            pad = pt[-1]
            if isinstance(pad, int) and 1 <= pad <= 16:
                pt = pt[:-pad]
            text = pt.decode("utf-8", errors="replace")
            urls = re.findall(r"https?://[^\s\"']+\.m3u8[^\s\"']*", text)
            if urls:
                return urls[0]
            urls = re.findall(r"url\s*:\s*['\"]([^'\"]+)['\"]", text)
            for u in urls:
                if u.startswith("http"):
                    return u
        except Exception:
            pass
        return ""

    def _parse_list(self, html):
        if not html:
            return []
        import re
        vods = []
        seen = set()
        pattern = re.compile(
            r'<li>\s*<a\s+href="https?://[^"]*?/movie/(\d+)\.html"[^>]*>\s*'
            r'<img[^>]+(?:data-original|src)="([^"]+)"[^>]*alt="([^"]*)"',
            re.S | re.I,
        )
        for m in pattern.finditer(html):
            vid, pic, name = m.group(1), m.group(2), m.group(3).strip()
            if vid in seen:
                continue
            seen.add(vid)
            if "blank.gif" in pic:
                pm = re.search(
                    rf'movie/{vid}\.html[\s\S]{{0,400}}data-original="([^"]+)"',
                    html,
                )
                if pm:
                    pic = pm.group(1)
            if not name:
                nm = re.search(rf'movie/{vid}\.html"[^>]*>([^<]+)</a></h3>', html)
                name = nm.group(1).strip() if nm else vid
            vods.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": "",
            })
        if not vods:
            for m in re.finditer(r'/movie/(\d+)\.html"', html):
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                nm = re.search(rf'movie/{vid}\.html"[^>]*>([^<]{{1,40}})<', html[m.start():m.start()+200])
                name = nm.group(1).strip() if nm else vid
                vods.append({"vod_id": vid, "vod_name": name, "vod_pic": "", "vod_remarks": ""})
        return vods

    def _parse_pagecount(self, html, cur):
        if not html:
            return cur
        import re
        pages = [cur]
        for m in re.finditer(r'/page/(\d+)', html):
            try:
                pages.append(int(m.group(1)))
            except Exception:
                pass
        return max(pages) if pages else cur

    def _re_one(self, pat, text, flags=0):
        import re
        m = re.search(pat, text, flags)
        return m.group(1).strip() if m else ""
