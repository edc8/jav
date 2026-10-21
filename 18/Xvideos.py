# -*- coding: utf-8 -*-
# 四壳通用Python Spider - Xvideos.com
# 双协议兼容继承base.spider，13接口齐全

try:
    from base.spider import Spider
except ImportError:
    class _BaseSpider:
        def init(self, extend=""): pass
    class Spider(_BaseSpider):
        pass

import requests
from urllib.parse import urljoin, quote
import re

class XvideosSpider(Spider):
    def getDependence(self):
        return "xvideos.com"
    
    def init(self, extend=""):
        self.rawSite = "https://www.xvideos.com/"
        self.siteUrl = "https://xsz-shared-proxy.97471201.workers.dev"
        self.HOST = self.siteUrl
        self.timeout = 10
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.rawSite + '/',
            'Origin': self.rawSite
        }
    
    def homeContent(self, *args):
        url = self.siteUrl + "/vodshow"
        resp = self.request(url)
        if not resp:
            return {"class": [], "filters": []}
        
        classes = []
        filters = {}
        
        # 解析分类
        class_list = re.findall(r'"type_id":"([^"]+)","type_name":"([^"]+)"', resp.text)
        for tid, type_name in class_list:
            classes.append({"type_id": tid, "type_name": type_name})
            filters[tid] = [{"key": "sort", "name": "排序", "init": "", 
                           "value": [{"n": "最新", "v": "new"}, {"n": "热度", "v": "hot"}]}]
        
        return {"class": classes, "filters": filters, "list": []}
    
    def categoryContent(self, tid, page=1):
        url = self.siteUrl + f"/vodshow/{quote(tid)}--------fypage---/"
        resp = self.request(url)
        if not resp:
            return {"page": page, "pagecount": 0, "limit": 20, "total": 0, "list": []}
        
        list = []
        pagecount = 1
        total = 0
        
        # 解析视频列表
        video_items = re.findall(r'"vod_id":"([^"]+)"|"vod_name":"([^"]+)"|"vod_pic":"([^"]+)"|"vod_remarks":"([^"]+)"|"vod_play_from":"([^"]+)"|"vod_play_url":"([^"]+)"',