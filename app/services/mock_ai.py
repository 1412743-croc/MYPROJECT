"""Deterministic offline replies used before a real AI provider is introduced."""


class MockAI:
    HIGH_RISK_PHRASES = (
        "自杀",
        "不想活",
        "结束生命",
        "伤害自己",
        "kill myself",
        "suicide",
    )

    @classmethod
    def reply(cls, message: str) -> str:
        normalized = message.casefold()
        if any(phrase in normalized for phrase in cls.HIGH_RISK_PHRASES):
            return (
                "听起来你现在可能处在危险中，你的安全最重要。请立即联系当地紧急服务，"
                "并尽快告诉一位你信任的人或校园工作人员，请他们陪在你身边。"
                "这个系统不能替代紧急援助。"
            )
        return (
            "谢谢你愿意告诉我这些。听起来你正在承受一些压力。"
            "如果你愿意，可以再说说最近最困扰你的事情；我们可以一起把它分成更小的部分。"
            "我提供的是支持性交流，不是医疗诊断。"
        )
