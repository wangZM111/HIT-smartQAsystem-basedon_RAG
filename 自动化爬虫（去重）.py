import os
import json
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import tempfile
import embedding_json

# ========== 配置路径 ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
VISITED_PATH = os.path.join(current_dir, "数据库", "VISITED_PATH.json")
HISTORY_PATH = os.path.join(current_dir, "数据库", "hit_articles.json")

# ========== 网页解析 ==========
def get_urls(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
        article_links = []
        for link in links:
            href = link['href']
            if href.startswith('/article/'):
                article_links.append(f"网页网址") #项目不对外提供
        return article_links
    else:
        print(f"请求失败：{url}，状态码 {response.status_code}")
        return []

def extract_info(page):
    try:
        title = page.text_content('.article-title h3')
        content = page.text_content('.article-content')
        if title and content:
            return title.strip(), content.strip()
    except:
        pass
    return None, None

def all_urls(n=2):
    urls = []
    for i in range(n):
        url_parent = f'哈工大网页'
        #校内信息网点，本项目不提供直接地址
        urls += get_urls(url_parent)
    return urls

# ========== 状态管理 ==========
def load_visited_urls():
    """加载已访问的 URL、标题和内容"""
    if os.path.exists(VISITED_PATH):
        with open(VISITED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_visited_urls(visited):
    """保存已访问的 URL、标题和内容"""
    with open(VISITED_PATH, "w", encoding="utf-8") as f:
        json.dump(visited, f, ensure_ascii=False, indent=2)

def load_old_articles():
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_all_articles(all_articles):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

# ========== 主函数，支持传入 page 和页数 ==========
def run_spider(page, n_pages=2):
    visited_urls = load_visited_urls()
    urls = all_urls(n=n_pages)
    new_urls = [url for url in urls if url not in [entry["url"] for entry in visited_urls]]  # 检查新 URL
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 共发现 {len(new_urls)} 篇新文章")

    data_list = []

    for url in new_urls:
        try:
            page.goto(url)
            page.wait_for_selector('.article-title h3', timeout=10000)
            title, content = extract_info(page)
            if title and content:
                # 保存 URL、标题和内容
                data_list.append({
                    "url": url,
                    "title": title,
                    "content": content
                })
                visited_urls.append({
                    "url": url,
                    "title": title,
                })
                print(f"✅ 爬取成功：{title}")
            else:
                print(f"⚠️ 内容为空：{url}")
        except Exception as e:
            print(f"❌ 出错跳过：{url}，原因：{e}")
            continue

    old_data = load_old_articles()
    combined_data = old_data + data_list
    save_all_articles(combined_data)
    save_visited_urls(visited_urls)  # 保存更新后的 URL、标题和内容

    print(f"\n✅ 成功新增 {len(data_list)} 篇文章，总计：{len(combined_data)} 篇\n")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as tmp_file:
        json.dump(data_list, tmp_file, ensure_ascii=False, indent=2)
        temp_path = tmp_file.name

    print(f"📁 新增文章已保存至临时文件：{temp_path}")
    embedding_json.process_file_and_save_information(temp_path, window_size=300, step_size=150,flag=True)

    try:
        os.remove(temp_path)
        print(f"🧹 临时文件已删除：{temp_path}")
    except Exception as e:
        print(f"⚠️ 删除临时文件失败：{e}")


# ========== 调用入口 ==========
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HIT 新闻自动爬虫")
    parser.add_argument("--pages", type=int, default=2, help="爬取前几页（默认2页）")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 登录
        page.goto('登录页面') #项目不对外提供
        page.fill('input#username', '账号') #项目不对外提供
        page.fill('input#password', '密码') #项目不对外提供
        page.click('a#login_submit')
        page.wait_for_selector('.article-title h3')

        # 运行爬虫，指定页数
        run_spider(page, n_pages=2)

        browser.close()
