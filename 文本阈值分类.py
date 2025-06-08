import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


# 模型和 tokenizer 加载（只加载一次）
model_path = "saved_label_classification_model"
model = AutoModelForSequenceClassification.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)
model.eval()

def classify_text_by_confidence(text, top_k_if_uncertain=3):
    """
    基于分段置信度规则对文本分类：
    - ≥ 0.85：只返回最大概率的类别
    - [0.75, 0.85)：返回前 2 个
    - [0.60, 0.75)：返回前 3 个
    - < 0.60：返回前 top_k_if_uncertain 个

    参数：
        text (str): 待分类文本
        top_k_if_uncertain (int): 最低置信度下返回的类别数量，默认 3

    返回：
        List[int]: 预测的类别索引（1~N 个）
    """
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=256)
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = F.softmax(logits, dim=1).squeeze().cpu().numpy()

    max_prob = probs.max()

    if max_prob >= 0.8:
        return [probs.argmax()]
    elif max_prob >= 0.60:
        return probs.argsort()[-2:][::-1].tolist()
    elif max_prob >= 0.50:
        return probs.argsort()[-3:][::-1].tolist()
    else:
        return probs.argsort()[-top_k_if_uncertain:][::-1].tolist()

