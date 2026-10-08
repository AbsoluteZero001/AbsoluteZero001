import os
import requests

from datetime import datetime, timezone


USERNAME = "AbsoluteZero001"

API_URL = f"https://api.github.com/users/{USERNAME}"


def get_github_data():

    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AbsoluteZero-Profile"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        API_URL,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    user = response.json()

    # GitHub 注册时间
    created_at = datetime.fromisoformat(
        user["created_at"].replace("Z", "+00:00")
    )

    now = datetime.now(timezone.utc)

    # 计算注册至今的完整年月
    years = now.year - created_at.year
    months = now.month - created_at.month

    if now.day < created_at.day:
        months -= 1

    if months < 0:
        years -= 1
        months += 12

    uptime = f"{years} years, {months} months"

    return {
        "username": user["login"],
        "repos": user["public_repos"],
        "followers": user["followers"],
        "following": user["following"],
        "uptime": uptime,
        "created_at": user["created_at"]
    }


if __name__ == "__main__":

    data = get_github_data()

    for key, value in data.items():
        print(f"{key}: {value}")
