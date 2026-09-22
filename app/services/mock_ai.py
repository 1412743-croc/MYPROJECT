"""Deterministic offline AI provider."""

from collections.abc import Iterator, Sequence

from app.models.risk import RiskLevel


class MockProvider:
    name = "mock"

    def generate(
        self,
        message: str,
        risk_level: RiskLevel,
        history: Sequence[object],
    ) -> str:
        if risk_level == RiskLevel.HIGH:
            return (
                "我很在意你现在的安全。请立即联系当地紧急服务，并尽快告诉一位你信任的人，"
                "也可以联系校园心理中心、辅导员或其他校园支持人员，请他们陪在你身边。"
                "如果可以，请先远离可能伤害自己的物品或地点。这个系统不能替代紧急援助。"
            )
        if risk_level == RiskLevel.MEDIUM:
            return (
                "谢谢你说出这些感受。你提到的压力或情绪困扰值得认真对待。"
                "如果愿意，可以告诉我这种状态持续多久了，以及现在最难承受的部分。"
                "也可以考虑联系一位信任的人或校园心理支持资源。"
            )
        return (
            "谢谢你愿意告诉我这些。"
            "如果你愿意，可以再说说最近最困扰你的事情；我们可以一起把它分成更小的部分。"
            "我提供的是支持性交流，不是医疗诊断。"
        )

    def stream(
        self,
        message: str,
        risk_level: RiskLevel,
        history: Sequence[object],
    ) -> Iterator[str]:
        reply = self.generate(message, risk_level, history)
        chunk_size = 8
        for start in range(0, len(reply), chunk_size):
            yield reply[start : start + chunk_size]
