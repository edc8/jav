# -*- coding: utf-8 -*-
# FongMi/TVBox Python Spider - CEOTV ceotv1108.xyz
import re, json
from urllib.parse import urljoin, quote, unquote
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def fetch(self, url, headers=None, timeout=10):
            import requests, urllib3
            urllib3.disable_warnings()
            return requests.get(url, headers=headers, timeout=timeout, verify=False)
        def log(self, msg): print(msg)

class Spider(BaseSpider):
    def getName(self): return 'CEOTV'
    def getDependence(self): return []

    def init(self, extend=''):
        self.host = 'https://ceotv1108.xyz'
        self.headers = {
            'User-Agent':'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36',
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer':self.host + '/'
        }
        self.classes = [
            {'type_id':'1','type_name':'国产视频'}, {'type_id':'2','type_name':'中文字幕'},
            {'type_id':'3','type_name':'国产传媒'}, {'type_id':'4','type_name':'日本有码'},
            {'type_id':'5','type_name':'日本无码'}, {'type_id':'6','type_name':'欧美无码'},
            {'type_id':'7','type_name':'强奸乱伦'}, {'type_id':'8','type_name':'制服诱惑'},
            {'type_id':'9','type_name':'国产主播'}, {'type_id':'10','type_name':'激情动漫'},
            {'type_id':'11','type_name':'明星换脸'}, {'type_id':'12','type_name':'抖音视频'},
            {'type_id':'13','type_name':'女优明星'}, {'type_id':'14','type_name':'网曝黑料'},
            {'type_id':'15','type_name':'伦理三级'}, {'type_id':'16','type_name':'AV解说'},
            {'type_id':'17','type_name':'SM调教'}, {'type_id':'18','type_name':'人妖系列'}
        ]
        self.filters = {}

    def homeContent(self, filter): return {'class': self.classes, 'filters': self.filters if filter else {}}
    def homeVideoContent(self): return {'list': self.parseList(self.host + '/')}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or '1')
        url = self.host + ('/index.php/vod/type/id/%s.html' % tid if pg == '1' else '/index.php/vod/type/id/%s/page/%s.html' % (tid, pg))
        vods = self.parseList(url)
        return {'list': vods, 'page': int(pg), 'pagecount': 999999 if vods else int(pg), 'limit': 20, 'total': 999999 if vods else 0}

    def detailContent(self, ids):
        vid = ids[0]
        title, pic, content = '', '', ''
        if '|$|' in vid:
            parts = vid.split('|$|')
            vid = parts[0]
            title = unquote(parts[1]) if len(parts) > 1 else ''
            pic = parts[2] if len(parts) > 2 else ''
        try:
            txt = '' if (title and pic) else self.html(vid)
            if not title:
                m = re.search(r'var\s+player_\w+\s*=\s*(\{[\s\S]*?\})\s*</script>', txt, re.I)
                if m: title = (json.loads(m.group(1)).get('vod_data') or {}).get('vod_name','')
            if not title:
                title = self.clean(self.find1(txt, r'<title[^>]*>([\s\S]*?)(?:详情|在线观看|-)'))
            if not pic:
                pic = self.find1(txt, r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)') or self.find1(txt, r'<img[^>]+src=["\']([^"\']+)')
            content = self.clean(self.find1(txt, r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)'))
        except Exception as e:
            self.log('详情解析失败 %s' % e)
        if not title: title = '视频'
        vod = {'vod_id':vid, 'vod_name':title, 'vod_pic':self.fix(pic), 'type_name':'', 'vod_year':'', 'vod_area':'', 'vod_remarks':'直连', 'vod_actor':'', 'vod_director':'', 'vod_content':content or title, 'vod_play_from':'奥斯卡', 'vod_play_url':'播放$%s' % vid}
        return {'list':[vod]}

    def searchContent(self, key, quick, pg='1'):
        pg = str(pg or '1')
        path = '/index.php/vod/search.html?wd=' + quote(key or '') if pg == '1' else '/index.php/vod/search/page/%s/wd/%s.html' % (pg, quote(key or ''))
        vods = self.parseList(self.host + path)
        return {'list': vods, 'page': int(pg), 'total': len(vods)}

    def playerContent(self, flag, id, vipFlags):
        url = id
        try:
            if not self.isMedia(url):
                txt = self.html(id)
                m = re.search(r'var\s+player_\w+\s*=\s*(\{[\s\S]*?\})\s*</script>', txt, re.I)
                if m:
                    data = json.loads(m.group(1)); url = data.get('url') or id
                if not self.isMedia(url):
                    url = self.find1(txt, r'(https?://[^"\'<>\s]+?\.(?:m3u8|mp4)[^"\'<>\s]*)') or url
        except Exception as e:
            self.log('播放解析失败 %s' % e)
        if self.isMedia(url): return {'parse':0, 'url':url, 'header':self.playHeader(url)}
        return {'parse':1, 'url':id, 'header':self.headers}

    def parseList(self, url):
        try:
            txt = self.html(url)
            if self.isNoResult(txt): return []
            vods, seen = [], set()
            blocks = re.findall(r'<section[^>]+class=["\'][^"\']*item-box[^"\']*["\'][\s\S]*?</section>', txt, re.I)
            for block in blocks:
                href = self.fix(self.find1(block, r'<a[^>]+href=["\']([^"\']*?/index\.php/vod/play/id/\d+[^"\']*)'))
                if not href or href in seen: continue
                name = self.clean(self.find1(block, r'<h2[^>]*[\s\S]*?<a[^>]*>([\s\S]*?)</a>') or self.find1(block, r'title=["\']([^"\']+)') or self.find1(block, r'alt=["\']([^"\']+)'))
                pic = self.fix(self.find1(block, r'<img[^>]*?\sdata-src=["\']([^"\']+)') or self.find1(block, r'<img[^>]*?\sdata-original=["\']([^"\']+)') or self.find1(block, r'<img[^>]*?\ssrc=["\']([^"\']+)'))
                if 'dancing.gif' in pic or 'loading' in pic: pic = ''
                if not name: continue
                seen.add(href)
                vods.append({'vod_id':href+'|$|'+quote(name)+'|$|'+pic, 'vod_name':name, 'vod_pic':pic, 'vod_remarks':'直连'})
            if not vods:
                for m in re.finditer(r'<a[^>]+href=["\']([^"\']*?/index\.php/vod/play/id/\d+[^"\']*)["\'][^>]+title=["\']([^"\']+)', txt, re.I):
                    href = self.fix(m.group(1)); name = self.clean(m.group(2))
                    if href and name and href not in seen:
                        seen.add(href); vods.append({'vod_id':href+'|$|'+quote(name)+'|$|', 'vod_name':name, 'vod_pic':'', 'vod_remarks':'直连'})
            return vods
        except Exception as e:
            self.log('列表解析失败 %s %s' % (url, e)); return []

    def html(self, url):
        r = self.fetch(url, headers=self.headers, timeout=15)
        return r.content.decode('utf-8','ignore') if hasattr(r,'content') else getattr(r,'text','')
    def fix(self, url): return urljoin(self.host + '/', (url or '').replace('&amp;','&').strip()) if url else ''
    def find1(self, txt, pat):
        m = re.search(pat, txt or '', re.I); return m.group(1) if m else ''
    def clean(self, s):
        s = re.sub(r'<[^>]+>', ' ', s or ''); s = re.sub(r'\s+', ' ', s).strip(); return s[:120]
    def isMedia(self, url): return bool(re.search(r'\.(m3u8|mp4)(\?|$)', url or '', re.I))
    def isNoResult(self, txt): return bool(re.search(r'没有找到|暂无数据|搜索无结果|未找到|404 Not Found', txt or '', re.I))
    def playHeader(self, url): return {'User-Agent': self.headers['User-Agent'], 'Referer': self.host + '/'}
    def localProxy(self, param): return [404, 'text/plain', b'']
    def manualVideoCheck(self): return True
    def liveContent(self, url): return None
    def action(self, action): return None
    def destroy(self): return None

spider = Spider()
