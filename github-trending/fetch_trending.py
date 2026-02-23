import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TRENDING_URL = "https://github.com/trending"
GITHUB_API = "https://api.github.com"


def fetch_text(url, headers=None):
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url, headers=None):
    content = fetch_text(url, headers=headers)
    return json.loads(content)


def build_headers():
    headers = {
        "User-Agent": "github-trending-skill/1.0",
        "Accept": "application/vnd.github+json",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def parse_trending_repos(html):
    # GitHub trending 页面结构已更新，使用更宽松的匹配模式
    # 匹配 article 中的 h2 标题链接
    pattern = re.compile(r'<article[^>]*>.*?<h2[^>]*>.*?<a[^>]*href="(/[^/"]+/[^/"]+)"', re.IGNORECASE | re.DOTALL)
    repos = []
    seen = set()
    for match in pattern.finditer(html):
        repo_path = match.group(1).strip("/")
        if repo_path.count("/") != 1:
            continue
        if repo_path.startswith("login") or repo_path.startswith("signup"):
            continue
        if repo_path in seen:
            continue
        seen.add(repo_path)
        repos.append(repo_path)
        if len(repos) >= 5:
            break
    return repos


def fetch_repo_info(repo_full_name, headers):
    repo_url = f"{GITHUB_API}/repos/{repo_full_name}"
    data = fetch_json(repo_url, headers=headers)
    return {
        "name": repo_full_name,
        "html_url": data.get("html_url"),
        "description": data.get("description"),
        "language": data.get("language"),
        "stargazers_count": data.get("stargazers_count"),
        "default_branch": data.get("default_branch"),
    }


def fetch_readme(repo_full_name, headers):
    readme_url = f"{GITHUB_API}/repos/{repo_full_name}/readme"
    readme_headers = dict(headers)
    readme_headers["Accept"] = "application/vnd.github.v3.raw"
    try:
        return fetch_text(readme_url, headers=readme_headers)
    except HTTPError as exc:
        if exc.code == 404:
            return ""
        raise


def build_payload(repos, headers):
    items = []
    for index, repo in enumerate(repos, start=1):
        info = fetch_repo_info(repo, headers)
        readme = fetch_readme(repo, headers)
        item = dict(info)
        item["rank"] = index
        item["readme"] = readme
        items.append(item)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": TRENDING_URL,
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="trending_top5.json")
    args = parser.parse_args()

    headers = build_headers()
    try:
        html = fetch_text(TRENDING_URL, headers=headers)
        repos = parse_trending_repos(html)
        if len(repos) < 5:
            raise RuntimeError("无法解析到足够的热门项目")
        payload = build_payload(repos, headers)
    except (HTTPError, URLError, RuntimeError) as exc:
        print(f"获取 trending 失败: {exc}", file=sys.stderr)
        raise SystemExit(1)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    print(f"已保存: {args.output}")


if __name__ == "__main__":
    main()
