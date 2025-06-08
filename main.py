import streamlit as st
import os
import time
import json
import 缓存问答系统主体
import doubao_API
import 用户端文档读取
import tempfile

# ========= ✅ ✅ ✅ 自定义流式换行函数 =========
def format_stream_with_linebreaks(stream):
    full_text = ""
    placeholder = st.empty()

    for chunk in stream:
        if "✅" in chunk:
            if "✅" in full_text:
                parts = chunk.split("✅")
                processed = parts[0]
                for part in parts[1:]:
                    processed += "\n\n✅" + part
                chunk = processed
        full_text += chunk
        placeholder.markdown(full_text)  # 不用 unsafe_allow_html=True

    return full_text



# ========== 侧边栏初始化 ==========
st.sidebar.title("控制台")
true_api_token = st.secrets["general"]["api_key"]
outer_api_token = st.secrets["general"]["outer_api_key"]
flag = True
is_external = True  # 默认设置为 False，确保在没有输入密钥时不会报错

# 请求用户输入密钥
if api_key := st.sidebar.text_input("请输入密钥", type="password", help='请输入有效的密钥才能使用'):
    if api_key in true_api_token:  # 内部用户
        st.sidebar.success("密钥验证成功！内部用户")
        flag = False
        is_external = False  # 标记是否为外部用户
    elif api_key in outer_api_token:  # 外部用户
        st.sidebar.success("密钥验证成功！外部用户")
        flag = False
        is_external = True  # 标记为外部用户
    else:
        st.sidebar.error("请输入正确的密钥")
        flag = True



model_name = st.sidebar.selectbox("选择模型", ['豆包'], disabled=flag,help='选择用于回答的大模型，后续可能接入更多模型')
use_ref = st.sidebar.selectbox("是否使用知识库检索", ["是", "否"], disabled=flag,help='使用可以检索哈尔滨工业大学私域数据库，获得更加精准的校内信息回答')
tempreture = st.sidebar.slider("温度", 0.0, 2.0, 1.0, disabled=flag,help='控制回答的随机性，0.0为最确定回答，2.0为最随机回答，默认值是1.0')

# ========== 文件上传缓存防抖 ==========
if uploaded_file := st.sidebar.file_uploader("上传文件", type=["docx", "pdf"], disabled=is_external, help='上传文件以扩充知识库，注意我们只支持处理纯文字和表格部分'):
    if not is_external:  # 仅内部用户能上传文件
        if 'uploaded_files_processed' not in st.session_state:
            st.session_state.uploaded_files_processed = {}

        file_name = uploaded_file.name
        file_key = f"{file_name}_{uploaded_file.size}"

        if file_key not in st.session_state.uploaded_files_processed:
            file_ext = os.path.splitext(file_name)[1].lower()
            current_dir = os.path.dirname(os.path.abspath(__file__))
            save_dir = os.path.join(current_dir, "用户上传文件文件集")
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, file_name)

            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            security_response = doubao_API.security_exam(tmp_path)
            if '1' in security_response:
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())

                if file_ext == ".pdf":
                    用户端文档读取.read_pdf(file_path)
                elif file_ext == ".docx":
                    用户端文档读取.read_docx(file_path)

                st.sidebar.success("文件上传成功！")
            else:
                st.sidebar.error("您的文件没有通过安全审查")

            os.remove(tmp_path)
            st.session_state.uploaded_files_processed[file_key] = True
        else:
            st.sidebar.info("该文件已上传并处理")
    else:
        # 外部用户只能看到上传模块，但无法上传
        st.sidebar.info("外部用户无法上传文件，其他功能保持可用")

# ========== 留言与反馈 ==========
if "last_feedback" not in st.session_state:
    st.session_state.last_feedback = ""

txt = st.sidebar.text_area('反馈留言板', disabled=flag,help='您可以在此进行自由留言，作者会认真阅读您的留言。包括但不限于bug指出，想法建议，批评鼓励')
if txt and txt.strip() and txt != st.session_state.last_feedback:
    st.session_state.last_feedback = txt
    local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    if not is_external:
        tips = {"内部用户"+local_time: txt}
    else:
        tips = {"外部用户" + local_time: txt}

    jsonfilepath = os.path.join(os.path.dirname(__file__), "日志与反馈", "反馈留言.json")
    try:
        with open(jsonfilepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            data.update(tips)
    except:
        data = tips
    with open(jsonfilepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    st.sidebar.success("感谢您的反馈！")
elif txt and txt.strip():
    st.sidebar.info("您的反馈已提交")

sentiment_mapping = ["抱歉给您带来了糟糕体验，您可以反馈您的批评建议，我们会尽快修改。",
                     "抱歉让您感到不满，您可以反馈您的批评建议，我们会尽快修改。",
                     "遗憾让您感觉平庸，您可以反馈您的批评建议，我们会继续优化系统，争取让您的体验更上一层楼。",
                     "欣喜让您体验不错，您可以反馈您的建议，我们争取做到更好！",
                     "非常高兴您满意，您可以反馈您的建议或鼓励，这是我们不断前行的动力！"]
selected = st.sidebar.feedback("stars")
if selected is not None:
    st.sidebar.markdown(sentiment_mapping[selected])

with st.sidebar.popover("关于本系统"):
    st.markdown("Hi!欢迎使用本系统。这里有系统介绍和帮助信息，以及作者碎碎念。")
    st.text(
           '本系统根据哈尔滨工业大学校内私域数据库构建，系统会检索与您问题最相关的文段输送给LLM，最终呈现出相对准确的结果。\n'
             '本系统的初衷为面向我们团队项目的知识探索，同时便利工大师生。我们不能保证信息的绝对准确性和绝对全面性，仅供参考交流使用。\n'
             '***免责声明：我们不承担由本系统信息不准确带来的任何后果***\n'
             '本系统对您的cookies只限于管理对话状态，不会记录您的对话内容，不会访问您的敏感信息，但您仍应该注意避免输入任何个人信息和违法违纪内容。\n'
             '为了长期更新和优化我们的知识库，您可以选择自行上传文件补充我们的知识库。请注意，我们只支持上传docx、pdf格式的文件，且只支持处理纯文字和表格部分。您上传的文件会在自动审核后经过分割、编码、向量化、分类后进入知识库，这需要耗费一些时间。\n'
             '鉴于本系统目前承载体量较小，为避免崩溃，您必须输入密钥才能够使用。\n'
             "作者信息：本系统由海晏、我迪迦在东北、睿、千一合作开发。\n"
             "本系统方案代码开源。您可以在 https://github.com/THUAIer/THUAIer-ChatGPT-Server 获取源代码。并查看完整技术路径。\n"
             "***任何在哈工大2025年7月答辩的大一年度项目，若直接使用本项目的代码或方法，需在github下留言与作者联系，且必须使用标准格式标明出处。本项目保留此项权利。***\n"
             '作者碎碎念：这是作者大一年度项目的课题，作者很认真很用心地做这个项目了，但项目仍处于开发阶段，如果您在使用过程中遇到任何问题、bug或建议，欢迎在留言框中留言。'
                      )

# ========== 聊天主逻辑 ==========
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi👋 我是哈工大智能问答助手，请问有什么可以帮助您的？"}]

st.header('哈尔滨工业大学智能问答助手')
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_query := st.chat_input("请输入内容...", disabled=flag):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)
    if use_ref == "是":
        if not is_external:
            with st.spinner("模型正在思考..."):
                knowledge = 缓存问答系统主体.output(user_query)
                stream = doubao_API.get_doubao_answer(knowledge, user_query, temperature=tempreture)
        if is_external:
            with st.spinner("模型正在思考..."):
                knowledge = 缓存问答系统主体.outer_output(user_query)
                stream = doubao_API.get_doubao_answer(knowledge, user_query, temperature=tempreture)

        with st.chat_message("assistant"):
            response = format_stream_with_linebreaks(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        with st.spinner("模型正在思考..."):
            history = st.session_state.messages[1:]
            stream = doubao_API.doubao_response_stream(history, user_query, temperature=tempreture)

        with st.chat_message("assistant"):
            response = format_stream_with_linebreaks(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})

if st.button("清空聊天记录", disabled=flag):
    st.session_state.messages = [{"role": "assistant", "content": "Hi👋 我是哈工大智能问答助手，请问有什么可以帮助您的？"}]
    st.rerun()
