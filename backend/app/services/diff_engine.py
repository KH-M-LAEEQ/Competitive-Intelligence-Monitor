import difflib


def compute_diff(old_text: str, new_text: str) -> str:
    diff = difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile="previous",
        tofile="current",
        lineterm=""
    )

    return "\n".join(diff)


def has_material_diff(old_text: str, new_text: str) -> bool:
    return old_text.strip() != new_text.strip()
