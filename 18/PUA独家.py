# -*- coding: utf-8 -*-
# PUA独家 四壳通用Python Spider
# 站点: https://g3h4i5j6.puapua7.cc
# 架构: 苹果CMS + puapua模板 + ge_js_validator Cookie验证 + TLS指纹检测
# 播放: player_aaaa URL编码 m3u8

import re
import json
import html as html_mod
import urllib.parse

try:
    from base.spider import Spider
except Exception:
    class Spider:
        def __init__(self):
            self.extend = {}

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.rawSite = "https://g3h4i5j6.puapua7.cc"
        self.siteUrl = self.rawSite
        self.HOST = self.siteUrl
        self.cookie = ""
        self._cookie_ts = 0
        self._session = None
        self._use_curl_cffi = None

    def init(self, extend=""):
        if extend:
            try:
                ext = json.loads(extend) if isinstance(extend, str) else extend
                if ext.get("proxy"):
                    self.siteUrl = ext["proxy"]
                    self.HOST = self.siteUrl
                if ext.get("siteUrl"):
                    self.siteUrl = ext["siteUrl"]
                    self.HOST = self.siteUrl
                if ext.get("direct"):
                    self.siteUrl = self.rawSite
                    self.HOST = self.rawSite
            except Exception:
                pass

    def _get_session(self):
        """获取HTTP会话，优先curl_cffi（浏览器TLS指纹），兜底urllib"""
        if self._use_curl_cffi is None:
            try:
                from curl_cffi import requests as cffi_requests
                self._session = cffi_requests.Session(impersonate="chrome131")
                self._use_curl_cffi = True
            except Exception:
                self._use_curl_cffi = False
        return self._session

    def _get_cookie(self):
        """获取ge_js_validator cookie"""
        import time
        now = int(time.time())
        if self.cookie and (now - self._cookie_ts) < 500:
            return self.cookie
        try:
            resp = self._req_raw(self.siteUrl + "/vodtype/11.html")
            if resp and "ge_js_validator" in resp:
                m = re.search(r'document\.cookie\s*=\s*"([^"]+)"', resp)
                if m:
                    cookie_str = m.group(1)
                    name_val = cookie_str.split(';')[0]
                    self.cookie = name_val
                    self._cookie_ts = now
                    # 设置到session
                    sess = self._get_session()
                    if sess and self._use_curl_cffi:
                        cname, cval = name_val.split('=', 1)
                        sess.cookies.set(cname, cval, domain='.puapua7.cc')
                    return self.cookie
        except Exception:
            pass
        return self.cookie

    def _req_raw(self, url):
        """底层请求，不带cookie（用于获取挑战页）"""
        sess = self._get_session()
        if self._use_curl_cffi and sess:
            try:
                r = sess.get(url, timeout=15)
                return r.text
            except Exception:
                return ""
        else:
            import urllib.request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode('utf-8', errors='ignore')
            except Exception:
                return ""

    def _req(self, url, need_cookie=True):
        """统一请求方法，处理ge_js_validator + TLS指纹"""
        if need_cookie:
            self._get_cookie()

        sess = self._get_session()
        if self._use_curl_cffi and sess:
            try:
                r = sess.get(url, timeout=15)
                text = r.text
                # 如果返回的还是挑战页，强制刷新cookie重试
                if text and len(text) < 500 and "ge_js_validator" in text:
                    self.cookie = ""
                    self._cookie_ts = 0
                    self._get_cookie()
                    r = sess.get(url, timeout=15)
                    text = r.text
                return text
            except Exception:
                return ""
        else:
            # urllib兜底
            import urllib.request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            if self.cookie:
                headers["Cookie"] = self.cookie
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    charset = "utf-8"
                    ct = resp.headers.get("Content-Type", "")
                    if "charset=" in ct:
                        charset = ct.split("charset=")[-1].split(";")[0].strip()
                    return data.decode(charset, errors="ignore")
            except Exception:
                return ""

    def _parse_list(self, html):
        """解析视频列表"""
        result = []
        pattern = re.compile(
            r'<div class="item">.*?<a[^>]*href="(/voddetail/(\d+)\.html)"[^>]*title="([^"]*)".*?data-original="([^"]*)".*?</div>',
            re.S
        )
        for m in pattern.finditer(html):
            vod_id = m.group(2)
            vod_name = html_mod.unescape(m.group(3).strip())
            vod_pic = m.group(4)
            if vod_pic.startswith("//"):
                vod_pic = "https:" + vod_pic
            result.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": "",
            })
        return result

    def _get_total(self, html):
        """获取总条数"""
        pages = re.findall(r'/vodtype/\d+-(\d+)\.html', html)
        if pages:
            max_page = max(int(p) for p in pages)
            return max_page * 24
        pages = re.findall(r'----------(\d+)---\.html', html)
        if pages:
            max_page = max(int(p) for p in pages)
            return max_page * 24
        return 0

    def homeContent(self, *args):
        """首页内容"""
        result = {}
        classes = self._get_classes()
        result["class"] = classes
        html = self._req(self.siteUrl + "/vodtype/11.html")
        videos = self._parse_list(html)
        result["list"] = videos
        filters = {}
        for c in classes:
            filters[c["type_id"]] = []
        result["filters"] = filters
        return result

    def _get_classes(self):
        """获取分类列表"""
        html = self._req(self.siteUrl + "/vodtype/11.html")
        classes = []
        seen = set()
        pattern = re.compile(r'<a[^>]*href="/vodtype/(\d+)\.html"[^>]*>([^<]+)</a>')
        for m in pattern.finditer(html):
            tid = m.group(1)
            tname = html_mod.unescape(m.group(2).strip())
            if tname and tid not in seen and len(tname) < 20:
                minor_keywords = ['萝莉', '幼女', '少女', '童', 'teen', 'loli', 'schoolgirl', '豆蔻', '玉蕊', '碧玉', '稚子']
                if any(kw.lower() in tname.lower() for kw in minor_keywords):
                    continue
                seen.add(tid)
                classes.append({"type_id": tid, "type_name": tname})
        return classes

    def categoryContent(self, tid, pg, *args):
        """分类内容"""
        if not pg or pg == "1":
            url = self.siteUrl + f"/vodtype/{tid}.html"
        else:
            url = self.siteUrl + f"/vodtype/{tid}-{pg}.html"
        html = self._req(url)
        videos = self._parse_list(html)
        total = self._get_total(html)
        pagecount = (total + 23) // 24 if total > 0 else 1
        return {
            "page": int(pg) if pg else 1,
            "pagecount": pagecount,
            "limit": 24,
            "total": total,
            "list": videos,
        }

    def detailContent(self, array):
        """详情内容"""
        if not array:
            return {"list": []}
        vod_id = str(array[0])
        url = self.siteUrl + f"/voddetail/{vod_id}.html"
        html = self._req(url)
        if not html:
            return {"list": []}

        title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        vod_name = html_mod.unescape(title_m.group(1).strip()) if title_m else ""
        if not vod_name:
            title_m = re.search(r'<title>(.*?)</title>', html, re.S)
            if title_m:
                vod_name = html_mod.unescape(title_m.group(1).split("-")[0].strip())

        pic_m = re.search(r'data-original="([^"]+)"', html)
        vod_pic = pic_m.group(1) if pic_m else ""
        if vod_pic.startswith("//"):
            vod_pic = "https:" + vod_pic

        content_m = re.search(r'class="detail-content[^"]*"[^>]*>(.*?)</div>', html, re.S)
        vod_content = ""
        if content_m:
            vod_content = re.sub(r'<[^>]+>', '', content_m.group(1)).strip()

        vod_play_from = ""
        vod_play_url = ""

        play_pattern = re.compile(r'/vodplay/' + re.escape(vod_id) + r'-(\d+)-(\d+)\.html')
        play_links = {}
        for m in play_pattern.finditer(html):
            sid = m.group(1)
            nid = m.group(2)
            if sid not in play_links:
                play_links[sid] = set()
            play_links[sid].add(nid)

        if play_links:
            sources = []
            urls = []
            for sid in sorted(play_links.keys(), key=int):
                eps = sorted(play_links[sid], key=int)
                ep_list = []
                for nid in eps:
                    ep_list.append(f"第{nid}集${self.siteUrl}/vodplay/{vod_id}-{sid}-{nid}.html")
                sources.append(f"源{sid}")
                urls.append("#".join(ep_list))
            vod_play_from = "$$$".join(sources)
            vod_play_url = "$$$".join(urls)
        else:
            vod_play_from = "默认"
            vod_play_url = f"第1集${self.siteUrl}/vodplay/{vod_id}-1-1.html"

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_content": vod_content,
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        """播放内容 - 从播放页提取m3u8"""
        if not id:
            return {"parse": 0, "jx": 0, "url": "", "header": {}}

        play_url = id if id.startswith("http") else self.siteUrl + id
        html = self._req(play_url)
        if not html:
            return {"parse": 0, "jx": 0, "url": "", "header": {}}

        video_url = ""
        m = re.search(r'var player_aaaa\s*=\s*(\{.*?\});', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                enc_url = data.get("url", "")
                if enc_url:
                    video_url = urllib.parse.unquote(enc_url)
            except Exception:
                url_m = re.search(r'"url"\s*:\s*"([^"]+)"', m.group(1))
                if url_m:
                    video_url = urllib.parse.unquote(url_m.group(1))

        if not video_url:
            m3u8_m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
            if m3u8_m:
                video_url = m3u8_m.group(1)

        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": self.rawSite + "/",
            "Origin": self.rawSite,
        }

        return {
            "parse": 0,
            "jx": 0,
            "url": video_url,
            "header": header,
        }

    def searchContent(self, wd, pg, *args):
        """搜索内容"""
        if not pg or pg == "1":
            url = self.siteUrl + f"/vodsearch/{urllib.parse.quote(wd)}----------1---.html"
        else:
            url = self.siteUrl + f"/vodsearch/{urllib.parse.quote(wd)}----------{pg}---.html"
        html = self._req(url)
        videos = self._parse_list(html)
        total = self._get_total(html)
        pagecount = (total + 23) // 24 if total > 0 else 1
        return {
            "page": int(pg) if pg else 1,
            "pagecount": pagecount,
            "limit": 24,
            "total": total,
            "list": videos,
        }

    def getDependence(self, *args):
        return ""

    def localProxy(self, *args):
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        return url.endswith(".m3u8") or url.endswith(".mp4")

    def manualVideoCheck(self):
        return False

    def getName(self):
        return "PUA独家"

    def getApp(self):
        return "PUA独家"
