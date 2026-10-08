from pathlib import Path
import xml.etree.ElementTree as ET
from html import escape


AVATAR_FILE = Path("cache/avatar.svg")
OUTPUT_FILE = Path("cache/profile.svg")

SVG_NS = "http://www.w3.org/2000/svg"

ET.register_namespace("", SVG_NS)

# 卡片尺寸
WIDTH = 1400
HEIGHT = 800

# 头像区域
AVATAR_X = 35
AVATAR_Y = 85
AVATAR_WIDTH = 650

# 右侧信息区域
INFO_X = 730

# 配色
BG = "#0D1117"
HEADER_BG = "#080D12"
TEXT = "#E6EDF3"
MUTED = "#8B949E"
GREEN = "#50FA7B"
BLUE = "#58A6FF"
YELLOW = "#F1C40F"


def add_text(parent, x, y, content, color=TEXT, size=19):
    element = ET.SubElement(
        parent,
        f"{{{SVG_NS}}}text",
        {
            "x": str(x),
            "y": str(y),
            "fill": color,
            "font-family": "monospace",
            "font-size": str(size),
        }
    )

    element.text = str(content)
    return element


def add_rect(parent, x, y, width, height, fill, radius=0):
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
        }
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
            "stroke": "#30363D",
            "stroke-width": "1",
        }
    )


def add_info(parent, y, label, value, color=BLUE):
    add_text(parent, INFO_X, y, label, color)

    add_text(
        parent,
        INFO_X + 145,
        y,
        value,
        TEXT
    )


def embed_avatar(parent):
    if not AVATAR_FILE.exists():
        raise FileNotFoundError(
            f"找不到头像 SVG：{AVATAR_FILE}"
        )

    tree = ET.parse(AVATAR_FILE)
    avatar_root = tree.getroot()

    original_width = float(avatar_root.get("width"))
    original_height = float(avatar_root.get("height"))

    scale = AVATAR_WIDTH / original_width

    group = ET.SubElement(
        parent,
        f"{{{SVG_NS}}}g",
        {
            "transform": (
                f"translate({AVATAR_X},{AVATAR_Y}) "
                f"scale({scale})"
            )
        }
    )

    # 只复制字符画，避免头像背景覆盖卡片
    for element in avatar_root:
        tag_name = element.tag.split("}")[-1]

        if tag_name == "rect":
            continue

        group.append(element)


def generate_profile():
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": str(WIDTH),
            "height": str(HEIGHT),
            "viewBox": f"0 0 {WIDTH} {HEIGHT}",
        }
    )

    # 背景
    add_rect(root, 0, 0, WIDTH, HEIGHT, BG, 20)

    # 终端标题栏
    add_rect(root, 0, 0, WIDTH, 55, HEADER_BG, 20)

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
            }
        )

    add_text(
        root,
        WIDTH // 2,
        35,
        "absolutezero — neofetch",
        MUTED,
        17
    ).set("text-anchor", "middle")

    # 左侧头像
    embed_avatar(root)

    # 右侧标题
    add_text(
        root,
        INFO_X,
        105,
        "AbsoluteZero001@github",
        GREEN,
        22
    )

    add_line(
        root,
        INFO_X,
        125,
        WIDTH - 50,
        125
    )

    # 个人信息
    add_info(root, 165, "OS", "Windows 11 · Linux", GREEN)
    add_info(root, 195, "Shell", "PowerShell · Bash", GREEN)
    add_info(root, 225, "Role", "Java Backend Developer", GREEN)
    add_info(root, 255, "Stack", "Spring Boot · MySQL", GREEN)

    # GitHub 数据占位
    add_info(root, 315, "Repos", "--")
    add_info(root, 345, "Stars", "--", YELLOW)
    add_info(root, 375, "Forks", "--")
    add_info(root, 405, "Followers", "--")
    add_info(root, 435, "Commits", "--")

    # 个人方向
    add_info(root, 495, "Focus", "Backend · DevOps", GREEN)
    add_info(root, 525, "Site", "evezero.cn", GREEN)

    add_line(
        root,
        INFO_X,
        550,
        WIDTH - 50,
        550
    )

    # 语言展示占位
    languages = [
        ("Java", "#F89820"),
        ("Python", "#3776AB"),
        ("Vue", "#42B883"),
        ("TypeScript", "#3178C6"),
        ("Shell", "#89E051"),
    ]

    for index, (language, color) in enumerate(languages):
        y = 590 + index * 30

        add_text(root, INFO_X, y, language, color, 18)

        add_rect(
            root,
            INFO_X + 145,
            y - 15,
            170,
            14,
            "#21262D",
            2
        )

        add_text(
            root,
            INFO_X + 330,
            y,
            "--%",
            TEXT,
            17
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    tree = ET.ElementTree(root)

    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True
    )

    # 验证生成的 SVG 是否有效
    ET.parse(OUTPUT_FILE)

    print("Neofetch 卡片生成成功！")
    print("文件：", OUTPUT_FILE)
    print("尺寸：", WIDTH, "×", HEIGHT)


if __name__ == "__main__":
    generate_profile()
