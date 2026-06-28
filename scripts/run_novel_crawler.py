"""
小说爬虫 - 爬取前10章数据并保存到MongoDB
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 配置
NOVEL_URL = "https://tianyashuku.net/wangluo/1615/"
MAX_CHAPTERS = 10  # 爬取前10章
REQUEST_INTERVAL = 1.5

print(f"=== 天涯书库小说爬虫 ===")
print(f"URL: {NOVEL_URL}")
print(f"Max chapters: {MAX_CHAPTERS}")

# ======== 第一步: 测试网络请求 ========
print("\n--- Step 1: 测试网络连接 ---")
import httpx
try:
    resp = httpx.get(NOVEL_URL, timeout=15, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    print(f"HTTP {resp.status_code}, Size: {len(resp.text)} bytes")
    if resp.status_code != 200:
        print(f"ERROR: 网站返回 {resp.status_code}")
        sys.exit(1)
    # 保存HTML到临时文件供分析
    tmp_path = os.path.join(os.path.dirname(__file__), '..', 'tmp_novel_page.html')
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print(f"页面已保存到: {tmp_path}")
except Exception as e:
    print(f"ERROR: 网络请求失败: {e}")
    sys.exit(1)

# ======== 第二步: 解析目录页 ========
print("\n--- Step 2: 解析目录页 ---")
import re

# 从meta提取信息
def extract_meta(html, prop):
    for pattern in [
        rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]*content=["\']([^"\']*)["\']',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']{prop}["\']',
    ]:
        m = re.search(pattern, html)
        if m:
            return m.group(1).strip()
    return ''

novel_title = extract_meta(resp.text, 'og:novel:book_name')
novel_author = extract_meta(resp.text, 'og:novel:author')
novel_category = extract_meta(resp.text, 'og:novel:category')
novel_status = extract_meta(resp.text, 'og:novel:status')
novel_cover = extract_meta(resp.text, 'og:image')
novel_desc = extract_meta(resp.text, 'og:description')

print(f"书名: {novel_title}")
print(f"作者: {novel_author}")
print(f"分类: {novel_category}")
print(f"状态: {novel_status}")

# 提取章节列表
list_match = re.search(r'<div id="list">(.*?)</div>', resp.text, re.DOTALL)
if not list_match:
    print("ERROR: 未找到章节列表 div#list")
    # 保存部分内容供分析
    with open(tmp_path.replace('.html', '_debug.html'), 'w', encoding='utf-8') as f:
        f.write(resp.text[:10000])
    sys.exit(1)

links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', list_match.group(1))
print(f"发现章节: {len(links)} 章")

# 只取前10章
target_links = links[:MAX_CHAPTERS]
print(f"将爬取前 {len(target_links)} 章:")

# ======== 第三步: 爬取每章内容 ========
print("\n--- Step 3: 爬取章节内容 ---")
chapters = []
for i, (url, title) in enumerate(target_links):
    if url.startswith('/'):
        url = f'https://tianyashuku.net{url}'
    elif not url.startswith('http'):
        url = f'{NOVEL_URL}{url}'

    print(f"  [{i+1}/{len(target_links)}] {title.strip()}")
    print(f"       URL: {url}")

    try:
        ch_resp = httpx.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if ch_resp.status_code != 200:
            print(f"       ERROR: HTTP {ch_resp.status_code}")
            continue

        # 提取正文
        content = ''
        for pattern in [
            r'<div[^>]*class="content-body[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="m-article-text"[^>]*>(.*?)</div>',
        ]:
            m = re.search(pattern, ch_resp.text, re.DOTALL)
            if m:
                content = m.group(1)
                break

        if not content:
            print(f"       WARN: 未找到正文，保存HTML供分析")
            ch_tmp = tmp_path.replace('.html', f'_ch{i}.html')
            with open(ch_tmp, 'w', encoding='utf-8') as f:
                f.write(ch_resp.text)
            print(f"       已保存到: {ch_tmp}")
            continue

        # 清理HTML
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', '\n', content)
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        ad_keywords = ['推荐票', '月票', '收藏', '加入书签', '投推荐票', '手机阅读', '本章未完']
        clean_lines = [l for l in lines if not any(kw in l for kw in ad_keywords)]
        clean_content = '\n'.join(clean_lines)

        print(f"       正文: {len(clean_content)} 字")

        chapters.append({
            'chapter_index': i,
            'title': title.strip(),
            'url': url,
            'content': clean_content,
        })

    except Exception as e:
        print(f"       ERROR: {e}")
        continue

print(f"\n爬取完成: {len(chapters)}/{len(target_links)} 章")

if not chapters:
    print("ERROR: 未爬取到任何数据")
    sys.exit(1)

# ======== 第四步: 保存到MongoDB ========
print("\n--- Step 4: 保存到MongoDB ---")
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    import asyncio

    async def save_to_mongo():
        client = AsyncIOMotorClient('mongodb://mongo_5pnRDX:mongo_YsYryF@192.168.17.136:27017')
        db = client['jobs']
        collection = db['novels']

        novel_doc = {
            'novel_title': novel_title,
            'novel_author': novel_author,
            'novel_category': novel_category,
            'novel_status': novel_status,
            'novel_cover': novel_cover,
            'novel_desc': novel_desc,
            'source_url': NOVEL_URL,
            'total_chapters': len(links),
            'chapters': chapters,
            'crawl_time': asyncio.get_event_loop().time(),
        }

        # 检查是否已存在
        existing = await collection.find_one({'novel_title': novel_title})
        if existing:
            print(f"小说 '{novel_title}' 已存在，更新章节...")
            # 合并已有章节和新章节
            existing_chapters = existing.get('chapters', [])
            existing_indices = {c['chapter_index'] for c in existing_chapters}
            new_chs = [c for c in chapters if c['chapter_index'] not in existing_indices]
            if new_chs:
                await collection.update_one(
                    {'novel_title': novel_title},
                    {'$push': {'chapters': {'$each': new_chs}}}
                )
                print(f"新增 {len(new_chs)} 章")
            else:
                print("所有章节已存在")
        else:
            await collection.insert_one(novel_doc)
            print(f"小说 '{novel_title}' 已插入 MongoDB ({len(chapters)} 章)")

        # 验证
        count = await collection.count_documents({})
        print(f"MongoDB novels 集合总文档数: {count}")
        await client.close()

    asyncio.run(save_to_mongo())

except ImportError:
    print("Motor 未安装，保存到本地JSON文件...")
    # Fallback to JSON file
    novel_doc = {
        'novel_title': novel_title,
        'novel_author': novel_author,
        'novel_category': novel_category,
        'novel_status': novel_status,
        'novel_cover': novel_cover,
        'novel_desc': novel_desc,
        'source_url': NOVEL_URL,
        'total_chapters': len(links),
        'chapters': chapters,
    }
    save_path = tmp_path.replace('.html', '_data.json')
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(novel_doc, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {save_path}")

print("\n=== 完成 ===")
