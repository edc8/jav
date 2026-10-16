# coding=utf-8
import sys
import json
import re
import requests
from bs4 import BeautifulSoup

class Spider(object):
    def getName(self):
        return "每日大赛"

    def init(self, extend=""):
        pass

    def home(self, filter):
        result = {}
        # 严格对齐网站的实际分类目录
        classes = [
            {"type_id": "mrds", "type_name": "每日大赛"},
            {"type_id": "ztds", "type_name": "主题大赛"},
            {"type_id": "rstt", "type_name": "热搜吃瓜"},
            {"type_id": "xazd", "type_name": "校园学生"},
            {"type_id": "blyp", "type_name": "必撸大赛"},
            {"type_id": "fctg", "type_name": "反差泄密"},
            {"type_id": "mhds", "type_name": "网红黑料"},
            {"type_id": "lqdp", "type_name": "猎奇重口"}
        ]
        result['class'] = classes
        return result

    def homeVideo(self):
        return {"list": []}

    def category(self, tid, page, filter, extend):
        url = f"https://www.mrds66.com/category/{tid}/page/{page}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.mrds66.com/'
        }
        videos = []
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for item in soup.select('article'):
                    a = item.find('a', href=True)
                    img = item.find('img')
                    if a:
                        title = a.get('title') or a.get_text(strip=True)
                        link = a['href']
                        if not link.startswith('http'):
                            continue
                        pic = ""
                        if img:
                            pic = img.get('data-original') or img.get('src') or ""
                        videos.append({
                            "vod_id": link,
                            "vod_name": title,
                            "vod_pic": pic,
                            "vod_remarks": "高清"
                        })
        except Exception as e:
            print(f"[TVBox Python Error] Category fetch failed: {e}")
            
        return {
            "list": videos,
            "page": int(page),
            "pagecount": 999,
            "limit": 12,
            "total": 9999
        }

    def detail(self, id):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.mrds66.com/'
        }
        vod = {}
        play_url = id
        try:
            res = requests.get(id, headers=headers, timeout=12)
            if res.status_code == 200:
                html = res.text
                soup = BeautifulSoup(html, 'html.parser')
                title_node = soup.find('h1')
                title = title_node.get_text(strip=True) if title_node else "未知标题"
                
                content_elem = soup.select_one('.article-content')
                content_text = content_elem.get_text(strip=True) if content_elem else ""
                
                # 正则试探匹配真实视频直链（m3u8/mp4）
                m3u8_match = re.search(r'(https?://[^\s<>"]+?\.(?:m3u8|mp4))', html)
                if m3u8_match:
                    play_url = m3u8_match.group(1)
                else:
                    iframe_match = re.search(r'src=["\'](https?://[^"\']+?\.(?:m3u8|mp4|html)[^"\']*?)["\']', html)
                    if iframe_match:
                        play_url = iframe_match.group(1)

                vod = {
                    "vod_id": id,
                    "vod_name": title,
                    "vod_type": "吃瓜爆料",
                    "vod_content": content_text,
                    "vod_play_from": "默认线路",
                    "vod_play_url": f"正片${play_url}"
                }
        except Exception as e:
            print(f"[TVBox Python Error] Detail fetch failed: {e}")
            
        return {"list": [vod]}

    def play(self, flag, id, flags):
        if any(ext in id for ext in ['.m3u8', '.mp4']):
            return {"parse": 0, "jx": 0, "url": id}
        return {
            "parse": 1,
            "jx": 1,
            "url": id
        }

    def search(self, wd, quick):
        videos = []
        try:
            url = f"https://www.mrds66.com/search/{wd}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.mrds66.com/'
            }
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for item in soup.select('article'):
                    a = item.find('a', href=True)
                    img = item.find('img')
                    if a:
                        title = a.get('title') or a.get_text(strip=True)
                        link = a['href']
                        if not link.startswith('http'):
                            continue
                        pic = ""
                        if img:
                            pic = img.get('data-original') or img.get('src') or ""
                        videos.append({
                            "vod_id": link,
                            "vod_name": title,
                            "vod_pic": pic,
                            "vod_remarks": "搜索"
                        })
        except Exception as e:
            print(f"[TVBox Python Error] Search failed: {e}")
            
        return {"list": videos}