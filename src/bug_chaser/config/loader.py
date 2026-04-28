from __future__ import annotations

from pathlib import Path

import yaml

from bug_chaser.config.forum import ForumConfig, LoadedForumConfig


class ForumConfigLoader:
    """Loads per-forum YAML files."""

    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir

    def load_all(self) -> list[LoadedForumConfig]:
        if not self._config_dir.exists():
            msg = f"Config directory does not exist: {self._config_dir}"
            raise FileNotFoundError(msg)

        loaded: list[LoadedForumConfig] = []
        for path in sorted(self._config_dir.glob("*.yaml")):
            loaded.append(self.load(path))
        for path in sorted(self._config_dir.glob("*.yml")):
            loaded.append(self.load(path))

        if not loaded:
            msg = f"No forum config files found in: {self._config_dir}"
            raise FileNotFoundError(msg)
        return loaded

    def load(self, path: Path) -> LoadedForumConfig:
        with path.open("r", encoding="utf-8") as file:
            raw = yaml.safe_load(file) or {}
        return LoadedForumConfig(path=path, config=ForumConfig.model_validate(raw))
