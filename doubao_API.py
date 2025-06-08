import os
from volcenginesdkarkruntime import Ark

#本地环境变量下的SDK-APIkey
client = Ark(api_key=os.environ.get("ARK_API_KEY"))

def get_doubao_answer(knowledge: str, question: str,temperature=1):
    """豆包模型有知识库提示回答"""
    stream = client.chat.completions.create(
        model="doubao-1.5-pro-32k-250115",
        messages=[
                {
                    "role": "system",
                    "content": (
                        "你现在是一个乐于助人的助手，请为用户回答问题。\n"
                        "请注意：\n"
                        "1. 请用中文回答用户的问题。\n"
                        "2. 你将会接受到一个字典，包含信息源和原始信息，其中的原始信息是通过文本切块的方式获得的，可能存在语句不完整的情况,可能存在语句重复的情况，可能存在句子位置错乱的情况，可能存在信息相关性不高的情况。你需要对信息进行辨析和整合，然后再进行回答。"
                        "   并且，这个字典中信息的重要性和相关性按一定顺序排列，也要适当注意，但这一点并不是绝对的。"
                        "   你要严格按照如下顺序分析问题：首先对提供的原始信息进行去重、整合。随后根据问题概括答案。接着对信息进行概括性总结（不失原本信息样貌，但不得照搬照抄）。最后给出信息源。"
                        "3. 如果用户给定知识提示，且问题能够从知识库中得到答案，请输出：\n"
                        "   ✅根据已有知识库，{answer}\n"
                        "   ✅对应原始信息为：{information}\n"
                        "   ✅信息源为：{source}\n"
                        "   其中，{answer}为问题的答案，{information}为知识库中与问题相关的信息，{source}为每一个知识库信息对应的源。\n"
                        "   需要注意的是，{answer}部分要简要凝练，概括内容,注意要简练一些，但是仍应该包含主要信息，100字左右。{information}部分要详细具体，包含关键信息，并按照逻辑进行解释，200字左右。{source}部分要给出每一个知识库信息的来源。注意！如果信息源是重复的要整合成一个。对于不重复的需要一行一个信息源。"
                        "   注意很重要！请检查你即将回复的信息源，如果某条不是网址(http)，就将这条替换成：源于用户上传文档"
                        "4. 如果用户给定知识提示，但是问题不能够从知识库中得到答案，请输出：“不能根据知识库输出答案。”并且给出不能回答的理由。\n"
                        "5. 一切有关违背公序良俗道德法律的内容均不能回答。"

                    )
                },
                {"role": "user", "content": f"知识库：{knowledge}"},
                {"role": "user", "content": f"问题：{question}"}
            ],
            # 如需要支持流式输出，可以将 stream 参数设置为 True
            stream=True,
            temperature=temperature

        )

        # 返回助手的回答内容
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content





def doubao_response_stream(history: list, question: str,temperature=1):
    """豆包模型通用回答（心理/普通）支持多轮对话，流式生成器形式"""
    messages = [
        {"role": "system",
         "content": (
             "你现在是一个智能辅导员。\n"
             "你要注意，问题分为两种类型：\n"
             "1. 普通问题：用户正常询问，请直接正常回答。\n"
             "2. 哈工大学生的心理健康问题：你是心理陪伴员，要安慰学生，倾听、理解、共情，语气温柔，建议合理。\n"
             "注意用户可能连续提问，请记住上下文。"
         )}
    ]

    messages.extend(history)
    messages.append({"role": "user", "content": question})

    stream = client.chat.completions.create(
        model="doubao-1.5-pro-32k-250115",
        messages=messages,
        stream=True,
        temperature=temperature
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content





def security_exam(text: str):
    """安全检查，返回bool:0,1，判别用户文档是否进入知识库"""
    completion = client.chat.completions.create(
        model="doubao-1.5-pro-32k-250115",
        messages=[
            {"role": "system",
             "content":
                 "你现在是一个智能安全审查助手，请注意，你会接受到一个文本，你首先要评价它是否安全合规。"
                 "安全合规的标准是：不涉及暴力、恐怖、色情、政治暗示（不包括某些政务通知，仅检测敏感政治信息）"
                 "如果文本没有通过安全审查，请返回：您的文档没有通过安全审查！同时返回不通过安全审查的理由。不必进行接下来的步骤"
                 "你的回复有且仅有数字0或者1"
                 "0代表没有通过"
                 "1代表通过"},
            {"role": "user", "content": f"文段：{text}"}
        ],

    )
    return completion.choices[0].message.content

def topic_generation(text: str):
    """主题生成：用户文档解析前用于命名文件，便于后续回溯"""
    completion = client.chat.completions.create(
        model="doubao-1.5-pro-32k-250115",
        messages=[
            {"role": "system",
             "content": (
                 "你现在是一个主题生成助手，请注意，你会接受到一个文本，请十分简要地提取主题。"
                 "你的回复有且仅有主题，不能包含任何其它文字")},
             {"role": "user", "content": f"文段：{text}"}
        ],

    )
    return completion.choices[0].message.content

def target_recognition(text: str):
    """意图识别，判断用户问题的指向"""
    completion = client.chat.completions.create(
        model="doubao-1.5-pro-32k-250115",
        messages=[
            {"role": "system",
             "content": (
                 "你现在是一个用户问题引导助手。你的任务是：识别用户问题，并将其匹配到对应的数据库。"
                 "现有数据库为以下五种，最前面是它的对应编号，注意从0到4共五个数字，其后附有解释"
                 "0.科创竞赛——包括科创活动、演讲讲座、各种竞赛比赛"
                 "1.学生活动——包括心理减压、社团活动、娱乐活动、课余活动、实践探索活动"
                 "2.学校政策——包括课程安排、学生手册、守则、保研、考研、毕业等关乎学生未来规划的重要信息"
                 "3.日常通知——包括各种日常相对不那么重要的通知、各种开会（不包括讲座之类）"
                 "4.闲杂信息——包括一切不能被分类到前四种类别的信息"
                 "你要注意：你的回复可以包括多种类别,并且你必须回答至少一个类别，哪怕问题匹配是并不好的。你至多回复两个类别")},
            {"role": "user", "content": f"文段：{text}"}
        ],

    )
    message =  completion.choices[0].message.content

    target_list = []
    for i in range(5):
        if f'{i}' in message:
            target_list.append(int(i))
    return target_list

def text_classification(title:str,text: str):
    completion = client.chat.completions.create(
        model="doubao-1.5-pro-32k-250115",
        messages=[
            {"role": "system",
             "content": (
                 "你现在是一个文本分类助手。你的任务是：读取标题和文本，并将其分类到对应的数据库。"
                 "现有数据库为以下五种，最前面是它的对应编号，注意从0到4共五个数字，其后附有解释"
                 "0.科创竞赛——包括科创活动、演讲讲座、各种竞赛比赛"
                 "1.学生活动——包括心理减压、社团活动、娱乐活动、课余活动、实践探索活动"
                 "2.学校政策——包括课程安排、学生手册、守则、保研、考研、毕业等关乎学生未来规划的重要信息"
                 "3.日常通知——包括各种日常相对不那么重要的通知、各种开会（不包括讲座之类）"
                 "4.闲杂信息——包括一切不能被分类到前四种类别的信息"
                 "你要注意：你的回复可以包括多种类别,并且你必须回答至少一个类别，哪怕问题匹配是并不好的。并且你至多回复两个类别。注意尽量只输出一个类别，只有对于极其不确定的文本才输出多个类别。")},
            {"role": "user", "content": f"标题：{title},文段：{text}"}
        ],

    )
    message = completion.choices[0].message.content
    target_list = []
    for i in range(5):
        if f'{i}' in message:
            target_list.append(int(i))
    return target_list



