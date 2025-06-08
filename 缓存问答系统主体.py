import torch
import numpy as np
from transformers import BertTokenizer, BertModel, AutoTokenizer, AutoModelForSequenceClassification
import jieba
from rank_bm25 import BM25Okapi
from collections import defaultdict
import warnings
import os
import streamlit as st
import doubao_API as API


warnings.filterwarnings("ignore")

# ========================== ✅ 模型与分词器缓存加载 ===========================
@st.cache_resource
def load_models():

    current_dir = os.path.dirname(os.path.abspath(__file__))
    tokenizer = BertTokenizer.from_pretrained(os.path.join(current_dir, "local_bge_small_zh_model"))
    model = BertModel.from_pretrained(os.path.join(current_dir, "local_bge_small_zh_model"))
    model.eval()

    tokenizer_reranker = AutoTokenizer.from_pretrained(os.path.join(current_dir, "reranker-base"))
    model_reranker = AutoModelForSequenceClassification.from_pretrained(os.path.join(current_dir, "reranker-base"))
    model_reranker.eval()

    return tokenizer, model, tokenizer_reranker, model_reranker

# 获取模型实例
bert_tokenizer, bert_model, rerank_tokenizer, rerank_model = load_models()

# ========================== 📌 编码函数 ===========================
def bert_embedding(text: str):
    inputs = bert_tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=128)
    with torch.no_grad():
        outputs = bert_model(**inputs)
    embeddings = outputs.last_hidden_state[:, 0, :]
    return embeddings.cpu().numpy()

# ========================== 📌 数据加载部分 ===========================
def load_folder_path(question: str):
    folder_names = API.target_recognition(question)
    folder_paths = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    folder_map = {
        0: "0科创竞赛",
        1: "1学生活动",
        2: "2学校政策",
        3: "3日常通知",
        4: "4闲杂信息"
    }
    for k in folder_names:
        folder_paths.append(os.path.join(current_dir, "数据库", folder_map[k]))
    return folder_paths

def load_all_pt_information(folder_paths: list):
    pt_files_paths = []
    for folder_path in folder_paths:
        pt_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.pt')]
        pt_files_paths.extend(pt_files)
    return pt_files_paths

def load_information_all(file_paths: list):
    sentence_dict = {}
    jieba_sentences_content = []
    embeddings = np.array([[0] * 512])

    for file_path in file_paths:
        data = torch.load(file_path, weights_only=False)
        sentence_dict.update(data['sentense_dict'])
        jieba_sentences_content.extend(data['jieba_sentences_content'])
        embeddings = np.concatenate((embeddings, data['embeddings']), axis=0)

    embeddings = np.delete(embeddings, 0, axis=0)
    return sentence_dict, jieba_sentences_content, embeddings

# ========================== 🔍 BM25 检索部分 ===========================
@st.cache_data(show_spinner=False)
def build_bm25(jieba_sentences_content):
    return BM25Okapi(jieba_sentences_content)

def bm25_search_index(query, jieba_sentences_content, top_k1=30):
    bm25 = build_bm25(jieba_sentences_content)
    query_terms = jieba.lcut(query, cut_all=False)
    scores = bm25.get_scores(query_terms)
    top_k_indices = np.argsort(scores)[-top_k1:][::-1]
    return top_k_indices

def cosine_similarity_np(array1, array2):
    dot_product = np.dot(array1, array2.T)
    norm_array1 = np.linalg.norm(array1, axis=1, keepdims=True)
    norm_array2 = np.linalg.norm(array2, axis=1, keepdims=True)
    similarity = dot_product / (norm_array1 * norm_array2.T)
    return similarity[0]

def find_BM25_bert_similar_page_index(question, sentence_dict, jieba_sentences_content, embeddings, top_k2=10):
    top_k_indices = bm25_search_index(question, jieba_sentences_content)
    question_embedding = bert_embedding([question])
    top_k_embeddings = embeddings[top_k_indices]
    cos_similarities = cosine_similarity_np(question_embedding, top_k_embeddings)

    if len(top_k_indices) < top_k2:
        top_k2 = len(top_k_indices)
    indices = np.argsort(cos_similarities)[-top_k2:][::-1].tolist()
    return [int(top_k_indices[i]) for i in indices]

# ========================== 🔁 Reranker 阶段 ===========================
def find_the_final_information(sentence_dict, indices):
    keys_list = list(sentence_dict.keys())
    return {keys_list[i]: sentence_dict[keys_list[i]] for i in indices}

def rerank_documents(query, final_information_dict, model, tokenizer, top_p=5, device="cpu", batch_size=8):
    documents = list(final_information_dict.values())
    doc_keys = list(final_information_dict.keys())
    scores = []
    model.to(device)

    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_keys = doc_keys[i:i+batch_size]
        inputs = tokenizer(
            [query] * len(batch_docs), batch_docs,
            return_tensors="pt", padding=True, truncation=True, max_length=256
        ).to(device)

        with torch.no_grad():
            logits = model(**inputs, return_dict=True).logits.view(-1).cpu()
            scores.extend(list(zip(batch_keys, batch_docs, logits)))

    sorted_docs = sorted(scores, key=lambda x: x[2], reverse=True)
    top_p_docs = sorted_docs[:top_p]
    return {key: doc for key, doc, _ in top_p_docs}



def merge_dict_by_prefix(reranked_dict):
    result = defaultdict(list)
    for key, value in reranked_dict.items():
        prefix = key.split('-')[0]
        result[prefix].append(value)
    return dict(result)

# ========================== 🎯 主调用接口 ===========================
def output(question):
    pt_folder_paths = load_folder_path(question)
    pt_file_paths = load_all_pt_information(pt_folder_paths)
    sentence_dict, jieba_sentences_content, embeddings = load_information_all(pt_file_paths)
    bert_index = find_BM25_bert_similar_page_index(question, sentence_dict, jieba_sentences_content, embeddings)
    final_information = find_the_final_information(sentence_dict, bert_index)
    reranker_information = rerank_documents(question, final_information, rerank_model, rerank_tokenizer)
    merge_information = merge_dict_by_prefix(reranker_information)
    return merge_information

def outer_output(question):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pt_folder_paths = [os.path.join(current_dir, "数据库","外用户示例")]
    pt_file_paths = load_all_pt_information(pt_folder_paths)
    sentence_dict, jieba_sentences_content, embeddings = load_information_all(pt_file_paths)
    bert_index = find_BM25_bert_similar_page_index(question, sentence_dict, jieba_sentences_content, embeddings)
    final_information = find_the_final_information(sentence_dict, bert_index)
    reranker_information = rerank_documents(question, final_information, rerank_model, rerank_tokenizer)
    merge_information = merge_dict_by_prefix(reranker_information)
    return merge_information

