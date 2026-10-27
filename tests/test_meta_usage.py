"""Using the tool is not a taste.

A real profile accumulated thirteen dialogue-derived interests built while the
user configured, tested and debugged OpenBiliClaw (「系统配置与测试」0.85,
「Agent配置工具链验证」0.7 …) and dislike topics that are complaints about agent
behaviour. These guards keep operating the product out of the taste profile
without nuking legitimate technical interests.
"""

from __future__ import annotations

import json

import pytest

from openbiliclaw.soul.dialogue_insight_analyzer import DialogueInsightAnalyzer
from openbiliclaw.soul.meta_usage import (
    is_product_operations_message,
    looks_like_product_ops_topic,
    should_drop_dialogue_candidate,
)


@pytest.mark.parametrize(
    "name",
    [
        "系统配置与测试",
        "Agent配置工具链验证",
        "系统测试与验证",
        "参数化调试方法论",
        "软件配置管理",
        "参数配置与调优",
        "自动化边界测试",
    ],
)
def test_compound_operational_topics_are_flagged(name: str) -> None:
    assert looks_like_product_ops_topic(name)


@pytest.mark.parametrize("name", ["软件测试", "系统化工程方法", "编程", "国际时事", "美食"])
def test_single_word_technical_topics_are_left_for_review(name: str) -> None:
    """「软件测试」 is a real interest for many people — never auto-archive it."""
    assert not looks_like_product_ops_topic(name)


def test_product_operations_turn_is_detected() -> None:
    assert is_product_operations_message("帮我看看 OpenBiliClaw 的抓取任务为什么一直超时")
    assert is_product_operations_message("我刚改了配置，顺便调一下日志级别")


def test_ordinary_chat_is_not_product_operations() -> None:
    assert not is_product_operations_message("我最近在学软件测试，感觉挺有意思")
    assert not is_product_operations_message("今天看了个讲宋朝的纪录片，特别好")


def test_operational_candidate_in_tool_turn_is_dropped() -> None:
    assert should_drop_dialogue_candidate(
        "系统配置与测试",
        user_message="我把 config.toml 改了，测试一下新的抓取流程",
    )


def test_real_taste_in_tool_turn_survives() -> None:
    assert not should_drop_dialogue_candidate(
        "播客",
        user_message="改完配置后我拿 OpenBiliClaw 听播客，还是更喜欢访谈类节目",
    )


def test_operational_word_outside_tool_turn_survives() -> None:
    assert not should_drop_dialogue_candidate(
        "软件测试",
        user_message="我最近在学软件测试，想找些入门视频",
    )


class _FixedRegistry:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls = 0

    async def complete_structured_task(self, **_: object) -> object:
        self.calls += 1

        class _Response:
            content = json.dumps(self.payload, ensure_ascii=False)

        return _Response()


@pytest.mark.asyncio
async def test_analyzer_drops_meta_usage_candidates_but_keeps_settles() -> None:
    registry = _FixedRegistry(
        {
            "candidates": [
                {
                    "kind": "interest",
                    "content": "系统配置与测试",
                    "confidence": 0.8,
                    "evidence": "",
                },
                {"kind": "interest", "content": "播客", "confidence": 0.7, "evidence": ""},
            ],
            "settles": [],
        }
    )
    analyzer = DialogueInsightAnalyzer(registry)  # type: ignore[arg-type]

    result = await analyzer.extract(
        user_message="我把 config.toml 里的抓取参数调了一下，测试一下效果",
        assistant_reply="好的，已经重新跑了一轮抓取。",
        core_memory={},
    )

    contents = [candidate["content"] for candidate in result["candidates"]]  # type: ignore[index]
    assert contents == ["播客"]
