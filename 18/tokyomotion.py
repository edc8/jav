# -*- coding: utf-8 -*-
# 遮天TVBox · TOKYO Motion https://www.tokyomotion.net
# AVS 脚本站：/video/{id}/ 详情内 <source src="/vsrc/sd|hd/{hash}"> 直链 MP4
import re
import sys
from html import unescape
from urllib import parse, request as urlrequest

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        def __init__(self):
            pass

_SEED = [{"vod_id": "4727879", "vod_name": "デリヘル　中出し", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb147/4727879/1.jpg", "vod_remarks": "28:19"}, {"vod_id": "6778040", "vod_name": "LC", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6778040/1.jpg", "vod_remarks": "42:43"}, {"vod_id": "6534972", "vod_name": "ライブチャットフェラ", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb204/6534972/2.jpg", "vod_remarks": "07:59"}, {"vod_id": "6198952", "vod_name": "M 12", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb193/6198952/1.jpg", "vod_remarks": "37:37"}, {"vod_id": "3578213", "vod_name": "jk 悪ノリ レズ", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb111/3578213/1.jpg", "vod_remarks": "55:57"}, {"vod_id": "6719830", "vod_name": "DBTK-002 初撮り奥さま今日からAVデビュー 蒼乃幸恵 (モザイク破壊)", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb209/6719830/5.jpg", "vod_remarks": "47:40"}, {"vod_id": "5898334", "vod_name": "最新モザイク破壊 20251209", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb184/5898334/1.jpg", "vod_remarks": "15:52"}, {"vod_id": "5578802", "vod_name": "夜間学校に通う‘ 人妻", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb174/5578802/1.jpg", "vod_remarks": "02:05:35"}, {"vod_id": "6667931", "vod_name": "Candid 1435", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb208/6667931/1.jpg", "vod_remarks": "08:38"}, {"vod_id": "6709778", "vod_name": "背景ストライプ2026.7.17", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb209/6709778/9.jpg", "vod_remarks": "08:28"}, {"vod_id": "6771508", "vod_name": "凄く美人①", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6771508/1.jpg", "vod_remarks": "11:49"}, {"vod_id": "6769206", "vod_name": "收藏用", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6769206/1.jpg", "vod_remarks": "11:03"}, {"vod_id": "6782265", "vod_name": "ドウイン", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782265/1.jpg", "vod_remarks": "00:21"}, {"vod_id": "6782262", "vod_name": "拾い", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782262/1.jpg", "vod_remarks": "00:34"}, {"vod_id": "6782249", "vod_name": "拾い", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782249/1.jpg", "vod_remarks": "09:33"}, {"vod_id": "6782247", "vod_name": "Ckl", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782247/1.jpg", "vod_remarks": "11:00"}, {"vod_id": "6782241", "vod_name": "拾い", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782241/1.jpg", "vod_remarks": "02:00"}, {"vod_id": "6782240", "vod_name": "Encoxada Dickflash cum ass", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782240/1.jpg", "vod_remarks": "00:31"}, {"vod_id": "6782239", "vod_name": "Encoxada Dickflash cum ass", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782239/1.jpg", "vod_remarks": "00:31"}, {"vod_id": "6782237", "vod_name": "Encoxada Dickflash cum ass", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782237/1.jpg", "vod_remarks": "00:31"}, {"vod_id": "6782235", "vod_name": "自撮り", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782235/1.jpg", "vod_remarks": "12:19"}, {"vod_id": "6782233", "vod_name": "Encoxada Dickflash cum ass", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782233/1.jpg", "vod_remarks": "00:31"}, {"vod_id": "6782231", "vod_name": "拾い", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782231/1.jpg", "vod_remarks": "00:52"}, {"vod_id": "6782230", "vod_name": "Encoxada Dickflash cum ass", "vod_pic": "https://cdn.tokyo-motion.net/media/videos/tmb211/6782230/1.jpg", "vod_remarks": "00:31"}]


class Spider(BaseSpider):
    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.host = "https://www.tokyomotion.net"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
            "Referer": "https://www.tokyomotion.net/",
        }
        self.session = None
        self._seed = list(_SEED)

    def init(self, extend=""):
        self._ensure_session()
        return True

    def _ensure_session(self):
        if self.session is not None:
            return
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        except Exception:
            self.session = None

    def getName(self):
        return "TOKYO Motion"

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return any(x in u for x in [".mp4", ".m3u8", ".flv", "/vsrc/"])

    def manualVideoCheck(self):
        return False

    def _get(self, path, timeout=18):
        url = path if path.startswith("http") else (self.host.rstrip("/") + path)
        self._ensure_session()
        headers = dict(self.headers)
        headers["Referer"] = self.host + "/"
        if self.session is not None:
            try:
                r = self.session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                r.encoding = "utf-8"
                if r.status_code == 200 and r.text:
                    return r.text
            except Exception as e:
                print("[TOK] req", e)
        try:
            req = urlrequest.Request(url, headers=headers)
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as e:
            print("[TOK] urllib", e)
        return ""

    def _fallback_classes(self):
        return [
            {"type_id": "home", "type_name": "首页"},
            {"type_id": "mr", "type_name": "最新"},
            {"type_id": "bw", "type_name": "正在看"},
            {"type_id": "mv", "type_name": "最多观看"},
            {"type_id": "tr", "type_name": "好评"},
            {"type_id": "md", "type_name": "今日热门"},
        ]

    def _list_url(self, tid, pg):
        pg, tid = str(pg), str(tid)
        if tid in ("home", "0", ""):
            if pg in ("1", "0", ""):
                return "/"
            return "/page=%s" % pg
        # /videos?o=mr&page=2 或 /videos?o=mr
        o = tid
        if pg in ("1", "0", ""):
            return "/videos?o=%s" % o
        return "/videos?o=%s&page=%s" % (o, pg)

    def _cards(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        for m in re.finditer(
            r'href="(/video/(\d+)/[^"]*)"',
            html,
        ):
            path, vid = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            block = html[max(0, m.start() - 80) : m.end() + 500]
            title = ""
            t = re.search(r'(?:title|alt)="([^"]+)"', block)
            if t:
                title = unescape(t.group(1)).strip()
            if not title:
                t = re.search(r'video-title[^>]*>\s*([^<]+)', block)
                if t:
                    title = unescape(t.group(1)).strip()
            pic = ""
            img = re.search(r'src="(https://cdn\.tokyo-motion\.net/media/videos/[^"]+)"', block)
            if img:
                pic = img.group(1)
            remarks = ""
            d = re.search(r'class="duration"[^>]*>\s*([^<]+)', block)
            if d:
                remarks = d.group(1).strip()
            if not remarks:
                hd = re.search(r'hd-text-icon[^>]*>\s*([^<]+)', block)
                if hd:
                    remarks = hd.group(1).strip()
            videos.append(
                {
                    "vod_id": vid,
                    "vod_name": (title or vid)[:80],
                    "vod_pic": pic,
                    "vod_remarks": remarks or "TOK",
                }
            )
        return videos

    def homeContent(self, filter):
        videos = self._cards(self._get("/"))
        if not videos:
            videos = list(self._seed)
        return {"class": self._fallback_classes(), "list": videos}

    def homeVideoContent(self):
        try:
            return self.categoryContent("home", "1", False, {})
        except Exception:
            return {"list": list(self._seed)}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            path = self._list_url(tid, pg)
            print("[TOK] list", path)
            html = self._get(path)
            videos = self._cards(html)
            if not videos and str(pg) in ("1", "0", "") and self._seed:
                videos = list(self._seed)
            print("[TOK] cards", len(videos))
            return {
                "list": videos,
                "page": int(pg) if str(pg).isdigit() else 1,
                "pagecount": 999 if videos else 1,
                "limit": 24,
                "total": 99999 if videos else 0,
            }
        except Exception as e:
            print("[TOK] category", e)
            videos = list(self._seed) if self._seed else []
            return {"list": videos, "page": 1, "pagecount": 1, "limit": 24, "total": len(videos)}

    def detailContent(self, ids):
        try:
            vid = str(ids[0] if isinstance(ids, list) else ids)
            vid = re.sub(r"\D", "", vid.split("/")[-1] if not vid.isdigit() else vid)
            # 先试 /video/{id}/
            html = self._get("/video/%s/" % vid)
            if not html or "vsrc" not in html:
                html = self._get("/video/%s" % vid)

            title = ""
            t = re.search(r'<h3[^>]*>\s*([^<]+)', html or "")
            if not t:
                t = re.search(r'<h4[^>]*>\s*([^<]+)', html or "")
            if t:
                title = unescape(t.group(1)).strip()
            if not title:
                t = re.search(r'og:title"\s+content="([^"]+)"', html or "")
                if t:
                    title = unescape(t.group(1)).strip()
            if not title:
                for s in self._seed:
                    if s["vod_id"] == vid:
                        title = s["vod_name"]
                        break
            if not title:
                title = vid

            pic = ""
            img = re.search(r'og:image"\s+content="([^"]+)"', html or "")
            if img:
                pic = img.group(1)
            if not pic:
                img = re.search(r'poster="(https://cdn\.tokyo-motion\.net/[^"]+)"', html or "")
                if img:
                    pic = img.group(1)

            # <source src=".../vsrc/hd/xxx" title="HD">
            sources = re.findall(
                r'<source[^>]+src="(https?://[^"]+/vsrc/(sd|hd)/[^"]+)"[^>]*(?:title="([^"]*)")?',
                html or "",
            )
            if not sources:
                sources = [
                    (u, "hd" if "/hd/" in u else "sd", "HD" if "/hd/" in u else "SD")
                    for u in re.findall(r'(https?://[^"\']+/vsrc/(?:sd|hd)/[a-f0-9]+)', html or "")
                ]

            # 优先 HD
            sources = sorted(sources, key=lambda x: 0 if (x[1] or "").lower() == "hd" else 1)

            play_from, play_url = [], []
            if sources:
                lines = []
                for src, quality, title_s in sources:
                    q = (title_s or quality or "MP4").upper()
                    if q not in ("HD", "SD"):
                        q = "HD" if "/hd/" in src else "SD"
                    lines.append("%s$%s" % (q, src))
                play_from.append("TOKYO")
                play_url.append("#".join(lines))
            else:
                play_from.append("TOKYO")
                play_url.append("正片$%s/video/%s/" % (self.host, vid))

            return {
                "list": [
                    {
                        "vod_id": vid,
                        "vod_name": title[:80],
                        "vod_pic": pic,
                        "vod_content": title,
                        "vod_play_from": "$$$".join(play_from),
                        "vod_play_url": "$$$".join(play_url),
                    }
                ]
            }
        except Exception as e:
            print("[TOK] detail", e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            url = id
            header = {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
            }
            low = url.lower()
            if any(x in low for x in [".mp4", "/vsrc/", ".m3u8", ".flv"]):
                return {"parse": 0, "url": url, "header": header}

            # 详情页再抽一次
            if "/video/" in url or url.isdigit():
                vid = re.sub(r"\D", "", url.split("/video/")[-1].split("/")[0]) if "/video/" in url else url
                html = self._get("/video/%s/" % vid)
                for src in re.findall(r'(https?://[^"\']+/vsrc/(?:hd|sd)/[a-f0-9]+)', html or ""):
                    if "/hd/" in src:
                        return {"parse": 0, "url": src, "header": header}
                for src in re.findall(r'(https?://[^"\']+/vsrc/(?:hd|sd)/[a-f0-9]+)', html or ""):
                    return {"parse": 0, "url": src, "header": header}
                return {"parse": 1, "url": self.host + "/video/%s/" % vid, "header": header}
            return {"parse": 1, "url": url, "header": header}
        except Exception as e:
            print("[TOK] player", e)
            return {"parse": 1, "url": id, "header": {}}

    def searchContent(self, key, quick, pg="1"):
        try:
            q = parse.quote(key.strip())
            path = "/search?search_query=%s&search_type=videos" % q
            if str(pg) not in ("1", "0", ""):
                path += "&page=%s" % pg
            html = self._get(path)
            videos = self._cards(html)
            return {"list": videos, "page": int(pg) if str(pg).isdigit() else 1}
        except Exception as e:
            print("[TOK] search", e)
            return {"list": [], "page": 1}

    def localProxy(self, param):
        return [200, "text/plain", b"ok"]
