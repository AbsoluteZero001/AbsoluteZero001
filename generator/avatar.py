from pathlib import Path
import requests

GITHUB_USERNAME = "AbsoluteZero001"

def download_avatar():
    print("正在获取 GitHub 头像...")

    url = f"https://api.github.com/users/{GITHUB_USERNAME}"

    response = requests.get(url, timeout=15)
    response.raise_for_status()

    avatar_url = response.json()["avatar_url"]

    avatar_response = requests.get(avatar_url, timeout=20)
    avatar_response.raise_for_status()

    Path("cache").mkdir(exist_ok=True)

    avatar_path = Path("cache/avatar.png")
    avatar_path.write_bytes(avatar_response.content)

    print(f"头像下载成功：{avatar_path}")


if __name__ == "__main__":
    download_avatar()
