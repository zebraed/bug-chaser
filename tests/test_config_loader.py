from pathlib import Path

from bug_chaser.config.loader import ForumConfigLoader

_MINIMAL_FORUM_YAML = """\
forum:
  key: "test-forum"
  guild_id: 1
  channel_id: 2
"""


def test_loads_forum_config(tmp_path: Path) -> None:
    forum_dir = tmp_path / "forums"
    forum_dir.mkdir()
    (forum_dir / "production.yaml").write_text(_MINIMAL_FORUM_YAML, encoding="utf-8")

    loaded = ForumConfigLoader(forum_dir).load_all()

    assert len(loaded) == 1
    assert loaded[0].config.forum.key == "test-forum"


def test_example_yaml_is_ignored(tmp_path: Path) -> None:
    forum_dir = tmp_path / "forums"
    forum_dir.mkdir()
    (forum_dir / "example.yaml").write_text(_MINIMAL_FORUM_YAML, encoding="utf-8")
    (forum_dir / "production.yaml").write_text(_MINIMAL_FORUM_YAML, encoding="utf-8")

    loaded = ForumConfigLoader(forum_dir).load_all()

    assert len(loaded) == 1
    assert loaded[0].path.name == "production.yaml"
