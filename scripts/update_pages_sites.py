#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"
USER_AGENT = "rkeelan.github.io-pages-site-updater"


def github_request(path: str, token: str):
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": API_VERSION,
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def list_public_repos(username: str, token: str):
    page = 1

    while True:
        query = urllib.parse.urlencode(
            {
                "type": "public",
                "sort": "full_name",
                "per_page": 100,
                "page": page,
            }
        )
        repos = github_request(f"/users/{username}/repos?{query}", token)
        if not repos:
            break

        for repo in repos:
            yield repo

        if len(repos) < 100:
            break

        page += 1


def get_pages_site(owner: str, repo: str, token: str):
    try:
        return github_request(f"/repos/{owner}/{repo}/pages", token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def build_output(username: str, token: str):
    sites = []
    profile_repo_name = f"{username.lower()}.github.io"

    for repo in list_public_repos(username, token):
        if repo["name"].lower() == profile_repo_name:
            continue

        if not repo.get("has_pages"):
            continue

        pages_site = get_pages_site(repo["owner"]["login"], repo["name"], token)
        if not pages_site:
            continue

        sites.append(
            {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description") or "",
                "repo_url": repo["html_url"],
                "site_url": pages_site["html_url"],
            }
        )

    sites.sort(key=lambda site: site["name"].lower())

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sites": sites,
    }


def main():
    username = os.environ.get("GITHUB_USERNAME", "RKeelan")
    token = os.environ.get("GITHUB_TOKEN")
    output_path = Path(
        os.environ.get("OUTPUT_PATH", "data/pages-sites.json")
    )

    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    output = build_output(username, token)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
