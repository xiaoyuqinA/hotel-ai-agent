"""YAML parser for hotel context resource files."""

from pathlib import Path

import yaml


class YamlParser:
    """解析 YAML 格式的酒店资源文件。"""

    def parse(self, path: Path) -> dict:
        """解析 YAML 文件为字典。

        Args:
            path: YAML 文件路径

        Returns:
            解析后的字典
        """
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
