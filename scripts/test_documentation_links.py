#!/usr/bin/env python3

"""Verify that repository-relative Markdown links resolve."""

from pathlib import Path
import re
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"\[[^\]]*]\(([^)]+)\)")


class DocumentationLinkTests(unittest.TestCase):
    def test_relative_markdown_links_resolve(self):
        broken = []
        markdown_files = sorted(
            path
            for path in ROOT.rglob("*.md")
            if not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
        )
        for markdown in markdown_files:
            source = markdown.read_text(encoding="utf-8")
            for raw_target in LINK_PATTERN.findall(source):
                target = raw_target.strip().strip("<>")
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path_text = unquote(target.split("#", 1)[0])
                if not path_text:
                    continue
                resolved = (markdown.parent / path_text).resolve()
                try:
                    resolved.relative_to(ROOT)
                except ValueError:
                    broken.append(f"{markdown.relative_to(ROOT)} -> {target} (outside repository)")
                    continue
                if not resolved.exists():
                    broken.append(f"{markdown.relative_to(ROOT)} -> {target}")
        self.assertEqual(broken, [], "Broken documentation links:\n" + "\n".join(broken))


if __name__ == "__main__":
    unittest.main(verbosity=2)
