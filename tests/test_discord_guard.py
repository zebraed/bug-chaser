import asyncio

from bug_chaser.config.forum import ActionRule, ForumConfig
from bug_chaser.discord.guard import RobotGuardThreadManager


def test_action_rule_loads_remove_tags() -> None:
    action = ActionRule.model_validate(
        {
            "add_comment": "解決済みです。",
            "remove_tags": ["重複", "対応中"],
            "add_tags": ["解決済み"],
            "archive": True,
        }
    )

    assert action.remove_tags == ["重複", "対応中"]
    assert action.add_tags == ["解決済み"]
    assert action.archive is True


def test_action_rule_does_not_infer_remove_tags() -> None:
    action = ActionRule.model_validate({"add_comment": "対応中です。"})

    assert action.remove_tags == []


def test_action_sends_comment_before_archiving() -> None:
    config = ForumConfig.model_validate(
        {
            "forum": {
                "key": "example",
                "guild_id": 1,
                "channel_id": 2,
                "automation": {
                    "enabled": True,
                    "auto_comment": True,
                    "auto_archive": True,
                },
            },
            "state_order": [],
            "actions": {
                "when_closed": {
                    "add_comment": "解決済みです。",
                    "archive": True,
                },
            },
        }
    )
    thread = _FakeThread()

    asyncio.run(
        RobotGuardThreadManager(archive_delay_seconds=0).apply_action(
            config,
            thread,
            "when_closed",
        )
    )

    assert thread.calls == [
        ("send", {"content": "解決済みです。"}),
        ("edit", {"archived": True}),
    ]


class _FakeThread:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def send(self, content: str) -> None:
        self.calls.append(("send", {"content": content}))

    async def edit(self, **kwargs: object) -> None:
        self.calls.append(("edit", kwargs))
