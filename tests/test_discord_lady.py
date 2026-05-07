import asyncio

from flannel.config.forum import ActionRule, ForumConfig
from flannel.discord.lady import ShadowLadyThreadManager


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
        ShadowLadyThreadManager(archive_delay_seconds=0).apply_action(
            config,
            thread,
            "when_closed",
        )
    )

    assert thread.calls == [
        ("send", {"content": "解決済みです。"}),
        ("edit", {"archived": True}),
    ]


def test_action_skips_existing_bot_comment() -> None:
    config = _comment_config()
    thread = _FakeThread(
        messages=[_FakeMessage(content="対応中です。", author=_FakeAuthor(bot=True))]
    )

    asyncio.run(
        ShadowLadyThreadManager().apply_action(
            config,
            thread,
            "when_in_progress",
        )
    )

    assert thread.calls == []


def test_action_does_not_skip_matching_user_comment() -> None:
    config = _comment_config()
    thread = _FakeThread(
        messages=[
            _FakeMessage(content="対応中です。", author=_FakeAuthor(bot=False)),
        ]
    )

    asyncio.run(
        ShadowLadyThreadManager().apply_action(
            config,
            thread,
            "when_in_progress",
        )
    )

    assert thread.calls == [("send", {"content": "対応中です。"})]


def test_action_only_checks_latest_comment_for_duplicates() -> None:
    config = _comment_config()
    thread = _FakeThread(
        messages=[
            _FakeMessage(content="別のコメントです。", author=_FakeAuthor(bot=True)),
            _FakeMessage(content="対応中です。", author=_FakeAuthor(bot=True)),
        ]
    )

    asyncio.run(
        ShadowLadyThreadManager().apply_action(
            config,
            thread,
            "when_in_progress",
        )
    )

    assert thread.calls == [("send", {"content": "対応中です。"})]


def _comment_config() -> ForumConfig:
    return ForumConfig.model_validate(
        {
            "forum": {
                "key": "example",
                "guild_id": 1,
                "channel_id": 2,
                "automation": {
                    "enabled": True,
                    "auto_comment": True,
                },
            },
            "state_order": [],
            "actions": {
                "when_in_progress": {
                    "add_comment": "対応中です。",
                },
            },
        }
    )


class _FakeThread:
    def __init__(self, messages: list["_FakeMessage"] | None = None) -> None:
        self.id = 123
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.messages = messages or []

    async def send(self, content: str) -> None:
        self.calls.append(("send", {"content": content}))
        self.messages.insert(
            0,
            _FakeMessage(content=content, author=_FakeAuthor(bot=True)),
        )

    async def edit(self, **kwargs: object) -> None:
        self.calls.append(("edit", kwargs))

    def history(self, limit: int):
        async def _messages():
            for message in self.messages[:limit]:
                yield message

        return _messages()


class _FakeAuthor:
    def __init__(self, bot: bool) -> None:
        self.bot = bot


class _FakeMessage:
    def __init__(self, content: str, author: _FakeAuthor) -> None:
        self.content = content
        self.author = author
