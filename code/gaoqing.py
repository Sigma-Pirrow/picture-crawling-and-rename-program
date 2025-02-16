import requests
from bs4 import BeautifulSoup
import os
from PIL import Image
from io import BytesIO
import re
import json
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# 确保有一个文件夹来存储图片
os.makedirs('images', exist_ok=True)

# 读取文本文件
with open('insects.txt', 'r', encoding='utf-8') as file:
    lines = file.readlines()

# 设置重试策略
retry_strategy = Retry(
    total=3,  # 总共重试3次
    backoff_factor=1,  # 重试间隔时间因子
    status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
    allowed_methods=["HEAD", "GET", "OPTIONS"]  # 需要重试的请求方法
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

for line in lines:
    # 提取中文部分
    chinese_name = ''.join(filter(lambda x: u'\u4e00' <= x <= u'\u9fff', line))
    
    # 使用中文名进行搜索
    search_url = f"https://cn.bing.com/images/async?q={chinese_name}"  # 替换为实际的搜索引擎URL
    
    try:
        response = http.get(search_url)
        response.raise_for_status()  # 检查请求是否成功
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch search results for {chinese_name}: {e}")
        continue

    soup = BeautifulSoup(response.text, 'html.parser')

    # 找到前五张图片的URL（具体选择器需要根据实际网页结构调整）
    image_tags = soup.find_all('a', {'class': 'iusc'}, limit=3)
    image_urls = []

    for tag in image_tags:
        try:
            m_data = json.loads(tag['m'])
            image_url = m_data.get('murl')
            if image_url and not re.match(r'^data:', image_url):
                image_urls.append(image_url)
        except (KeyError, json.JSONDecodeError):
            continue

    if image_urls:
        best_image_url = None
        best_image_pixels = 0

        # 尝试下载图片，直到成功或所有图片都尝试完毕
        for selected_image_url in image_urls:
            try:
                img_response = http.get(selected_image_url)
                img_response.raise_for_status()  # 检查请求是否成功
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch image from URL: {selected_image_url}: {e}")
                continue
            
            try:
                img = Image.open(BytesIO(img_response.content))
                # 如果图片是RGBA模式，转换为RGB模式
                if img.mode == 'RGBA':
                    img = img.convert('RGB')

                # 计算总像素
                img_pixels = img.width * img.height

                # 更新最佳图片
                if img_pixels > best_image_pixels:
                    best_image_url = selected_image_url
                    best_image_pixels = img_pixels
                    best_img = img
            except IOError:
                print(f"Failed to open image from URL: {selected_image_url}")
                continue
        
        if best_image_url:
            # 保存最佳图片
            img_name = line.strip() + '.jpg'
            best_img.save(os.path.join('images', img_name))
            print(f"Saved {img_name}")
        else:
            print(f"No valid image URL found for {chinese_name}")
    else:
        print(f"No valid image URL found for {chinese_name}")