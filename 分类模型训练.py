import pandas as pd
import torch
from datasets import Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)

#使用了cuda加速

# ===== 1. 读取 Excel 数据 =====
df = pd.read_excel("类别.xlsx")  # 或使用 "/mnt/data/多标签拆分后.xlsx"

# 保证内容为字符串，类别为整数
df['content'] = df['content'].astype(str)
df['category'] = df['category'].astype(int)

# 获取分类数
num_labels = df['category'].nunique()

# ===== 2. 划分训练/验证集 =====
train_df, val_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['category'])
train_dataset = Dataset.from_pandas(train_df)
val_dataset = Dataset.from_pandas(val_df)

# ===== 3. 加载 tokenizer 和模型 =====
model_name = "BAAI/bge-small-zh-v1.5"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)

# ===== 4. 编码函数 =====
def preprocess(examples):
    return tokenizer(
        examples["content"],
        padding="max_length",
        truncation=True,
        max_length=256
    )

train_dataset = train_dataset.map(preprocess, batched=True)
val_dataset = val_dataset.map(preprocess, batched=True)

# ===== 5. 设置 labels 列名 =====
train_dataset = train_dataset.rename_column("category", "labels")
val_dataset = val_dataset.rename_column("category", "labels")

# ===== 6. 删除不必要的列 =====
train_dataset = train_dataset.remove_columns(["content", "__index_level_0__"])
val_dataset = val_dataset.remove_columns(["content", "__index_level_0__"])

# ===== 7. 设置训练参数 =====
training_args = TrainingArguments(
    output_dir="./results",
    eval_strategy="epoch",
    save_strategy="epoch",
    logging_dir="./logs",
    logging_steps=10,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    num_train_epochs=5,
    learning_rate=2e-5,
    load_best_model_at_end=True,
    fp16=torch.cuda.is_available(),
    report_to="none"
)

# ===== 8. 评估函数 =====
def compute_metrics(p):
    preds = p.predictions.argmax(-1)
    return {
        "accuracy": accuracy_score(p.label_ids, preds),
        "f1_macro": f1_score(p.label_ids, preds, average="macro")
    }

# ===== 9. 初始化 Trainer 并训练 =====
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics
)

trainer.train()

# ===== 10. 保存模型 =====
save_path = "./saved_single_label_model"
model.save_pretrained(save_path)
tokenizer.save_pretrained(save_path)
