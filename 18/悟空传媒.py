# -*- coding: utf-8 -*-
# 悟空传媒 TVBox 四壳通用 Python Spider
# 站点: https://vfjrmiqa.wkavav260.sbs
# 结构: 自定义CMS(苹果CMS内核), 详情/play/{id}, 播放/v-p/{id}-{line}-{ep}, 分类/vod/{id}, 搜索/sou/-.html
# 播放: player_data JSON 直出 m3u8 (encrypt=0)

import re
import json
import urllib.parse

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def __init__(self):
            self.extend = {}

# ==================== 未成年过滤关键词 ====================
MINOR_KEYWORDS = ['萝莉', '幼女', '少女', '童', 'teen', 'loli', 'schoolgirl', '未成年']

def is_minor(text):
    if not text:
        return False
    t = text.lower()
    return any(kw.lower() in t for kw in MINOR_KEYWORDS)

# ==================== 分类配置 ====================
CATEGORIES = [
    {"type_id": "1", "type_name": "国产"},
    {"type_id": "2", "type_name": "网红"},
    # {"type_id": "3", "type_name": "萝莉"},  # 铁律13: 未成年跳过
    {"type_id": "4", "type_name": "大秀"},
    {"type_id": "5", "type_name": "探花"},
    {"type_id": "6", "type_name": "自拍"},
    {"type_id": "7", "type_name": "乱伦毁三观"},
    {"type_id": "8", "type_name": "强奸"},
    {"type_id": "9", "type_name": "传媒"},
    {"type_id": "10", "type_name": "反差婊"},
    {"type_id": "11", "type_name": "网爆门"},
    {"type_id": "12", "type_name": "偷拍"},
    {"type_id": "13", "type_name": "福利姬"},
    {"type_id": "14", "type_name": "吃瓜"},
    {"type_id": "15", "type_name": "大学生"},
    {"type_id": "16", "type_name": "人兽"},
    {"type_id": "17", "type_name": "人妖"},
    {"type_id": "18", "type_name": "OnlyFans"},
    {"type_id": "20", "type_name": "喷水"},
    {"type_id": "21", "type_name": "裸贷"},
    {"type_id": "22", "type_name": "性虐"},
    {"type_id": "23", "type_name": "AI换脸"},
    {"type_id": "24", "type_name": "无码"},
    {"type_id": "25", "type_name": "中文字幕"},
    {"type_id": "26", "type_name": "欧美"},
    {"type_id": "27", "type_name": "动漫"},
    {"type_id": "28", "type_name": "三级片"},
    {"type_id": "29", "type_name": "AV解说"},
    {"type_id": "30", "type_name": "兄弟姐妹"},
    {"type_id": "31", "type_name": "禁忌母子"},
    {"type_id": "32", "type_name": "狂操小姨"},
    {"type_id": "33", "type_name": "猛干嫂子"},
    {"type_id": "34", "type_name": "野外车震"},
    {"type_id": "35", "type_name": "夫妻交换"},
    {"type_id": "36", "type_name": "淫荡儿媳"},
    {"type_id": "37", "type_name": "学生下海"},
    {"type_id": "38", "type_name": "瑜伽裤"},
    {"type_id": "39", "type_name": "兽耳系列"},
    {"type_id": "40", "type_name": "多人群P"},
    {"type_id": "41", "type_name": "Cosplay"},
]

FILTER_VALUES = {
    "class": "tid",
}


class Spider(Spider):
    # ==================== 基础配置 ====================
    def __init__(self):
        super().__init__()
        self.siteUrl = "https://vfjrmiqa.wkavav260.sbs"
        self.rawSite = "https://vfjrmiqa.wkavav260.sbs"
        self.HOST = self.siteUrl
        self.cookies = {}
        self._session = None

    def init(self, extend=""):
        if extend and isinstance(extend, str):
            try:
                self.extend = json.loads(extend)
            except Exception:
                self.extend = {}
        elif isinstance(extend, dict):
            self.extend = extend
        else:
            self.extend = {}
        if self.extend.get("siteUrl"):
            self.siteUrl = self.extend["siteUrl"]
            self.HOST = self.siteUrl
        if self.extend.get("proxy"):
            self.siteUrl = self.extend["proxy"]
            self.HOST = self.siteUrl

    # ==================== HTTP 请求 ====================
    def _get_session(self):
        if self._session is None:
            if HAS_CURL_CFFI:
                self._session = curl_requests.Session(impersonate="chrome131")
            else:
                import requests as req_lib
                self._session = req_lib.Session()
                self._session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                })
        return self._session

    def _fetch(self, url, timeout=15):
        session = self._get_session()
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return ""

    def _abs_url(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.siteUrl + url
        return self.siteUrl + "/" + url

    # ==================== 解析视频卡片 ====================
    def _parse_cards(self, html):
        """解析 div.card 视频卡片列表"""
        vod_list = []
        # 匹配 card 容器
        card_pattern = re.compile(
            r'<div class="card">\s*'
            r'<a class="pic" href="(/play/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*style="background-image:url\(([^)]*)\)"[^>]*>(.*?)</a>\s*'
            r'<a class="title"[^>]*>(.*?)</a>',
            re.S
        )
        for m in card_pattern.finditer(html):
            vod_id = m.group(2)
            vod_name = m.group(3).strip()
            vod_pic = self._abs_url(m.group(4).strip())
            # 铁律13: 未成年跳过
            if is_minor(vod_name):
                continue
            # 提取备注(评分/标签)
            card_inner = m.group(5)
            badge = re.search(r'<span class="badge">([^<]+)</span>', card_inner)
            score = re.search(r'<span class="badge-score">([^<]+)</span>', card_inner)
            remarks = ""
            if score:
                remarks = score.group(1).strip()
            if badge:
                remarks = (remarks + " " if remarks else "") + badge.group(1).strip()
            vod_list.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": remarks,
            })
        return vod_list

    # ==================== 1. homeContent ====================
    def homeContent(self, *args):
        result = {}
        # 分类
        classes = []
        for cat in CATEGORIES:
            classes.append({
                "type_id": cat["type_id"],
                "type_name": cat["type_name"],
            })
        result["class"] = classes
        # filters
        filters = {}
        for cat in CATEGORIES:
            filters[cat["type_id"]] = []
        result["filters"] = filters
        # 首页推荐列表
        html = self._fetch(self.siteUrl + "/")
        vod_list = self._parse_cards(html)
        result["list"] = vod_list
        return result

    # ==================== 2. categoryContent ====================
    def categoryContent(self, tid, page=1, *args):
        result = {}
        # 分类URL: 第1页 /vod/{id}.html, 第N页 /vod/{id}-{page}.html
        if int(page) <= 1:
            url = f"{self.siteUrl}/vod/{tid}.html"
        else:
            url = f"{self.siteUrl}/vod/{tid}-{page}.html"
        html = self._fetch(url)
        vod_list = self._parse_cards(html)
        # 分页信息
        page = int(page)
        pagecount = 999
        limit = 16
        total = pagecount * limit
        result["page"] = page
        result["pagecount"] = pagecount
        result["limit"] = limit
        result["total"] = total
        result["list"] = vod_list
        return result

    # ==================== 3. detailContent ====================
    def detailContent(self, ids, *args):
        result = {}
        vod_list = []
        if isinstance(ids, str):
            ids = [ids]
        for vod_id in ids:
            if not vod_id:
                continue
            html = self._fetch(f"{self.siteUrl}/play/{vod_id}.html")
            if not html:
                continue
            # 标题
            title_m = re.search(r'<h1>(.*?)</h1>', html, re.S)
            vod_name = title_m.group(1).strip() if title_m else ""
            # 铁律13: 未成年跳过
            if is_minor(vod_name):
                continue
            # 封面
            poster_m = re.search(r'<div class="poster"><img src="([^"]+)"', html)
            vod_pic = self._abs_url(poster_m.group(1).strip()) if poster_m else ""
            # 分类
            cat_m = re.search(r'<p class="meta">类型：([^<]+)</p>', html)
            type_name = cat_m.group(1).strip() if cat_m else ""
            # 发布/更新
            pub_m = re.search(r'<p>发布：([^<]+)</p>', html)
            update_m = re.search(r'<p>更新：([^<]+)</p>', html)
            vod_remarks = ""
            if update_m:
                vod_remarks = update_m.group(1).strip()
            # 标签
            tags = re.findall(r'<a href="/tag/\d+\.html" rel="tag">([^<]+)</a>', html)
            vod_content = ""
            if tags:
                vod_content = "标签：" + "、".join(tags)
            # 播放线路
            line_plays = re.findall(
                r'<a[^>]*class="line-play"[^>]*href="(/v-p/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]+)</a>',
                html
            )
            if not line_plays:
                # 兜底: 直接构造默认播放地址
                line_plays = [(f"/v-p/{vod_id}-2-1.html", vod_id, "2", "1", "HD高清")]
            # 构造播放列表
            play_from_list = []
            play_url_list = []
            for href, lid, line, ep, line_name in line_plays:
                play_from_list.append(line_name.strip())
                # 播放地址格式: 集数$url
                play_url_list.append(f"第1集${href}")
            vod_play_from = "$$$".join(play_from_list)
            vod_play_url = "$$$".join(play_url_list)
            vod_list.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "type_name": type_name,
                "vod_remarks": vod_remarks,
                "vod_content": vod_content,
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
            })
        result["list"] = vod_list
        return result

    # ==================== 4. playerContent ====================
    def playerContent(self, flag, id, vipFlags=None, *args):
        result = {}
        # id 是播放页路径, 如 /v-p/309501-2-1.html
        if not id.startswith("http"):
            play_url = self._abs_url(id)
        else:
            play_url = id
        html = self._fetch(play_url)
        play_url_final = ""
        if html:
            # 提取 player_data (兼容 var player_data= 和 player_data= 两种写法)
            m = re.search(r'(?:var\s+)?player_data\s*=\s*', html)
            if m:
                start = m.end()
                # 大括号配对提取JSON
                depth = 0
                end = start
                for i in range(start, min(start + 5000, len(html))):
                    if html[i] == '{':
                        depth += 1
                    elif html[i] == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end > start:
                    try:
                        data = json.loads(html[start:end])
                        raw_url = data.get("url", "")
                        if data.get("encrypt") == 1 and raw_url:
                            raw_url = urllib.parse.unquote(raw_url)
                        play_url_final = raw_url
                    except Exception:
                        pass
            # 兜底: 直接正则提取m3u8
            if not play_url_final:
                m3u8_m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
                if m3u8_m:
                    play_url_final = m3u8_m.group(1)
        result["parse"] = 0
        result["jx"] = 0
        result["url"] = play_url_final
        result["header"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": self.rawSite + "/",
            "Origin": self.rawSite,
        }
        return result

    # ==================== 5. searchContent ====================
    def searchContent(self, key, page=1, *args):
        result = {}
        key_enc = urllib.parse.quote(key)
        url = f"{self.siteUrl}/sou/-.html?wd={key_enc}&page={page}"
        html = self._fetch(url)
        vod_list = self._parse_cards(html)
        page = int(page)
        result["page"] = page
        result["pagecount"] = 99
        result["limit"] = 16
        result["total"] = 99 * 16
        result["list"] = vod_list
        return result

    # ==================== 6. localProxy (m3u8广告清洗) ====================
    def localProxy(self, param):
        """本地代理: 接收m3u8代理请求, 下载清洗后返回"""
        try:
            if isinstance(param, str):
                params = urllib.parse.parse_qs(param)
            else:
                params = param or {}
            url = params.get("url", [""])[0] if isinstance(params, dict) else ""
            if not url:
                return [404, "text/plain", ""]
            # 下载m3u8
            html = self._fetch(url, timeout=10)
            if not html:
                return [404, "text/plain", "fetch failed"]
            # 清洗广告
            cleaned = self._clean_m3u8(html, url)
            return [200, "application/vnd.apple.mpegurl", cleaned]
        except Exception:
            return [404, "text/plain", ""]

    def _clean_m3u8(self, content, base_url=""):
        """m3u8广告清洗核心: 剔除广告ts, 重写序列号"""
        lines = content.split("\n")
        cleaned = []
        ad_count = 0
        seq_rewrite = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 广告段识别
            if self._is_ad_segment(line):
                ad_count += 1
                continue
            # 重写MEDIA-SEQUENCE
            if line.startswith("#EXT-X-MEDIA-SEQUENCE"):
                seq_rewrite = True
                cleaned.append("#EXT-X-MEDIA-SEQUENCE:0")
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    def _is_ad_segment(self, line):
        """广告段五重识别"""
        if not line or line.startswith("#"):
            return False
        # 关键词
        ad_keywords = ["ad", "gg", "adv", "preroll", "片头", "广告", "guanggao"]
        lower = line.lower()
        if any(kw in lower for kw in ad_keywords):
            return True
        return False

    # ==================== 7. 其他接口 ====================
    def isVideoFormat(self, url):
        return any(url.endswith(ext) for ext in [".m3u8", ".mp4", ".mkv", ".avi", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    def getDependence(self):
        return "悟空传媒 Spider loaded"

    def getName(self):
        return "悟空传媒"

    def destroy(self):
        self._session = None
