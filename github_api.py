import os
import re
import httpx
import base64
import difflib
from tenacity import retry, stop_after_attempt, wait_fixed
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

github_token = os.environ["GITHUB_TOKEN"]


async def api_request(
    url, method="GET", data=None, headers=None, files=None, is_binary=False
):
    try:
        default_headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        if headers:
            default_headers.update(headers)

        async with httpx.AsyncClient() as client:
            logger.debug(f"Requesting URL: {url} with method: {method}")
            if is_binary:
                response = await client.request(
                    method, url, content=data, headers=default_headers
                )
            else:
                response = await client.request(
                    method, url, json=data, headers=default_headers, files=files
                )
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                return response.text
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
    url = f"https://api.github.com/orgs/{org_name}/repos?per_page=100&page="
    try:
        logger.info("Fetching repositories from GitHub.")
        valid_repos = []
        for page in range(1, 5):
            repos = await api_request(f"{url}{page}")
            if not repos:
                return valid_repos
            for repo in repos:
                if repo and not repo.get("private") and not repo.get("archived"):
                    repo["languages"] = await get_languages(repo["languages_url"])
                    if not repo["languages"]:
                        continue
                    valid_repos.append(repo)
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
        readme_data = await api_request(url)
        return (
            base64.b64decode(readme_data["content"]).decode("utf-8"),
            readme_data["sha"],
        )
    except Exception as e:
        logger.error(f"Error fetching README content: {e}")
        return None, None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def update_readme(org_name, repo_name, content, sha, new_content):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/README.md"
    try:
        logger.info(f"Updating README for {repo_name}")
        new_date = datetime.now().strftime("%m/%d/%y")
        updated_readme = (
            content.split("| --- | :---: | :---: | :---: |")[0]
            + "| --- | :---: | :---: | :---: |\n"
            + new_content
        )
        updated_readme = re.sub(
            r"Current Addon List \([^)]+\)",
            f"Current Addon List ({new_date})",
            updated_readme,
        )
        commit_data = {
            "message": f"Update README with new addon list on {new_date}",
            "content": base64.b64encode(updated_readme.encode("utf-8")).decode("utf-8"),
            "sha": sha,
        }
        await api_request(url, method="PUT", data=commit_data)
    except Exception as e:
        logger.error(f"Error updating README: {e}")


async def get_latest_addon_list(org_name, repo_name):
    releases = await api_request(
        f"https://api.github.com/repos/{org_name}/{repo_name}/releases"
    )
    if releases:
        latest_release = releases[0]
        for asset in latest_release["assets"]:
            if asset["name"] == "addon_list.md":
                return await api_request(asset["browser_download_url"])
    return ""


async def create_release(org_name, repo_name, body):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/releases"
    releases = await api_request(url)

    old_addon_list = await get_latest_addon_list()
    changes = "\n".join(
        difflib.unified_diff(
            old_addon_list.splitlines(),
            body.splitlines(),
            fromfile="old_list",
            tofile="new_list",
            lineterm="",
        )
    )
    if not changes and releases:
        logger.info("No changes detected, skipping release creation.")
        return

    latest_version = len(releases) + 1
    release_note = (
        f"Automatically generated addon list\n\n### Changes:\n{body}"
        if releases
        else "Creating first release"
    )
    release_data = {
        "tag_name": f"v{latest_version}",
        "name": f"Addon List v{latest_version}",
        "body": release_note,
        "draft": False,
        "prerelease": False,
    }
    release_response = await api_request(url, method="POST", data=release_data)
    upload_url = release_response["upload_url"].replace(
        "{?name,label}", "?name=addon_list.md"
    )
    with open("addon_list.md", "rb") as f:
        file_content = f.read()

    await api_request(
        upload_url,
        method="POST",
        data=file_content,
        headers={
            "Content-Type": "application/octet-stream",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        is_binary=True,
    )
