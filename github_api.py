import httpx
from utils import async_retry


@async_retry
async def api_request(url, method="GET", data=None, headers=None):
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_repos(org_name):
    url = f"https://api.github.com/orgs/{org_name}/repos"
    repos = await api_request(url)
    for repo in repos:
        repo["languages"] = await get_languages(repo["languages_url"])
    return repos


async def get_languages(languages_url):
    return await api_request(languages_url)


async def get_readme_content(org_name, repo_name):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/README.md"
    readme_data = await api_request(url)
    return readme_data["content"], readme_data["sha"]


async def update_readme(content, sha, new_addon_list, org_name, repo_name):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/README.md"
    updated_content = (
        content.split("| --- | :---: | :---: | :---: |")[0]
        + "| --- | :---: | :---: | :---: |\n"
        + new_addon_list
    )
    data = {"message": "Update README", "content": updated_content, "sha": sha}
    await api_request(url, method="PUT", data=data)


async def create_release(org_name, repo_name, release_note, new_addon_list):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/releases"
    release_data = {
        "tag_name": "new_release",
        "name": "New Addon List Release",
        "body": release_note,
        "draft": False,
        "prerelease": False,
    }
    await api_request(url, method="POST", data=release_data)
