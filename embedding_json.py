import json
import os
import warnings
import jieba
import torch
from transformers import BertTokenizer, BertModel
import doubao_API as API
import re
import time
import 文本阈值分类
warnings.filterwarnings("ignore")


# 加载BERT模型
current_dir = os.path.dirname(os.path.abspath(__file__))
tokenizer = BertTokenizer.from_pretrained(os.path.join(current_dir, "local_bge_small_zh_model"))
model = BertModel.from_pretrained(os.path.join(current_dir, "local_bge_small_zh_model"))
model.eval()


def bert_embedding(text):
    inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state[:, 0, :]
    return embeddings.cpu().numpy()


def append_log(file_path,url):
    """日志文件记录"""
    log_file_path = os.path.join(current_dir, "日志与反馈", "log.json")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    current_time = time.localtime()
    formatted_date = time.strftime("%Y/%m/%d %H:%M:%S", current_time)
    timestamp = time.time()  # 精确时间戳

    log_entry = {
        "file_name": os.path.basename(file_path),
        "file_path": file_path,
        "url": url,
        "date": formatted_date,
        "timestamp": timestamp
    }

    if os.path.exists(log_file_path):
        with open(log_file_path, 'r', encoding='utf-8') as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                log_data = []
    else:
        log_data = []

    log_data.append(log_entry)

    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)



def process_file_and_save_information(json_path, window_size=500, step_size=250, flag=True):
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    for x in json_data:
        url = x['url']
        text = x['content'].replace("\t", "").replace("\n", "")
        title = re.sub(r'[\\/:\*\?"<>\|]', '_', x['title'])

        # 滑动窗口分割
        page_segments = []
        for i in range(0, len(text) - window_size + 1, step_size):
            page_segments.append(text[i:i + window_size])
        if len(text) % window_size != 0:
            remaining_text = text[-(len(text) % window_size):]
            if page_segments:
                page_segments[-1] += remaining_text
            else:
                page_segments.append(remaining_text)

        # jieba分词
        jieba_sentences_content = [jieba.lcut(segment, cut_all=False) for segment in page_segments]
        window_strings = page_segments.copy()

        # 获取嵌入
        embeddings = bert_embedding(window_strings)
        text_embeddings = bert_embedding(text)

        # 分类
        if flag:
            category = 文本阈值分类.classify_text_by_confidence(text)  # 若用BERT分类则可填入自定义策略
        else:
            category = API.text_classification(title,text)  # 例：[0, 2]

        dataload_list = ['0科创竞赛', '1学生活动', '2学校政策', '3日常通知', '4闲杂信息']

        for c in category:
            sentence_dict = {}
            for idx, segment in enumerate(page_segments):
                segment_key = f"{url}-{idx + 1}__{c}"  # 👈 加入类别后缀
                sentence_dict[segment_key] = segment

            embedding_file_path = os.path.join(current_dir, "数据库", f"{dataload_list[c]}\\{title}.pt")
            #若linux:
            # embedding_file_path = os.path.join(current_dir, "数据库", f"{dataload_list[c]}/{title}.pt")
            torch.save({
                'file_path': url,
                'title': title,
                'sentense_dict': sentence_dict,
                'embeddings': embeddings,
                'text_embeddings': text_embeddings,
                'category': c,
                'jieba_sentences_content': jieba_sentences_content,
                'text': text,
            }, embedding_file_path)

            append_log(embedding_file_path,url)


