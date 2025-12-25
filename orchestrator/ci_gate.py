"""CI wait helper."""
import time

from orchestrator.github_client import GitHubClient
from orchestrator.util import logger


def wait_for_checks(pr_number: int, timeout_seconds: int = 600, poll_seconds: int = 15) -> bool:
    client = GitHubClient()
    start = time.time()
    while time.time() - start < timeout_seconds:
        if client.check_pr_status(pr_number):
            logger.info("PR %s checks are green", pr_number)
            return True
        logger.info("Waiting for checks on PR %s...", pr_number)
        time.sleep(poll_seconds)
    logger.error("Timeout waiting for checks on PR %s", pr_number)
    return False
