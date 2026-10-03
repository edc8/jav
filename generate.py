import glob
import json
import os

# 1. 自动获取当前目录下所有的 .py 文件
py_files = glob.glob("*.py")

sites = []
for file in py_files:
  # 排除生成脚本本身
  if file == "generate.py":
    continue

  # 提取文件名作为源名称 (去掉 .py 后缀)
  name_without_ext = os.path.splitext(file)[0]

  sites.append({
      "key": f"py_{name_without_ext}",
      "name": f"🐍 {name_without_ext}",
      "type": 3,
      "api": file,  # 直接指向该 py 文件的文件名
      "searchable": 1,
      "quickSearch": 1,
      "filterable": 1,
  })

# 2. 组装最终的 TVBox 配置结构
config = {
    "spider": "https://ghproxy.net/raw.githubusercontent.com/edc8/jav/main/spider.jar",
    "sites": sites,
    "parses": [],
    "rules": [],
}

# 3. 写入 output.json 文件
with open("output.json", "w", encoding="utf-8") as f:
  json.dump(config, f, ensure_ascii=False, indent=4)

print(
    f"成功自动扫描并加载了 {len(sites)} 个 Python 源，已更新 output.json！"
)
