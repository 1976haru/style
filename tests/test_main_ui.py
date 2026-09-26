import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_app_does_not_overwrite_tk_master_parent_pointer():
    """Protect Tk's parent chain from the v0.5 Windows startup hang."""
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    writes = []
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "master"
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                writes.append(target.lineno)
    assert writes == []


def test_master_editor_uses_non_reserved_widget_attribute():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "self.master_text=tk.Text" in source
