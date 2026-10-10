"""
Update only the age text in the published Neofetch SVG.

Does not download avatars, query GitHub, or regenerate the card.
Only the exact XML text between <text id="profile-age">...</text> changes.
"""

from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from age_utils import calculate_age


PROFILE_SVG = Path("profile.svg")
AGE_ID = "profile-age"

AGE_PATTERN = re.compile(
    r'(<text\b(?=[^>]*\bid="profile-age")[^>]*>)(\d+ years)(</text>)'
)


def update_age_only(path: Path = PROFILE_SVG) -> bool:

    # 从 age_utils.py 获取北京时间对应的周岁
    new_value = f"{calculate_age()} years"

    if not path.is_file():
        raise FileNotFoundError(
            f"{path} does not exist. "
            "Run the full Neofetch workflow first."
        )

    original = path.read_bytes()
    source = original.decode("utf-8")

    # 验证 SVG，并且确保年龄元素唯一
    svg_root = ET.fromstring(source)

    targets = [
        element
        for element in svg_root.iter()
        if element.get("id") == AGE_ID
    ]

    if len(targets) != 1:
        raise RuntimeError(
            "Could not find exactly one profile-age SVG element. "
            "Run the updated Neofetch workflow first."
        )

    target = targets[0]

    if target.tag.rsplit("}", 1)[-1] != "text" or len(target):
        raise RuntimeError(
            "profile-age must be a plain SVG text element"
        )

    matches = list(AGE_PATTERN.finditer(source))

    if len(matches) != 1 or matches[0].group(2) != target.text:
        raise RuntimeError(
            "Unexpected SVG age markup; refusing to alter other content"
        )

    match = matches[0]
    previous_value = match.group(2)

    # 年龄没有变化，不修改文件
    if previous_value == new_value:
        print(
            "Age unchanged; no SVG modifications "
            "and no commit needed."
        )
        return False

    # 仅替换年龄文本，不重新生成 SVG
    updated = (
        source[:match.start(2)]
        + new_value
        + source[match.end(2):]
    )

    # 再次验证 SVG 格式
    ET.fromstring(updated)

    path.write_bytes(updated.encode("utf-8"))

    print(f"Age updated: {previous_value} -> {new_value}")

    return True


if __name__ == "__main__":
    update_age_only()
