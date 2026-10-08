from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import xml.etree.ElementTree as ET
import requests
import os
import calendar


# ============================================================
# 基础配置
# ============================================================

USERNAME = "AbsoluteZero001"

AVATAR_FILE = Path("cache/avatar.svg")
OUTPUT_FILE = Path("cache/profile.svg")

SVG_NS = "http://www.w3.org/2000/svg"

ET.register_namespace("", SVG_NS)

WIDTH = 1400
HEIGHT = 970

AVATAR_X = 35
AVATAR_Y = 95
AVATAR_WIDTH = 650

INFO_X = 730
VALUE_X = 900

# ============================================================
# 颜色
# ============================================================

BG = "#0D1117"
HEADER_BG = "#080D12"
TEXT = "#E6EDF3"
MUTED = "#8B949E"
BORDER = "#30363D"

GREEN = "#50FA7B"
BLUE = "#58A6FF"
YELLOW = "#F1C40F"

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
# GitHub API
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

    created = datetime.fromisoformat(
        created_at.replace("Z", "+00:00")
    )

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

    user = github_get(
        f"https://api.github.com/users/{USERNAME}"
    )

    return {
        "username": user["login"],
        "repos": user["public_repos"],
        "followers": user["followers"],
        "following": user["following"],
        "uptime": calculate_uptime(user["created_at"]),
    }


def get_repositories():

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

    language_bytes = defaultdict(int)

    for repo in repositories:

        languages_url = repo.get("languages_url")

        if not languages_url:
            continue

        languages = github_get(languages_url)

        for language, byte_count in languages.items():
            language_bytes[language] += byte_count

    total = sum(language_bytes.values())

    if total == 0:
        return []

    sorted_languages = sorted(
        language_bytes.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    results = []

    for language, byte_count in sorted_languages:

        percentage = byte_count / total * 100

        results.append({
            "name": language,
            "percentage": percentage,
            "color": LANGUAGE_COLORS.get(
                language,
                "#8B949E",
            ),
        })

    return results


def get_commit_contributions():

    token = os.getenv("GITHUB_TOKEN") or os.getenv("ACCESS_TOKEN")

    if not token:
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

    return result["data"]["user"][
        "contributionsCollection"
    ]["totalCommitContributions"]


# ============================================================
# SVG 工具
# ============================================================

def add_text(
    parent,
    x,
    y,
    content,
    color=TEXT,
    size=19,
    weight="normal",
    anchor=None,
):

    attributes = {
        "x": str(x),
        "y": str(y),
        "fill": color,
        "font-family": "DejaVu Sans Mono, monospace",
        "font-size": str(size),
        "font-weight": weight,
    }

    if anchor:
        attributes["text-anchor"] = anchor

    element = ET.SubElement(
        parent,
        f"{{{SVG_NS}}}text",
        attributes,
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
):

    return ET.SubElement(
        parent,
        f"{{{SVG_NS}}}rect",
        {
            "x": str(x),
            "y": str(y),
            "width": str(width),
            "height": str(height),
            "fill": fill,
            "rx": str(radius),
        },
    )


def add_line(parent, x1, y1, x2, y2):

    return ET.SubElement(
        parent,
        f"{{{SVG_NS}}}line",
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
    color=BLUE,
    size=18,
):

    add_text(
        parent,
        INFO_X,
        y,
        label,
        color,
        size,
        "bold",
    )

    add_text(
        parent,
        VALUE_X,
        y,
        value,
        TEXT,
        size,
    )


# ============================================================
# 嵌入头像
# ============================================================

def embed_avatar(parent):

    if not AVATAR_FILE.exists():
        raise FileNotFoundError(
            f"Avatar SVG not found: {AVATAR_FILE}"
        )

    tree = ET.parse(AVATAR_FILE)

    avatar_root = tree.getroot()

    original_width = float(
        avatar_root.get("width")
    )

    original_height = float(
        avatar_root.get("height")
    )

    # 同时限制头像宽度和高度，防止超出卡片
    max_height = 900 - AVATAR_Y - 40

    scale = min(
        AVATAR_WIDTH / original_width,
        max_height / original_height,
    )

    group = ET.SubElement(
        parent,
        f"{{{SVG_NS}}}g",
        {
            "transform": (
                f"translate({AVATAR_X},{AVATAR_Y}) "
                f"scale({scale})"
            )
        },
    )

    for element in avatar_root:

        tag_name = element.tag.split("}")[-1]

        if tag_name == "rect":
            continue

        group.append(element)


# ============================================================
# 语言进度条
# ============================================================

def draw_languages(parent, languages):

    if not languages:

        add_text(
            parent,
            INFO_X,
            680,
            "No language statistics available",
            MUTED,
            17,
        )

        return

    # 展示前 8 种语言
    top_languages = languages[:8]

    start_y = 680
    row_height = 29

    bar_x = INFO_X + 170
    bar_width = 190
    bar_height = 14

    percentage_x = bar_x + bar_width + 18

    for index, language in enumerate(top_languages):

        y = start_y + index * row_height

        name = language["name"]
        percentage = language["percentage"]
        color = language["color"]

        # 语言名称
        add_text(
            parent,
            INFO_X,
            y,
            name,
            color,
            17,
        )

        # 进度条背景
        add_rect(
            parent,
            bar_x,
            y - 13,
            bar_width,
            bar_height,
            "#21262D",
            2,
        )

        # 彩色进度条
        fill_width = (
            bar_width * percentage / 100
        )

        if fill_width > 0:

            add_rect(
                parent,
                bar_x,
                y - 13,
                fill_width,
                bar_height,
                color,
                2,
            )

        # 百分比
        add_text(
            parent,
            percentage_x,
            y,
            f"{percentage:.1f}%",
            TEXT,
            16,
        )

    # 底部彩色语言汇总条
    rainbow_y = 930
    rainbow_x = INFO_X
    rainbow_width = 420

    current_x = rainbow_x

    for language in languages:

        segment_width = (
            rainbow_width
            * language["percentage"]
            / 100
        )

        add_rect(
            parent,
            current_x,
            rainbow_y,
            segment_width,
            15,
            language["color"],
        )

        current_x += segment_width


# ============================================================
# 主生成程序
# ============================================================

def generate_profile():

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

    # 创建 SVG
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": str(WIDTH),
            "height": str(HEIGHT),
            "viewBox": f"0 0 {WIDTH} {HEIGHT}",
        },
    )

    # 背景
    add_rect(
        root,
        0,
        0,
        WIDTH,
        HEIGHT,
        BG,
        20,
    )

    # 终端标题栏
    add_rect(
        root,
        0,
        0,
        WIDTH,
        55,
        HEADER_BG,
        20,
    )

    # 终端按钮
    for index, color in enumerate(
        ["#FF5F57", "#FEBC2E", "#28C840"]
    ):

        ET.SubElement(
            root,
            f"{{{SVG_NS}}}circle",
            {
                "cx": str(30 + index * 25),
                "cy": "28",
                "r": "8",
                "fill": color,
            },
        )

    # 终端标题
    add_text(
        root,
        WIDTH // 2,
        35,
        "absolutezero — neofetch",
        MUTED,
        17,
        anchor="middle",
    )

    # 左侧 ASCII 头像
    embed_avatar(root)

    # 右侧标题
    add_text(
        root,
        INFO_X,
        105,
        f'{user["username"]}@github',
        GREEN,
        22,
        "bold",
    )

    add_line(
        root,
        INFO_X,
        125,
        WIDTH - 50,
        125,
    )

    # ========================================================
    # 系统信息
    # ========================================================

    add_info(
        root,
        165,
        "OS",
        "Windows 11 · Linux",
        GREEN,
    )

    add_info(
        root,
        195,
        "Shell",
        "Bash · PowerShell",
        GREEN,
    )

    add_info(
        root,
        225,
        "Role",
        "Full-Stack Developer",
        GREEN,
    )

    # ========================================================
    # GitHub 统计
    # ========================================================

    add_info(
        root,
        270,
        "GitHub Age",
        user["uptime"],
        GREEN,
    )

    add_info(
        root,
        300,
        "Repos",
        str(user["repos"]),
        BLUE,
    )

    add_info(
        root,
        330,
        "Followers",
        str(user["followers"]),
        BLUE,
    )

    add_info(
        root,
        360,
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
        390,
        "Commits",
        commit_text,
        BLUE,
    )

    # ========================================================
    # 技术方向（最终定稿）
    # ========================================================

    add_info(root, 435, "Focus", "Full-Stack · Java Backend", GREEN)
    add_info(root, 465, "DevOps", "Linux · Docker · K8s · CI/CD", GREEN)
    add_info(root, 495, "NetSec", "Kali · Networking · Cybersecurity", GREEN, size=16)
    add_info(root, 525, "Stack", "Spring Boot · Redis · Kafka", GREEN)
    add_info(root, 555, "AI", "LLM · Ollama · AI Agents", GREEN)
    add_info(root, 590, "Site", "evezero.cn", GREEN)

    # ========================================================
    # 编程语言统计（公开非 Fork 仓库的代码字节占比）
    # ========================================================

    add_line(root, INFO_X, 615, WIDTH - 50, 615)
    add_text(root, INFO_X, 645, "Languages · Public Repositories", MUTED, 16)
    draw_languages(root, languages)

    # ========================================================
    # 保存 SVG
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tree = ET.ElementTree(root)

    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    # XML 验证
    ET.parse(OUTPUT_FILE)

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
