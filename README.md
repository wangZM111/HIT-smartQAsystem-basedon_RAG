# HIT-smartQAsystem-basedon_RAG

🎓 **HIT 智能问答助手 | HIT-QA**  
一个面向哈工大内部信息检索的智能问答系统，支持知识库问答、信息溯源、文档上传、文本分类、用户反馈与实时爬虫更新。

本项目旨在解决高校信息分散、查询不便的问题，构建一个 **基于大语言模型（LLM）+ 检索增强生成（RAG）** 的智能问答系统，支持中文语境下的知识库问答和文档交互。

## ✅ 核心特点
- 支持 Streamlit 前端交互，实时响应  
- 集成知识库检索 (BM25 + BERT + reranker)  
- 支持用户文档上传 (PDF、DOCX)  
- 后台爬虫自动抓取校园新闻公告，自动去重入库  
- 支持对爬虫解析的文本进行基于 BERT 的分类  
- 支持向量预计算缓存，加速召回  
- 支持知识库和非知识库检索两种模式，非知识库检索额外支持连续对话

## ⚙️ 使用须知
1. GitHub 源代码不包含数据库。也不包含开源模型
2. 爬虫文件不提供校内信息网址和登录账号密码。
3. `API.py` 文件需自行配置 `volcenginesdkarkruntime` 的 API key，参见豆包大模型官方文档：https://www.volcengine.com/docs/82379/0
4. Streamlit 与 Torch 存在兼容问题（`RuntimeError: Tried to instantiate class '__path__._path'`），但不影响项目使用。
5. 运行爬虫文件前，请执行：  
   ```bash
   playwright install
   playwright install-deps  # （Linux）
   ```
6. 启动主程序请执行：  
   ```bash
   streamlit run main.py
   ```
7. 服务器部署时需开放 8501 端口。

## 🧱 技术栈与模块说明
1. 使用 Playwright, BeautifulSoup, requests 实现模拟浏览器行为，可抓取登录后的校内新闻。
2. 文档处理使用滑动窗口法（window=500, step=250）进行段落分割。
3. 使用 jieba 分词用于 BM25 稀疏检索。
4. 使用 `BAAI/bge-small-zh-v1.5` 生成句向量（维度512）。
5. 使用 `BAAI/reranker-base` 进行候选段落重排序。
6. 文本分类模型为 `BAAI/bge-base-zh-v1.5` 微调而来，基于700条标注数据，执行5分类任务。
7. 数据结构以 `.pt` 格式存储：包含 url、标题、滑窗文本、滑窗分词、滑窗向量、全文向量、分类标签等。
8. 用户问题经过意图识别（LLM），决定检索数据库类别。
9. 三层检索结构：
   - ① BM25 稀疏召回（30条）  
   - ② 语义向量召回（10条，使用 cosine similarity）  
   - ③ reranker 精排（5条）
10. 使用大模型进行问答生成：
    - 知识库问答：Prompt + 问题 + 检索结果
    - 自由问答：Prompt + 问题
11. LLM 提示词应用：
    - 安全审查：识别敏感内容
    - 主题生成：命名上传文档
    - 文本分类：分类用户上传的文档类型
    - 意图识别：确定问答指向库
    - 回答生成
12. 前端（Streamlit）功能模块：
    - 身份验证（控制内部/外部权限）
    - temperature 参数调节
    - 文档上传（仅内部用户）
    - 用户反馈收集
    - 问答输出（支持总结信息、原始信息、信息溯源 / 自由问答支持连续对话）

## 👨‍💻 作者信息
- 海晏（版主）  
- 睿  
- 我迪迦在东北  
- 千一  
**共同合作开发**

## 📄 版权许可
本项目采用 MIT 开源许可，详见 [LICENSE](./LICENSE)。

### 项目声明
任何在哈尔滨工业大学 2025 年度项目结题答辩中直接使用本项目代码、思路的队伍，**必须在答辩 PPT 中使用以下格式声明本项目出处**：

> 本项目在某某部分借鉴了本届计算学部大一年度项目“基于大模型和RAG检索增强生成的智能问答系统”的部分内容。  
> 项目地址：https://github.com/wangZM111/HIT-smartQAsystem-basedon_RAG  
> 联系方式：3410751884@qq.com

## 🤝 致谢
We thank the BAAI team for their open-source contributions to the NLP community.  
See [NOTICE.md](./NOTICE.md) for license and citation information of third-party models.
