import os
import json

# 基础的 GitHub 原始链接路径
RAW_BASE_URL = "https://raw.githubusercontent.com/edc8/jav/main"
# 代理加速前缀
PROXY_URL = "https://gh-proxy.org/"

def generate_config():
    sites = []
    # 检查 18 文件夹是否存在
    target_dir = '18' if os.path.exists('18') else '.'
    
    for filename in os.listdir(target_dir):
        if filename.endswith('.py') and filename != 'generate.py':
            name = filename[:-3]
            
            # 针对每个具体的 py 文件拼接完整的直链，并加上代理加速前缀
            if target_dir == '18':
                file_raw_url = f"{RAW_BASE_URL}/18/{filename}"
            else:
                file_raw_url = f"{RAW_BASE_URL}/{filename}"
                
            accelerated_api = f"{PROXY_URL}{file_raw_url}"
            
            site = {
                "key": f"py_{name}",
                "name": f"🐍 {name}",
                "type": 3,
                "api": accelerated_api,
                "searchable": 1,
                "quickSearch": 1,
                "filterable": 1
            }
            sites.append(site)

    # 根目录下的 jar 包同样使用代理加速
    config = {
        "spider": f"{PROXY_URL}{RAW_BASE_URL}/custom_spider.jar",
        "sites": sites,
        "parses": [],
        "rules": []
    }

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    print(f"成功生成 output.json，共包含 {len(sites)} 个加速 Python 蜘蛛源。")

if __name__ == '__main__':
    generate_config()
