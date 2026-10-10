"""
Update the published Neofetch SVG at Beijing midnight.

Only modify the age and LAST UPDATED fields when age changes.

Does not download avatars, query GitHub, or regenerate the card.

BIRTH_DATE is read from GitHub Actions Secrets.
The actual birth date is never stored in the generated SVG.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from age_utils import BEIJING_TZ, calculate_age


# ============================================================
# Configuration
# ============================================================

PROFILE_SVG = Path("profile.svg")

AGE_ID = "profile-age"
UPDATED_ID = "profile-last-updated"


# ============================================================
# SVG patterns
# ============================================================

AGE_PATTERN = re.compile(
    r'(<text\b(?=[^>]*\bid="profile-age")[^>]*>)'
    r'(\d+ years)'
    r'(</text>)'
)

UPDATED_PATTERN = re.compile(
    r'(<text\b(?=[^>]*\bid="profile-last-updated")[^>]*>)'
    r'(\d{4}-\d{2}-\d{2}  \d{2}:\d{2}:\d{2})'
    r'(</text>)'
)


# ============================================================
# Beijing timestamp
# ============================================================

def beijing_timestamp() -> str:
    """
    Return the actual Beijing time when SVG is modified.

    This is not the scheduled GitHub Actions cron time.
    """

    return datetime.now(BEIJING_TZ).strftime(
        "%Y-%m-%d  %H:%M:%S"
    )


# ============================================================
# SVG validation
# ============================================================

def _require_plain_text(
    root: ET.Element,
    marker: str,
    pattern: re.Pattern[str],
    source: str,
):
    """
    Ensure the target SVG element exists exactly once.

    Refuse to modify the file when the structure is unexpected.
    """

    elements = [
        node
        for node in root.iter()
        if node.get("id") == marker
    ]

    if len(elements) != 1:
        raise RuntimeError(
            f"Expected exactly one SVG element with id={marker}"
        )

    element = elements[0]

    if (
        element.tag.rsplit("}", 1)[-1] != "text"
        or len(element)
    ):
        raise RuntimeError(
            f"{marker} must be a plain SVG text element"
        )

    matches = list(pattern.finditer(source))

    if (
        len(matches) != 1
        or matches[0].group(2) != element.text
    ):
        raise RuntimeError(
            f"Unexpected SVG markup for {marker}; "
            "refusing partial update"
        )

    return matches[0]


# ============================================================
# Independent age update
# ============================================================

def update_age_only(
    path: Path = PROFILE_SVG
) -> bool:
    """
    Update age and LAST UPDATED only when age changes.

    Returns:
        True  - SVG content changed.
        False - Age unchanged; no file modifications.
    """

    # Calculate current age using Beijing date.
    new_age = f"{calculate_age()} years"

    if not path.is_file():
        raise FileNotFoundError(
            f"{path} does not exist. "
            "Run the full Neofetch workflow first."
        )

    # Read original SVG without changing its formatting.
    source = path.read_bytes().decode("utf-8")

    # Validate SVG structure.
    root = ET.fromstring(source)

    # Locate age element.
    age_match = _require_plain_text(
        root,
        AGE_ID,
        AGE_PATTERN,
        source,
    )

    # Locate LAST UPDATED element.
    timestamp_match = _require_plain_text(
        root,
        UPDATED_ID,
        UPDATED_PATTERN,
        source,
    )

    old_age = age_match.group(2)

    # ========================================================
    # No age change -> no SVG update
    # ========================================================

    if old_age == new_age:

        print(
            "Age unchanged; "
            "LAST UPDATED unchanged; "
            "no commit needed."
        )

        return False

    # ========================================================
    # Age changed -> update both fields
    # ========================================================

    new_time = beijing_timestamp()

    updated = source

    changes = [
        (
            age_match.start(2),
            age_match.end(2),
            new_age,
        ),
        (
            timestamp_match.start(2),
            timestamp_match.end(2),
            new_time,
        ),
    ]

    # Replace from right to left to preserve text positions.
    for start, end, replacement in sorted(
        changes,
        reverse=True,
    ):

        updated = (
            updated[:start]
            + replacement
            + updated[end:]
        )

    # Validate SVG before writing.
    ET.fromstring(updated)

    # Write only after all checks have passed.
    path.write_bytes(
        updated.encode("utf-8")
    )

    print(
        f"Age updated: {old_age} -> {new_age}"
    )

    print(
        f"LAST UPDATED set to: "
        f"{new_time} (Asia/Shanghai)"
    )

    return True


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    update_age_only()
