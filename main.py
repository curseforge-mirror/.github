import asyncio
from datetime import datetime
from github_api import get_repos, get_readme_content, update_readme, create_release

org_name = "curseforge-mirror"
repo_name = ".github"
ignore_misc = ["template", ".github", "actions-template-sync", "cloudscraper"]

out_str = "| [{0}](https://github.com/curseforge-mirror/{0}) | [![workflow badge](https://github.com/curseforge-mirror/{0}/actions/workflows/main.yml/badge.svg)](https://github.com/curseforge-mirror/{0}/actions/workflows/main.yml) | [![workflow badge](https://github.com/curseforge-mirror/{0}/actions/workflows/template-sync.yml/badge.svg)](https://github.com/curseforge-mirror/{0}/actions/workflows/template-sync.yml) | [![download badge](https://img.shields.io/github/downloads/curseforge-mirror/{0}/total)](https://github.com/curseforge-mirror/{0}/releases) |"
small_out_str = "| [{0}](https://github.com/curseforge-mirror/{0}) | [![workflow badge](https://github.com/curseforge-mirror/{0}/actions/workflows/main.yml/badge.svg)](https://github.com/curseforge-mirror/{0}/actions/workflows/main.yml) | n/a | [![download badge](https://img.shields.io/github/downloads/curseforge-mirror/{0}/total)](https://github.com/curseforge-mirror/{0}/releases) |"


async def main():
    markdown_content = []
    repos = await get_repos(org_name)

    for repo in repos:
        if (
            repo["name"] not in ignore_misc
            and not repo["private"]
            and not repo["archived"]
        ):
            if "Lua" not in repo["languages"] or (
                repo["languages"]["Lua"] < max(repo["languages"].values())
            ):
                markdown_content.append(out_str.format(repo["name"]))
            else:
                markdown_content.append(small_out_str.format(repo["name"]))

    new_addon_list = "\n".join(markdown_content)

    readme_content, readme_sha = await get_readme_content(org_name, repo_name)
    await update_readme(readme_content, readme_sha, new_addon_list, org_name, repo_name)

    current_date = datetime.now().strftime("%m/%d/%y")
    release_note = f"Addon list updated on {current_date}"
    await create_release(org_name, repo_name, release_note, new_addon_list)


if __name__ == "__main__":
    asyncio.run(main())