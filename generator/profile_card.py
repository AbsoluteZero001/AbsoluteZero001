from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import xml.etree.ElementTree as ET

import requests

from age_utils import calculate_age


# ============================================================
# Configuration / layout
# ============================================================

USERNAME = "AbsoluteZero001"
AVATAR_FILE = Path("cache/avatar.svg")
OUTPUT_FILE = Path("cache/profile.svg")

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

# Smaller canvas, tighter avatar column, larger readable right-hand text.
# GitHub scales README images to its content width: a narrower canvas
# keeps terminal text readable without enlarging the entire page.
WIDTH = 1200
HEIGHT = 745
HEADER_HEIGHT = 42

INFO_X = 615
VALUE_X = 762
RIGHT_EDGE = WIDTH - 35

AVATAR_LEFT = 20
AVATAR_RIGHT = INFO_X - 18
# Preserve the original ASCII portrait in a strictly square 1:1 viewport.
# Move it upward to reserve a small terminal for identity information below.
AVATAR_SIZE = AVATAR_RIGHT - AVATAR_LEFT  # 577 x 577
AVATAR_TOP = HEADER_HEIGHT + 10          # y = 52
AVATAR_BOTTOM = AVATAR_TOP + AVATAR_SIZE # y = 629
TERMINAL_X = AVATAR_LEFT + 18

FONT_FAMILY = "Consolas, 'DejaVu Sans Mono', 'Liberation Mono', monospace"
BODY_SIZE = 18
LABEL_SIZE = 18

BG = "#0D1117"
HEADER_BG = "#090E13"
TEXT = "#D6DEE9"
MUTED = "#76889E"
BORDER = "#37475A"
GREEN = "#50FA7B"
BLUE = "#63C5FF"
YELLOW = "#F1C40F"

# Fixed Beijing timezone, independent of the machine / CI runner timezone.
CLOCK_TZ = timezone(timedelta(hours=8))
CLOCK_TZ_LABEL = "CN · UTC+08:00"



LANGUAGE_COLORS = {
    "Java": "#F89820",
    "Python": "#3776AB",
    "JavaScript": "#F7DF1E",
    "TypeScript": "#3178C6",
    "Vue": "#42B883",
    "HTML": "#E34F26",
    "CSS": "#1572B6",
    "Shell": "#89E051",
    "Dockerfile": "#2496ED",
    "C": "#A8B9CC",
    "C++": "#00599C",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "PHP": "#777BB4",
    "Kotlin": "#7F52FF",
    "Astro": "#BC52EE",
    "Other": "#8B949E",
}


# ============================================================
# GitHub API (keep all original live statistics)
# ============================================================

def github_headers():
    token = os.getenv("GITHUB_TOKEN") or os.getenv("ACCESS_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AbsoluteZero-Neofetch",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(url, params=None):
    response = requests.get(
        url,
        headers=github_headers(),
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def calculate_uptime(created_at):
    """GitHub account age in complete calendar years/months."""
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    years = now.year - created.year
    months = now.month - created.month

    if now.day < created.day:
        months -= 1

    if months < 0:
        years -= 1
        months += 12

    year_unit = "year" if years == 1 else "years"
    month_unit = "month" if months == 1 else "months"

    return f"{years} {year_unit}, {months} {month_unit}"


def get_user_data():
    user = github_get(f"https://api.github.com/users/{USERNAME}")

    return {
        "username": user["login"],
        "repos": user["public_repos"],
        "followers": user["followers"],
        "following": user["following"],
        "uptime": calculate_uptime(user["created_at"]),
    }


def get_repositories():
    """Owned public non-fork repositories, paginated."""
    repositories = []
    page = 1

    while True:
        data = github_get(
            f"https://api.github.com/users/{USERNAME}/repos",
            params={
                "per_page": 100,
                "page": page,
                "type": "owner",
            },
        )

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    return [
        repo
        for repo in repositories
        if not repo.get("fork", False)
    ]


def get_language_statistics(repositories):
    """Language percentages by GitHub-reported source bytes (not WakaTime)."""
    totals = defaultdict(int)

    for repo in repositories:
        url = repo.get("languages_url")

        if not url:
            continue

        for language, byte_count in github_get(url).items():
            totals[language] += byte_count

    total = sum(totals.values())

    if total == 0:
        return []

    return [
        {
            "name": language,
            "percentage": byte_count / total * 100,
            "color": LANGUAGE_COLORS.get(
                language,
                LANGUAGE_COLORS["Other"],
            ),
        }
        for language, byte_count in sorted(
            totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def get_commit_contributions():
    """GitHub contribution-calendar commits in the last 365 days."""
    if not (os.getenv("GITHUB_TOKEN") or os.getenv("ACCESS_TOKEN")):
        return None

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=365)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
        }
      }
    }
    """

    response = requests.post(
        "https://api.github.com/graphql",
        headers=github_headers(),
        json={
            "query": query,
            "variables": {
                "login": USERNAME,
                "from": start.isoformat(),
                "to": now.isoformat(),
            },
        },
        timeout=20,
    )

    response.raise_for_status()

    result = response.json()

    if result.get("errors"):
        raise RuntimeError(
            f"GitHub GraphQL error: {result['errors']}"
        )

    return result["data"]["user"]["contributionsCollection"][
        "totalCommitContributions"
    ]


# ============================================================
# SVG primitives
# ============================================================

def svg_element(name):
    return f"{{{SVG_NS}}}{name}"


def add_text(
    parent,
    x,
    y,
    content,
    color=TEXT,
    size=BODY_SIZE,
    weight="normal",
    anchor=None,
):
    attrs = {
        "x": str(x),
        "y": str(y),
        "fill": color,
        "font-family": FONT_FAMILY,
        "font-size": str(size),
        "font-weight": weight,
    }

    if anchor:
        attrs["text-anchor"] = anchor

    element = ET.SubElement(
        parent,
        svg_element("text"),
        attrs,
    )

    element.text = str(content)

    return element


def add_rect(
    parent,
    x,
    y,
    width,
    height,
    fill,
    radius=0,
    extra=None,
):
    attrs = {
        "x": str(x),
        "y": str(y),
        "width": str(width),
        "height": str(height),
        "fill": fill,
    }

    if radius:
        attrs["rx"] = str(radius)

    if extra:
        attrs.update(extra)

    return ET.SubElement(
        parent,
        svg_element("rect"),
        attrs,
    )


def add_line(parent, x1, y1, x2, y2):
    return ET.SubElement(
        parent,
        svg_element("line"),
        {
            "x1": str(x1),
            "y1": str(y1),
            "x2": str(x2),
            "y2": str(y2),
            "stroke": BORDER,
            "stroke-width": "1",
        },
    )


def add_info(
    parent,
    y,
    label,
    value,
    color=GREEN,
    size=BODY_SIZE,
):
    # Colored labels and thin terminal-style values.
    add_text(
        parent,
        INFO_X,
        y,
        label,
        color=color,
        size=size,
        weight="bold",
    )

    add_text(
        parent,
        VALUE_X,
        y,
        value,
        color=TEXT,
        size=size,
    )


# ============================================================
# Colored ASCII avatar
# Fit visible glyphs to the left column
# ============================================================

def svg_number(value, default=0.0):
    try:
        return float(
            str(value).strip().removesuffix("px")
        )
    except (TypeError, ValueError):
        return default


def get_avatar_bounds(avatar_root):
    """Estimate visual text extents, ignoring unused SVG whitespace."""

    points = []

    for node in avatar_root.iter():
        if node.tag.rsplit("}", 1)[-1] != "text":
            continue

        if not (node.text or "").strip():
            continue

        if node.get("x") is None or node.get("y") is None:
            continue

        x = svg_number(node.get("x"))
        y = svg_number(node.get("y"))
        font_size = svg_number(
            node.get("font-size"),
            13,
        )

        glyph_width = max(
            7.5,
            font_size * 0.62,
        ) * len(node.text or "")

        points.append(
            (
                x,
                y - font_size * 0.88,
                x + glyph_width,
                y + font_size * 0.16,
            )
        )

    if points:
        return (
            min(item[0] for item in points),
            min(item[1] for item in points),
            max(item[2] for item in points),
            max(item[3] for item in points),
        )

    viewbox = (
        avatar_root.get("viewBox", "")
        .replace(",", " ")
        .split()
    )

    if len(viewbox) == 4:
        x, y, w, h = (
            float(item)
            for item in viewbox
        )

        return (
            x,
            y,
            x + w,
            y + h,
        )

    w = svg_number(
        avatar_root.get("width"),
        650,
    )

    h = svg_number(
        avatar_root.get("height"),
        650,
    )

    return (
        0,
        0,
        w,
        h,
    )


def get_avatar_canvas(avatar_root):
    """Prefer source SVG canvas; fall back to occupied text bounds.

    The canvas, not the number of ASCII rows, defines the original picture.
    It must be mapped onto the square viewport with ONE scale factor.
    """
    raw = (avatar_root.get("viewBox") or "").replace(",", " ").split()
    if len(raw) == 4:
        try:
            x, y, w, h = map(float, raw)
            if w > 0 and h > 0:
                return x, y, w, h
        except ValueError:
            pass

    left, top, right, bottom = get_avatar_bounds(avatar_root)
    return left, top, max(right - left, 1), max(bottom - top, 1)


def ensure_defs(parent):
    defs = parent.find(svg_element("defs"))
    if defs is None:
        defs = ET.Element(svg_element("defs"))
        parent.insert(0, defs)
    return defs


def embed_avatar(parent):
    if not AVATAR_FILE.exists():
        raise FileNotFoundError(f"Avatar SVG not found: {AVATAR_FILE}")

    avatar_root = ET.parse(AVATAR_FILE).getroot()
    source_x, source_y, source_w, source_h = get_avatar_canvas(avatar_root)

    # Square canvas + UNIFORM scale.  No separate scaleX / scaleY exists.
    # `contain` preserves the source without stretching or cropping.
    scale = min(AVATAR_SIZE / source_w, AVATAR_SIZE / source_h)
    translate_x = AVATAR_LEFT + (AVATAR_SIZE - source_w * scale) / 2 - source_x * scale
    translate_y = AVATAR_TOP + (AVATAR_SIZE - source_h * scale) / 2 - source_y * scale

    # No decorative characters outside the square: reserve both bands for new content.

    # Clip the real avatar to its exact 1:1 bounds.  Regardless of the source
    # canvas aspect ratio, no portrait pixel can bleed into the filler bands.
    defs = ensure_defs(parent)
    clip = ET.SubElement(defs, svg_element("clipPath"), {"id": "avatar-1to1-clip"})
    add_rect(clip, AVATAR_LEFT, AVATAR_TOP, AVATAR_SIZE, AVATAR_SIZE, "white")

    viewport = ET.SubElement(parent, svg_element("g"), {
        "clip-path": "url(#avatar-1to1-clip)",
    })
    avatar_layer = ET.SubElement(viewport, svg_element("g"), {
        "transform": f"translate({translate_x:.3f},{translate_y:.3f}) scale({scale:.8f})",
        "xml:space": "preserve",
    })

    # Keep source text positions, shape, font and original blue colors.
    for element in avatar_root:
        if element.tag.rsplit("}", 1)[-1] == "rect":
            continue
        avatar_layer.append(deepcopy(element))



# ============================================================
# Linux identity terminal: no personal birthday is stored in the SVG.
# ============================================================

def draw_identity_terminal(parent, age: int) -> None:
    # A quiet separator makes the newly available region read as a terminal.
    add_line(parent, TERMINAL_X, 644, AVATAR_RIGHT - 4, 644)

    def command(y: int, name: str) -> None:
        prompt = add_text(parent, TERMINAL_X, y, "", size=16)
        user_span = ET.SubElement(prompt, svg_element("tspan"), {"fill": GREEN})
        user_span.text = "absolutezero@vertex"
        path_span = ET.SubElement(prompt, svg_element("tspan"), {"fill": BLUE})
        path_span.text = ":~$ "
        command_span = ET.SubElement(prompt, svg_element("tspan"), {"fill": TEXT})
        command_span.text = name

    command(665, "whoami")
    add_text(parent, TERMINAL_X, 686, "absolutezero", color=TEXT, size=16)
    command(710, "age")  # Custom informational command, not standard Linux.
    age_label = add_text(parent, TERMINAL_X, 731, f"{age} years", color=TEXT, size=16)
    age_label.set("id", "profile-age")  # Dedicated midnight update target.


# ============================================================
# Terminal-style language meters and proportional distribution bar
# ============================================================

def draw_terminal_meter(
    parent,
    x,
    y,
    percentage,
    color,
    width=126,
):
    """Square-ended terminal-style pixel meter."""

    height = 16
    cols = 50
    rows = 4

    cell_w = width / cols
    cell_h = height / rows

    active_end = width * percentage / 100

    add_rect(
        parent,
        x,
        y - 13,
        width,
        height,
        "#15202A",
    )

    for col in range(cols):
        for row in range(rows):
            xx = x + col * cell_w
            yy = y - 13 + row * cell_h

            attrs = {
                "opacity": (
                    "0.93"
                    if (col + 0.5) * cell_w <= active_end
                    else "0.25"
                )
            }

            add_rect(
                parent,
                xx + 0.40,
                yy + 0.35,
                cell_w - 0.8,
                cell_h - 1.0,
                color,
                extra=attrs,
            )


def draw_languages(parent, languages):
    """Draw Top 8 public repository language statistics."""

    top_languages = languages[:8]

    if not top_languages:
        add_text(
            parent,
            INFO_X,
            539,
            "No language statistics available",
            MUTED,
            17,
        )

    else:
        first_y = 535
        step = 22

        bar_x = INFO_X + 145
        bar_width = 250

        percent_x = bar_x + bar_width + 17

        for index, entry in enumerate(top_languages):
            y = first_y + index * step

            add_text(
                parent,
                INFO_X,
                y,
                entry["name"],
                entry["color"],
                17,
            )

            draw_terminal_meter(
                parent,
                bar_x,
                y,
                entry["percentage"],
                entry["color"],
                bar_width,
            )

            add_text(
                parent,
                percent_x,
                y,
                f'{entry["percentage"]:.1f}%',
                TEXT,
                17,
            )

    # Proportional stacked bar for ALL languages, not just the Top 8.
    # Each segment width reflects GitHub's language byte counts.
    strip_x = INFO_X
    strip_y = 707
    strip_width = min(450, RIGHT_EDGE - INFO_X)
    strip_height = 20

    add_rect(parent, strip_x, strip_y, strip_width, strip_height, "#15202A")

    if languages:
        # Normalize against the sum to avoid gaps from floating point rounding.
        total_percentage = sum(max(0.0, item["percentage"]) for item in languages)
        if total_percentage > 0:
            cursor = strip_x
            for index, entry in enumerate(languages):
                segment_width = (
                    strip_width * max(0.0, entry["percentage"]) / total_percentage
                )
                if index == len(languages) - 1:
                    segment_width = max(0.0, strip_x + strip_width - cursor)
                if segment_width > 0:
                    add_rect(
                        parent,
                        cursor,
                        strip_y,
                        segment_width,
                        strip_height,
                        entry["color"],
                    )
                cursor += segment_width


# ============================================================
# Build, render and validate the SVG
# ============================================================

def generate_profile():
    # Resolve the age before any network requests: fail early if the secret is missing.
    age = calculate_age()

    print("Fetching GitHub user data...")
    user = get_user_data()

    print("Fetching repositories...")
    repositories = get_repositories()

    print("Fetching language statistics...")
    languages = get_language_statistics(
        repositories
    )

    print("Fetching commit contributions...")

    try:
        commits = get_commit_contributions()

    except Exception as error:
        print(
            "Commit contribution query failed:",
            error,
        )
        commits = None

    # ========================================================
    # SVG root
    # ========================================================

    root = ET.Element(
        svg_element("svg"),
        {
            "width": str(WIDTH),
            "height": str(HEIGHT),
            "viewBox": f"0 0 {WIDTH} {HEIGHT}",
            "role": "img",
            "aria-label": (
                "Neofetch GitHub profile for AbsoluteZero001"
            ),
        },
    )

    ET.SubElement(
        root,
        svg_element("title"),
    ).text = "AbsoluteZero001 · Neofetch GitHub Profile"

    # ========================================================
    # Terminal background
    # ========================================================

    add_rect(
        root,
        0,
        0,
        WIDTH,
        HEIGHT,
        BG,
        radius=12,
    )

    add_rect(
        root,
        0,
        0,
        WIDTH,
        HEADER_HEIGHT,
        HEADER_BG,
        radius=12,
    )

    # Terminal window controls.
    for index, color in enumerate(
        (
            "#FF5F57",
            "#FEBC2E",
            "#28C840",
        )
    ):
        ET.SubElement(
            root,
            svg_element("circle"),
            {
                "cx": str(28 + index * 24),
                "cy": "21",
                "r": "8",
                "fill": color,
            },
        )

    # Terminal title.
    add_text(
        root,
        WIDTH / 2,
        27,
        "absolutezero — neofetch",
        MUTED,
        size=15,
        anchor="middle",
    )

    # ========================================================
    # ASCII avatar
    # ========================================================

    embed_avatar(root)
    draw_identity_terminal(root, age)

    # ========================================================
    # GitHub username
    # ========================================================

    add_text(
        root,
        INFO_X,
        76,
        f'{user["username"]}@github',
        GREEN,
        size=20,
        weight="bold",
    )

    # ========================================================
    # Beijing clock — generated timestamp, accurate to seconds.
    # GitHub README treats SVG as a static image, so the display
    # updates only when the SVG is regenerated, not every second.
    # ========================================================
    clock_now = datetime.now(CLOCK_TZ)
    add_text(
        root,
        RIGHT_EDGE,
        63,
        CLOCK_TZ_LABEL,
        color=MUTED,
        size=14,
        anchor="end",
    )
    add_text(
        root,
        RIGHT_EDGE,
        84,
        clock_now.strftime("%Y-%m-%d  %H:%M:%S"),
        color=BLUE,
        size=17,
        weight="bold",
        anchor="end",
    )

    add_line(
        root,
        INFO_X,
        94,
        RIGHT_EDGE,
        94,
    )

    # ========================================================
    # System information
    # ========================================================

    add_info(
        root,
        119,
        "OS",
        "Windows 11 · Linux",
    )

    add_info(
        root,
        144,
        "Shell",
        "Bash · PowerShell",
    )

    add_info(
        root,
        169,
        "Role",
        "Full-Stack Developer",
    )

    # ========================================================
    # GitHub statistics
    # ========================================================

    add_info(
        root,
        201,
        "GitHub Age",
        user["uptime"],
    )

    add_info(
        root,
        225,
        "Repos",
        str(user["repos"]),
        BLUE,
    )

    add_info(
        root,
        249,
        "Followers",
        str(user["followers"]),
        BLUE,
    )

    add_info(
        root,
        273,
        "Following",
        str(user["following"]),
        BLUE,
    )

    commit_text = (
        f"{commits:,} last 12 months"
        if commits is not None
        else "N/A"
    )

    add_info(
        root,
        297,
        "Commits",
        commit_text,
        BLUE,
    )

    # ========================================================
    # Technical profile
    # ========================================================

    add_info(
        root,
        333,
        "Focus",
        "Full-Stack · Java Backend",
    )

    add_info(
        root,
        357,
        "DevOps",
        "Linux · Docker · K8s · CI/CD",
    )

    add_info(
        root,
        381,
        "NetSec",
        "Kali · Networking · Cybersecurity",
    )

    add_info(
        root,
        405,
        "Stack",
        "Spring Boot · Redis · Kafka",
    )

    add_info(
        root,
        429,
        "AI",
        "LLM · Ollama · AI Agents",
    )

    add_info(
        root,
        465,
        "Site",
        "evezero.cn",
        BLUE,
    )

    # ========================================================
    # Language statistics
    # ========================================================

    add_line(
        root,
        INFO_X,
        483,
        RIGHT_EDGE,
        483,
    )

    add_text(
        root,
        INFO_X,
        508,
        "Languages · Public Repositories",
        MUTED,
        16,
    )

    draw_languages(
        root,
        languages,
    )

    # ========================================================
    # Save SVG
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ET.ElementTree(root).write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    # Validate generated XML.
    ET.parse(OUTPUT_FILE)

    # ========================================================
    # Log
    # ========================================================

    print()
    print("================================")
    print("Neofetch profile generated!")
    print("================================")
    print("Username:", user["username"])
    print("Repositories:", user["repos"])
    print("Followers:", user["followers"])
    print("Following:", user["following"])
    print("GitHub Age:", user["uptime"])
    print("Commits:", commit_text)
    print("Languages:", len(languages))
    print("Output:", OUTPUT_FILE)
    print("Size:", WIDTH, "x", HEIGHT)


if __name__ == "__main__":
    generate_profile()
