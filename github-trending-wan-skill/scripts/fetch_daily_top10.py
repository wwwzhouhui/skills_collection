#!/usr/bin/env python3
"""Fetch GitHub trending top repositories and enrich them for poster generation."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TRENDING_URL = "https://github.com/trending"
TRENDING_FALLBACK_URL = "https://github.com/trending?spoken_language_code=en"
GITHUB_API = "https://api.github.com"
GITHUB_WEB = "https://github.com"
RAW_GITHUB = "https://raw.githubusercontent.com"
DEFAULT_TOP_N = 5
README_MAX_CHARS = 12000
DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3
README_CANDIDATES = ("README.md", "README.MD", "readme.md", "Readme.md")
PROMPT_UNSAFE_MARKERS = ("===", "```", "<script", "</script", "<style", "</style")


def fetch_text(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = Request(url, headers=headers or {})
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(min(attempt * 2, 5))
    if last_error is None:
        raise RuntimeError(f"请求失败: {url}")
    raise last_error


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(fetch_text(url, headers=headers))


def build_headers() -> dict[str, str]:
    headers = {
        "User-Agent": "github-trending-wan-skill/1.0",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def build_api_headers() -> dict[str, str]:
    headers = build_headers()
    headers["Accept"] = "application/vnd.github+json"
    return headers


def parse_trending_repos(html: str, limit: int) -> list[str]:
    patterns = [
        re.compile(
            r'<article[^>]*>.*?<h2[^>]*>.*?<a[^>]*href="(/[^/" ]+/[^/" ]+)"',
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(r'href="/([^/" ]+/[^/" ]+)"\s+data-view-component="true"'),
    ]
    repos: list[str] = []
    seen: set[str] = set()

    for pattern in patterns:
        for match in pattern.finditer(html):
            repo_path = match.group(1).strip("/")
            repo_path = repo_path.split("?", 1)[0].split("#", 1)[0]
            if repo_path.count("/") != 1:
                continue
            if repo_path.startswith(("login", "signup", "features", "sponsors", "trending")):
                continue
            if repo_path in seen:
                continue
            seen.add(repo_path)
            repos.append(repo_path)
            if len(repos) >= limit:
                return repos

    return repos


def normalize_description(text: str, repo_full_name: str) -> str:
    value = unescape((text or "").strip())
    value = re.sub(r"\s+", " ", value)
    suffix = f" - {repo_full_name}"
    if value.endswith(suffix):
        value = value[: -len(suffix)].strip()
    return value or "暂无公开描述"


def parse_count(text: str) -> int:
    normalized = re.sub(r"\s+", "", text).replace(",", "").lower()
    if not normalized:
        return 0

    multiplier = 1
    if normalized.endswith("k"):
        multiplier = 1_000
        normalized = normalized[:-1]
    elif normalized.endswith("m"):
        multiplier = 1_000_000
        normalized = normalized[:-1]

    try:
        return int(float(normalized) * multiplier)
    except ValueError:
        return 0


def extract_embedded_payload(html: str) -> dict[str, Any]:
    match = re.search(
        r'<script type="application/json" data-target="react-app\.embeddedData">([\s\S]*?)</script>',
        html,
    )
    if not match:
        return {}
    try:
        return json.loads(unescape(match.group(1)))
    except json.JSONDecodeError:
        return {}


def extract_primary_language(html: str) -> str:
    patterns = [
        r'search\?l=[^\"]+"[^>]*>[\s\S]*?<span class="color-fg-default text-bold mr-1">([^<]+)</span>',
        r'<h2 class="h4 tmp-mb-3">Languages</h2>[\s\S]*?<span class="color-fg-default text-bold mr-1">([^<]+)</span>',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return unescape(match.group(1).strip())
    return "Unknown"


def extract_topics(html: str) -> list[str]:
    matches = re.findall(r'href="/topics/([^"#?]+)"', html)
    topics: list[str] = []
    for topic in matches:
        cleaned = unescape(topic.strip())
        if cleaned and cleaned not in topics:
            topics.append(cleaned)
    return topics[:8]


def extract_social_count(html: str, repo_full_name: str, kind: str) -> int:
    patterns = {
        "stars": [
            rf'aria-label="([0-9,]+) users starred {re.escape(repo_full_name)}"',
            r'aria-label="([0-9,]+) users starred this repository"',
            rf'href="/{re.escape(repo_full_name)}/stargazers"[\s\S]*?title="([0-9,]+)"',
        ],
        "forks": [
            rf'aria-label="([0-9,]+) users forked {re.escape(repo_full_name)}"',
            rf'href="/{re.escape(repo_full_name)}/forks"[\s\S]*?<strong>([^<]+)</strong>',
            rf'href="/{re.escape(repo_full_name)}/forks"[\s\S]*?Counter[^>]*>([^<]+)</span>',
        ],
        "issues": [
            rf'href="/{re.escape(repo_full_name)}/issues"[\s\S]*?Counter[^>]*>([^<]+)</span>',
        ],
    }
    for pattern in patterns[kind]:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return parse_count(match.group(1))
    return 0


def fetch_trending_repos(limit: int, headers: dict[str, str]) -> tuple[list[str], str]:
    best_repos: list[str] = []
    best_source = TRENDING_URL
    for url in (TRENDING_URL, TRENDING_FALLBACK_URL):
        html = fetch_text(url, headers=headers)
        repos = parse_trending_repos(html, limit)
        if len(repos) > len(best_repos):
            best_repos = repos
            best_source = url
        if len(best_repos) >= limit:
            break
    if len(best_repos) < limit:
        raise RuntimeError(f"无法解析到足够的热门项目，期望 {limit} 个，实际 {len(best_repos)} 个")
    return best_repos[:limit], best_source


def fetch_repo_info_via_api(repo_full_name: str, headers: dict[str, str]) -> dict[str, Any]:
    repo_url = f"{GITHUB_API}/repos/{repo_full_name}"
    data = fetch_json(repo_url, headers=headers)
    owner = data.get("owner") or {}
    license_info = data.get("license") or {}
    return {
        "name": repo_full_name,
        "html_url": data.get("html_url") or f"{GITHUB_WEB}/{repo_full_name}",
        "description": data.get("description") or "暂无公开描述",
        "language": data.get("language") or "Unknown",
        "stargazers_count": data.get("stargazers_count") or 0,
        "forks_count": data.get("forks_count") or 0,
        "open_issues_count": data.get("open_issues_count") or 0,
        "default_branch": data.get("default_branch") or "main",
        "topics": data.get("topics") or [],
        "homepage": data.get("homepage") or "",
        "license": license_info.get("spdx_id") or license_info.get("name") or "Unknown",
        "updated_at": data.get("updated_at"),
        "owner": owner.get("login") or repo_full_name.split("/", 1)[0],
    }


def fetch_repo_info_via_html(repo_full_name: str, headers: dict[str, str]) -> dict[str, Any]:
    repo_url = f"{GITHUB_WEB}/{repo_full_name}"
    html = fetch_text(repo_url, headers=headers)
    payload = extract_embedded_payload(html)
    code_view = (payload.get("payload") or {}).get("codeViewRepoRoute") or {}
    ref_info = code_view.get("refInfo") or {}

    description_match = re.search(r'<meta name="description" content="([^"]+)"', html, re.IGNORECASE)
    return {
        "name": repo_full_name,
        "html_url": repo_url,
        "description": normalize_description(
            description_match.group(1) if description_match else "",
            repo_full_name,
        ),
        "language": extract_primary_language(html),
        "stargazers_count": extract_social_count(html, repo_full_name, "stars"),
        "forks_count": extract_social_count(html, repo_full_name, "forks"),
        "open_issues_count": extract_social_count(html, repo_full_name, "issues"),
        "default_branch": ref_info.get("name") or "main",
        "topics": extract_topics(html),
        "homepage": "",
        "license": "Unknown",
        "updated_at": None,
        "owner": repo_full_name.split("/", 1)[0],
    }


def fetch_repo_info(
    repo_full_name: str,
    api_headers: dict[str, str],
    web_headers: dict[str, str],
) -> dict[str, Any]:
    try:
        return fetch_repo_info_via_api(repo_full_name, api_headers)
    except HTTPError as exc:
        if exc.code not in (403, 404, 429):
            raise
    except (URLError, json.JSONDecodeError):
        pass
    return fetch_repo_info_via_html(repo_full_name, web_headers)


def fetch_readme_via_raw(repo_full_name: str, default_branch: str, headers: dict[str, str]) -> str:
    branches = [default_branch, "main", "master"]
    tried: set[tuple[str, str]] = set()
    for branch in branches:
        if not branch:
            continue
        for candidate in README_CANDIDATES:
            key = (branch, candidate)
            if key in tried:
                continue
            tried.add(key)
            readme_url = f"{RAW_GITHUB}/{repo_full_name}/{branch}/{candidate}"
            try:
                return fetch_text(readme_url, headers=headers)
            except HTTPError as exc:
                if exc.code == 404:
                    continue
                if exc.code in (403, 429):
                    return ""
                raise
            except URLError:
                continue
    return ""


def fetch_readme(
    repo_full_name: str,
    default_branch: str,
    api_headers: dict[str, str],
    web_headers: dict[str, str],
) -> str:
    readme_url = f"{GITHUB_API}/repos/{repo_full_name}/readme"
    readme_headers = dict(api_headers)
    readme_headers["Accept"] = "application/vnd.github.v3.raw"
    try:
        return fetch_text(readme_url, headers=readme_headers)
    except HTTPError as exc:
        if exc.code not in (403, 404, 429):
            raise
    except URLError:
        pass
    return fetch_readme_via_raw(repo_full_name, default_branch, web_headers)


def strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sanitize_prompt_text(text: str, limit: int = 240) -> str:
    normalized = strip_markdown(text or "")
    normalized = unescape(normalized)
    normalized = re.sub(r"[\r\n\t]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    for marker in PROMPT_UNSAFE_MARKERS:
        normalized = normalized.replace(marker, " ")
    normalized = re.sub(r"[{}\[\]<>]+", " ", normalized)
    normalized = normalized.strip(" -|:;,.。")
    if len(normalized) > limit:
        normalized = normalized[: limit - 1].rstrip() + "…"
    return normalized


def extract_intro(readme: str) -> str:
    lines = [line.strip() for line in readme.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line:
            if cleaned:
                break
            continue
        if line.startswith(("![", "[![", "<img", "<picture")):
            continue
        if line.startswith("#"):
            continue
        if line.startswith("<") and line.endswith(">"):
            continue
        cleaned.append(line)
        if len(cleaned) >= 3:
            break
    return strip_markdown(" ".join(cleaned))


def find_section(readme: str, keywords: list[str]) -> list[str]:
    lines = readme.splitlines()
    current: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().lower()
            if any(keyword.lower() in heading for keyword in keywords):
                capture = True
                current = []
                continue
            if capture:
                break
        if capture and stripped:
            current.append(stripped)
            if len(current) >= 6:
                break
    return current


def extract_stack(readme: str, language: str) -> list[str]:
    keywords = [
        "tech stack",
        "technology",
        "stack",
        "built with",
        "features",
        "技术栈",
        "技术选型",
        "dependencies",
    ]
    candidates = find_section(readme, keywords)
    items: list[str] = []
    for line in candidates:
        stripped = line.strip()
        if stripped.startswith(("-", "*", "•")):
            items.append(strip_markdown(stripped.lstrip("-*• ").strip()))
        elif re.match(r"^\d+\.\s+", stripped):
            items.append(strip_markdown(re.sub(r"^\d+\.\s+", "", stripped)))
        elif stripped:
            items.append(strip_markdown(stripped))
        if len(items) >= 5:
            break

    normalized = [item for item in items if item]
    if language and language not in normalized:
        normalized.insert(0, language)

    deduped: list[str] = []
    for item in normalized:
        if item not in deduped:
            deduped.append(item)
    return deduped[:5]


def guess_target_user(description: str, intro: str, topics: list[str]) -> str:
    text = " ".join([description, intro, " ".join(topics)]).lower()
    if any(keyword in text for keyword in ["agent", "llm", "ai", "model"]):
        return "AI 开发者 / Agent 应用团队"
    if any(keyword in text for keyword in ["kubernetes", "docker", "infra", "cloud", "deploy"]):
        return "平台工程 / 运维团队"
    if any(keyword in text for keyword in ["frontend", "ui", "component", "design", "browser"]):
        return "前端 / 设计工程团队"
    if any(keyword in text for keyword in ["database", "sql", "analytics", "data"]):
        return "数据平台 / 后端团队"
    return "开发者 / 技术团队"


def build_item(
    rank: int,
    repo_full_name: str,
    api_headers: dict[str, str],
    web_headers: dict[str, str],
) -> dict[str, Any]:
    info = fetch_repo_info(repo_full_name, api_headers, web_headers)
    readme = fetch_readme(repo_full_name, info["default_branch"], api_headers, web_headers)
    intro = extract_intro(readme) or info["description"]
    tech_stack = extract_stack(readme, info["language"])
    item = dict(info)
    item["rank"] = rank
    item["readme"] = readme[:README_MAX_CHARS]
    item["summary_intro"] = sanitize_prompt_text(intro, limit=220)
    item["description"] = sanitize_prompt_text(info["description"], limit=160)
    item["tech_stack"] = [sanitize_prompt_text(value, limit=60) for value in tech_stack if sanitize_prompt_text(value, limit=60)]
    item["target_users"] = guess_target_user(
        info["description"],
        intro,
        info.get("topics") or [],
    )
    return item


def build_payload(limit: int, date_label: str | None) -> dict[str, Any]:
    web_headers = build_headers()
    api_headers = build_api_headers()
    repos, source = fetch_trending_repos(limit, web_headers)
    items = [
        build_item(index, repo, api_headers, web_headers)
        for index, repo in enumerate(repos, start=1)
    ]
    generated_date = date_label or datetime.now().strftime("%Y-%m-%d")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_date": generated_date,
        "source": source,
        "top_n": limit,
        "items": items,
    }


def save_payload(payload: dict[str, Any], output_path: str) -> None:
    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch GitHub Trending Top 5 for poster generation")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N, help="Number of trending repositories to fetch")
    parser.add_argument(
        "--output",
        default="output/daily_top10.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--date-label",
        default="",
        help="Display date used in generated assets; does not change GitHub Trending source window",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = build_payload(args.top, args.date_label.strip() or None)
        save_payload(payload, args.output)
    except (HTTPError, URLError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"获取 GitHub Trending 失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"已保存: {args.output}")
    print(f"项目数量: {len(payload['items'])}")


if __name__ == "__main__":
    main()
