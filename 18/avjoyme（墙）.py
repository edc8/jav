#coding=utf-8
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
TVBox / Pyramid Spider for cn.avjoy.me
严格符合 Pyramid 规范，所有必须方法均实现。
播放地址采用实时抓取详情页提取当前有效 MP4（解决 token 时效问题）。
"""

import re
import sys
import json
from urllib.parse import quote, urljoin, urlparse

sys.path.append('../../')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://cn.avjoy.me'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://cn.avjoy.me/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def getName(self):
        return "AVJoy"

    def init(self, extend=""):
        self.extend = extend or ""
        return

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(mp4|m3u8)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        """首页分类"""
        result = {}
        # 固定常用分类（从站点侧边栏提取）
        cateManual = {
            "最受欢迎": "videos?o=mv",
            "最新": "videos?o=mr",
            "最多观看": "videos?o=vp",
            "JAV": "categories/jav",
            "Amateur": "categories/amateur",
            "Anal": "categories/anal",
            "Asian": "categories/asian",
            "Big Tits": "categories/big-tits",
            "China": "categories/china",
            "Japan": "categories/japan",
            "Uncensored": "categories/uncensored",
            "Mature": "categories/mature",
        }
        classes = []
        for k, v in cateManual.items():
            classes.append({
                'type_id': v,
                'type_name': k
            })
        result['class'] = classes
        return result

    def homeVideoContent(self):
        """首页推荐（取最受欢迎第一页）"""
        return self.categoryContent('videos?o=mv', '1', False, {})

    def categoryContent(self, tid, pg, filter, extend):
        """分类/列表"""
        result = {}
        page = int(pg) if pg else 1
        if page < 1:
            page = 1

        # 构造列表 URL
        if tid.startswith('videos') or tid.startswith('categories') or tid.startswith('search'):
            url = f"{self.siteUrl}/{tid}"
        else:
            url = f"{self.siteUrl}/videos?o=mv"

        if page > 1:
            if '?' in url:
                url += f"&page={page}"
            else:
                url += f"?page={page}"

        try:
            rsp = self.fetch(url, headers=self.headers)
            html = rsp.text
        except Exception as e:
            print(f"categoryContent error: {e}")
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 20, 'total': 0}

        videos = []
        # 匹配视频卡片：/video/{id}/{slug}
        pattern = r'href="(/video/(\d+)/[^"]+)"[^>]*>.*?<img[^>]+(?:src|data-src)="([^"]+)"[^>]*(?:alt="([^"]*)")?'
        # 更稳健的匹配
        items = re.findall(
            r'<a[^>]+href="(/video/(\d+)/[^"]+)"[^>]*>[\s\S]*?<img[^>]+(?:src|data-src)="([^"]+avjoytmb[^"]+)"[^>]*(?:alt="([^"]*)")?[\s\S]*?</a>',
            html, re.I
        )
        if not items:
            # 备用匹配
            items = re.findall(
                r'href="(/video/(\d+)/[^"]+)"[^>]*title="([^"]*)"[^>]*>[\s\S]*?src="([^"]+avjoytmb[^"]+)"',
                html, re.I
            )
            for href, vid, title, pic in items:
                videos.append({
                    'vod_id': vid,
                    'vod_name': title.strip() or f'视频{vid}',
                    'vod_pic': urljoin(self.siteUrl, pic),
                    'vod_remarks': ''
                })
        else:
            for href, vid, pic, title in items:
                videos.append({
                    'vod_id': vid,
                    'vod_name': (title or '').strip() or f'视频{vid}',
                    'vod_pic': urljoin(self.siteUrl, pic),
                    'vod_remarks': ''
                })

        # 去重
        seen = set()
        unique = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique.append(v)

        # 粗略分页（站点显示总数，这里估算）
        total_match = re.search(r'显示\s*\d+\s*到\s*\d+\s*of\s*([\d,]+)', html)
        total = 20000
        if total_match:
            total = int(total_match.group(1).replace(',', ''))
        pagecount = max(1, (total + 15) // 16)

        result['list'] = unique
        result['page'] = page
        result['pagecount'] = pagecount
        result['limit'] = 16
        result['total'] = total
        return result

    def detailContent(self, ids):
        """详情"""
        vid = ids[0] if isinstance(ids, list) else ids
        url = f"{self.siteUrl}/video/{vid}/"

        try:
            rsp = self.fetch(url, headers=self.headers)
            html = rsp.text
        except Exception as e:
            print(f"detailContent error: {e}")
            return {'list': []}

        # 标题
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.I) or \
                      re.search(r'<title>([^<]+)</title>', html, re.I)
        title = title_match.group(1).strip() if title_match else f'视频{vid}'
        title = re.sub(r'\s*-\s*AVJOY.*$', '', title).strip()

        # 封面
        pic_match = re.search(r'(https?://[^"\']+avjoytmb[^"\']+\.(?:jpg|jpeg|png|webp))', html, re.I)
        pic = pic_match.group(1) if pic_match else ''

        # 简介/标签
        tags = re.findall(r'标签[:：]\s*([^<\n]+)', html)
        content = tags[0].strip() if tags else ''

        # 播放源：直接使用详情页本身，playerContent 再实时取地址
        # 这样保证 token 永远是最新的
        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_content': content,
            'vod_play_from': 'AVJoy',
            'vod_play_url': f'正片${vid}'   # id 传给 playerContent
        }
        return {'list': [vod]}

    def searchContent(self, key, quick):
        return self.searchContentPage(key, quick, '1')

    def searchContentPage(self, key, quick, page):
        """搜索"""
        page = int(page) if page else 1
        q = quote(key)
        tid = f'search/videos/{q}'
        return self.categoryContent(tid, str(page), False, {})

    def playerContent(self, flag, id, vipFlags):
        """
        播放：实时重新抓取详情页，提取当前有效的 MP4 地址。
        这样 token 始终是最新的，解决时效问题。
        """
        vid = id
        # 如果 id 是完整 URL，直接用
        if id.startswith('http'):
            return {
                'parse': 0,
                'url': id,
                'header': self.headers
            }

        detail_url = f"{self.siteUrl}/video/{vid}/"
        try:
            rsp = self.fetch(detail_url, headers=self.headers)
            html = rsp.text
        except Exception as e:
            print(f"playerContent fetch error: {e}")
            return {'parse': 0, 'url': '', 'header': self.headers}

        # 提取当前有效的 MP4 直链
        mp4_pattern = r'https?://media-cdn\d*\.avjoy\.me/video/[^"\'\s]+?\.mp4'
        matches = re.findall(mp4_pattern, html, re.I)
        if matches:
            play_url = matches[0]
            # 清理可能的多余字符
            play_url = play_url.split('"')[0].split("'")[0].split(' ')[0]
            return {
                'parse': 0,
                'url': play_url,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': detail_url,
                }
            }

        # 备用：尝试找其他可能的视频源
        alt = re.search(r'(https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)', html, re.I)
        if alt:
            return {
                'parse': 0,
                'url': alt.group(1),
                'header': self.headers
            }

        return {'parse': 0, 'url': '', 'header': self.headers}

    def localProxy(self, param):
        return None

    def fetch(self, url, headers=None, cookies=None):
        import requests
        if headers is None:
            headers = self.headers
        rsp = requests.get(url, headers=headers, timeout=15, verify=False)
        rsp.encoding = 'utf-8'
        return rsp
