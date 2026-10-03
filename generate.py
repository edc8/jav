import os
import json

BASE_URL = "https://raw.githubusercontent.com/edc8/jav/main"

def generate_config():
    sites = []
    for filename in os.listdir('.'):
        if filename.endswith('.py') and filename != 'generate.py':
            name = filename[:-3]
            site = {
                "key": f"py_{name}",
                "name": f"🐍 {name}",
                "type": 3,
                "api": f"{BASE_URL}/{filename}",
                "searchable": 1,
                "quickSearch": 1,
                "filterable": 1
            }
            sites.append(site)

    # 借用网络上公开稳定的 jar 综合解析包
    config = {
        "spider": "https://raw.githubusercontent.com/fantaiying/ext/main/jar/custom_spider.jar",
        "sites": sites,
        "parses": [],
        "rules": []
    }

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    print(f"成功生成 output.json，共包含 {len(sites)} 个 Python 蜘蛛源。")

if __name__ == '__main__':
    generate_config()
