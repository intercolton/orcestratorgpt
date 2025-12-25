"""Minimal GitHub client placeholder."""
from typing import Optional

import requests

from orchestrator.config import get_settings
from orchestrator.util import logger


class GitHubClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        if self.settings.github_token:
            self.session.headers.update({"Authorization": f"Bearer {self.settings.github_token}"})
        self.session.headers.update({"Accept": "application/vnd.github+json"})

    def create_branch(self, base_sha: str, branch: str) -> None:
        logger.info("[GitHub] create_branch %s -> %s", base_sha, branch)
        if not self.settings.github_repo:
            logger.warning("GITHUB_REPO not set; skipping branch creation")
            return
        owner_repo = self.settings.github_repo
        url = f"{self.base_url}/repos/{owner_repo}/git/refs"
        payload = {"ref": f"refs/heads/{branch}", "sha": base_sha}
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"GitHub branch create failed: {resp.text}")

    def create_pull_request(self, title: str, head: str, base: str = "main", body: str | None = None) -> Optional[int]:
        logger.info("[GitHub] create PR %s", title)
        if not self.settings.github_repo:
            logger.warning("GITHUB_REPO not set; skipping PR")
            return None
        url = f"{self.base_url}/repos/{self.settings.github_repo}/pulls"
        resp = self.session.post(url, json={"title": title, "head": head, "base": base, "body": body or ""})
        if resp.status_code >= 400:
            raise RuntimeError(f"GitHub PR create failed: {resp.text}")
        return resp.json().get("number")

    def comment_pull_request(self, pr_number: int, body: str) -> None:
        if not self.settings.github_repo:
            logger.warning("GITHUB_REPO not set; skipping PR comment")
            return
        url = f"{self.base_url}/repos/{self.settings.github_repo}/issues/{pr_number}/comments"
        resp = self.session.post(url, json={"body": body})
        if resp.status_code >= 400:
            raise RuntimeError(f"GitHub comment failed: {resp.text}")

    def check_pr_status(self, pr_number: int) -> bool:
        if not self.settings.github_repo:
            logger.warning("GITHUB_REPO not set; assuming checks green")
            return True
        url = f"{self.base_url}/repos/{self.settings.github_repo}/pulls/{pr_number}"
        resp = self.session.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"GitHub PR fetch failed: {resp.text}")
        state = resp.json().get("mergeable_state")
        return state in {"clean", "has_hooks"}
