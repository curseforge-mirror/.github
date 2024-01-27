import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def api_request(url, method="GET", data=None, headers=None):
    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Requesting URL: {url} with method: {method}")
            response = await client.request(method, url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 451:
            logger.warning(f"Repository unavailable due to legal reasons: {url}")
            return None
        logger.error(f"HTTP error occurred: {e}")
        raise
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_repos(org_name):
    url = f"https://api.github.com/orgs/{org_name}/repos"
    try:
        logger.info("Fetching repositories from GitHub.")
        repos = await api_request(url)
        valid_repos = []
        for repo in repos:
            if repo and not repo.get("private") and not repo.get("archived"):
                repo["languages"] = await get_languages(repo["languages_url"])
                valid_repos.append(repo)
        return valid_repos
    except Exception as e:
        logger.error(f"Error fetching repositories: {e}")
        return []


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_languages(languages_url):
    try:
        logger.debug(f"Fetching languages from {languages_url}")
        return await api_request(languages_url)
    except Exception as e:
        logger.error(f"Error fetching languages: {e}")
        return {}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_readme_content(org_name, repo_name):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/README.md"
    try:
        logger.info(f"Fetching README content for {repo_name}")
        return await api_request(url)
    except Exception as e:
        logger.error(f"Error fetching README content: {e}")
        return None, None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def update_readme(org_name, repo_name, content, sha, new_content):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/README.md"
    try:
        logger.info(f"Updating README for {repo_name}")
        data = {"message": "Update README.md", "content": new_content, "sha": sha}
        await api_request(url, method="PUT", data=data)
    except Exception as e:
        logger.error(f"Error updating README: {e}")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def create_release(org_name, repo_name, tag_name, release_name, body):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/releases"
    try:
        logger.info(f"Creating release {release_name} for {repo_name}")
        data = {
            "tag_name": tag_name,
            "name": release_name,
            "body": body,
            "draft": False,
            "prerelease": False,
        }
        await api_request(url, method="POST", data=data)
    except Exception as e:
        logger.error(f"Error creating release: {e}")
