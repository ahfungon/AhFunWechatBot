from zhipuai import ZhipuAI


class ZhiPu():
    def __init__(self, conf: dict) -> None:
        self.api_key = conf.get("api_key")
        self.model = conf.get("model", "glm-4")  # 默认使用 glm-4 模型
        self.prompt = conf.get("prompt", "你是智能聊天机器人，你叫 阿房公")  # 获取prompt配置
        self.client = ZhipuAI(api_key=self.api_key)
        self.converstion_list = {}
        print(f"[初始化] 使用prompt: {self.prompt}")  # 打印初始化信息

    @staticmethod
    def value_check(conf: dict) -> bool:
        if conf and conf.get("api_key"):
            return True
        return False

    def __repr__(self):
        return 'ZhiPu'

    def get_answer(self, msg: str, wxid: str, **args) -> str:
        print(f"\n[调试信息] 接收到新消息:")
        print(f"- wxid类型: {type(wxid)}")
        print(f"- wxid值: {wxid}")
        print(f"- 消息内容: {msg}")
        print(f"- 其他参数: {args}")
        
        # 检查是否为图片消息
        if msg.startswith('<?xml') and '<img' in msg:
            print("检测到图片消息")
            msg = "[用户发送了一张图片]"
        
        # 如果是新对话，先添加系统角色提示
        if wxid not in self.converstion_list:
            self.converstion_list[wxid] = []
            # print(f"[新对话] 设置prompt: {self.prompt}")
            self._update_message(wxid, self.prompt, "system")
        
        self._update_message(wxid, str(msg), "user")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.converstion_list[wxid]
        )
        resp_msg = response.choices[0].message
        answer = resp_msg.content
        print(f"智谱AI响应: {answer}")
        self._update_message(wxid, answer, "assistant")
        return answer

    def _update_message(self, wxid: str, msg: str, role: str) -> None:
        if wxid not in self.converstion_list.keys():
            self.converstion_list[wxid] = []
        content = {"role": role, "content": str(msg)}
        self.converstion_list[wxid].append(content)
        # 打印完整对话历史
        # print(f"\n当前对话历史 - wxid: {wxid}")
        # for idx, message in enumerate(self.converstion_list[wxid], 1):
        #     print(f"{idx}. {message['role']}: {message['content']}")
        # print("-" * 50)


if __name__ == "__main__":
    from configuration import Config
    config = Config().ZHIPU
    if not config:
        exit(0)

    zhipu = ZhiPu(config)
    rsp = zhipu.get_answer("你好")
    print(rsp)
