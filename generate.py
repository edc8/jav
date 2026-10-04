import os
import json

# 如果你的 .py 文件已经移动到了 18 文件夹，这里需要加上 /18
BASE_URL = "https://raw.githubusercontent.com/edc8/jav/main/18"

def generate_config():
    sites = []
    # 如果你的脚本也在根目录，而 py 文件在 18 文件夹，需要遍历 18 目录
    target_dir = '18' if os.path.exists('18') else '.'
    
    for filename in os.listdir(target_dir):
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

    # 已将 jar 包引用修改为指定的代理加速地址
    config = {
        "spider": "https://gh-proxy.org/https://raw.githubusercontent.com/edc8/jav/main/custom_spider.jar",
        "sites": sites,
        "parses": [],
        "rules": []
    }

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    print(f"成功生成 output.json，共包含 {len(sites)} 个 Python 蜘蛛源。")

if __name__ == '__main__':
    generate_config()
