import os
import json
import time
import sys
from datetime import datetime

# 修改为你的日志路径
current_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(current_dir, "日志与反馈", "log.json")
VISITED_PATH = os.path.join(current_dir, "数据库", "VISITED_PATH.json")  # VISITED_PATH 路径

def load_visited_urls():
    """加载已访问的 URL"""
    if os.path.exists(VISITED_PATH):
        with open(VISITED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_visited_urls(visited):
    """保存已访问的 URL"""
    with open(VISITED_PATH, "w", encoding="utf-8") as f:
        json.dump(visited, f, ensure_ascii=False, indent=2)

def delete_files_in_time_range_str(start_time_str, end_time_str, time_format="%Y/%m/%d %H:%M:%S"):
    try:
        start_ts = time.mktime(datetime.strptime(start_time_str, time_format).timetuple())
        end_ts = time.mktime(datetime.strptime(end_time_str, time_format).timetuple())
    except Exception as e:
        print(f"❌ 时间格式错误：{e}")
        return

    if not os.path.exists(log_path):
        print("⚠️ 日志文件不存在")
        return

    with open(log_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)

    visited_urls = load_visited_urls()  # 加载已访问的 URL
    new_log = []
    deleted = 0

    for entry in log_data:
        ts = entry.get("timestamp", 0)
        if start_ts <= ts <= end_ts:
            try:
                os.remove(entry["file_path"])  # 删除文件
                print(f"✅ 已删除：{entry['file_name']}")
                deleted += 1

                # 检查并更新 VISITED_PATH，确保 entry 中有 'url' 字段
                if "url" in entry:
                    visited_urls = [v for v in visited_urls if v['url'] != entry['url']]  # 从 VISITED_PATH 中移除该 URL
                    print(f"✅ 更新 VISITED_PATH: 移除 URL {entry['url']}")

            except Exception as e:
                print(f"❌ 删除失败：{entry['file_name']} -> {e}")
        else:
            new_log.append(entry)

    # 保存更新后的 VISITED_PATH
    save_visited_urls(visited_urls)

    # 更新 log.json 文件
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(new_log, f, ensure_ascii=False, indent=2)

    print(f"\n🎯 共删除文件：{deleted} 个")

def delete_file_by_path(file_path):
    """根据输入的文件路径删除文件，并更新 VISITED_PATH"""
    visited_urls = load_visited_urls()

    # 检查日志中是否有对应的文件记录
    with open(log_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)

    # 遍历日志文件，找到对应文件并删除
    deleted = 0
    for entry in log_data:
        if entry["file_path"] == file_path:
            try:
                os.remove(file_path)
                print(f"✅ 文件删除成功：{entry['file_name']}")
                deleted += 1

                # 如果是爬虫获取的文件，更新 VISITED_PATH
                if "url" in entry:
                    visited_urls = [v for v in visited_urls if v['url'] != entry['url']]  # 从 VISITED_PATH 中移除该 URL
                    print(f"✅ 更新 VISITED_PATH: 移除 URL {entry['url']}")
                break
            except Exception as e:
                print(f"❌ 删除失败：{entry['file_name']} -> {e}")
                break

    if deleted > 0:
        # 保存更新后的 VISITED_PATH
        save_visited_urls(visited_urls)

        # 更新 log.json 文件
        with open(log_path, 'r', encoding='utf-8') as f:
            new_log = [entry for entry in log_data if entry["file_path"] != file_path]

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(new_log, f, ensure_ascii=False, indent=2)

    if deleted == 0:
        print("⚠️ 文件未找到或未被爬虫获取，未更新 VISITED_PATH。")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("用法: python delete_logs.py '起始时间' '终止时间' 或 python delete_logs.py --delete '文件路径'")
        sys.exit(1)

    # 如果提供了文件路径，直接删除该文件
    if sys.argv[1] == "--delete" and len(sys.argv) == 3:
        file_path = sys.argv[2]
        delete_file_by_path(file_path)
    # 如果提供了时间范围，则删除时间范围内的文件
    elif len(sys.argv) == 3:
        start_time_str = sys.argv[1]
        end_time_str = sys.argv[2]
        delete_files_in_time_range_str(start_time_str, end_time_str)
