from pathlib import Path
from PIL import Image, ImageEnhance
from html import escape


# ASCII 字符密度：从深到浅
ASCII_CHARS = "@%#*+=-:. "

# 字符画宽度
ASCII_WIDTH = 85

# 字符尺寸
CHAR_WIDTH = 8
CHAR_HEIGHT = 13

# 输出路径
OUTPUT_FILE = Path("cache/avatar.svg")


def image_to_ascii(image_path):

    image = Image.open(image_path).convert("RGB")

    # 增强对比度，让字符轮廓更清晰
    image = ImageEnhance.Contrast(image).enhance(1.25)

    # 根据原图比例计算字符行数
    aspect_ratio = image.height / image.width

    ascii_height = max(
        1,
        round(
            ASCII_WIDTH
            * aspect_ratio
            * CHAR_WIDTH
            / CHAR_HEIGHT
        )
    )

    image = image.resize(
        (ASCII_WIDTH, ascii_height),
        Image.Resampling.LANCZOS
    )

    lines = []

    for y in range(ascii_height):

        row = []

        for x in range(ASCII_WIDTH):

            r, g, b = image.getpixel((x, y))

            # 计算像素亮度
            brightness = (
                0.2126 * r
                + 0.7152 * g
                + 0.0722 * b
            )

            index = int(
                brightness / 255 * (len(ASCII_CHARS) - 1)
            )

            char = ASCII_CHARS[index]

            # 保留 RGB 颜色
            color = f"#{r:02x}{g:02x}{b:02x}"

            row.append((char, color))

        lines.append(row)

    return lines


def generate_svg(lines):

    width = ASCII_WIDTH * CHAR_WIDTH + 40
    height = len(lines) * CHAR_HEIGHT + 40

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',

        '<rect width="100%" height="100%" '
        'fill="#0D1117"/>'
    ]

    for y, row in enumerate(lines):

        for x, (char, color) in enumerate(row):

            if char == " ":
                continue

            pos_x = 20 + x * CHAR_WIDTH
            pos_y = 20 + (y + 1) * CHAR_HEIGHT

            svg.append(
                f'<text x="{pos_x}" y="{pos_y}" '
                f'fill="{color}" '
                f'font-family="monospace" '
                f'font-size="13" '
                f'xml:space="preserve">'
                f'{escape(char)}'
                f'</text>'
            )

    svg.append("</svg>")

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.write_text(
        "\n".join(svg),
        encoding="utf-8"
    )

    print(f"ASCII SVG 已生成：{OUTPUT_FILE}")
    print(f"SVG 尺寸：{width} × {height}")


if __name__ == "__main__":

    image_path = Path("cache/avatar.png")

    if not image_path.exists():
        raise FileNotFoundError(
            "未找到头像，请先运行 avatar.py"
        )

    lines = image_to_ascii(image_path)

    generate_svg(lines)
