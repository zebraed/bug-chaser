from pathlib import Path

from bug_chaser.config.loader import ForumConfigLoader


def test_loads_example_config() -> None:
    loaded = ForumConfigLoader(Path("config/forums")).load_all()

    assert loaded[0].config.forum.key == "example-forum"
