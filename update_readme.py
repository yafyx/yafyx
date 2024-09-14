import os
import re
from datetime import datetime
from pathlib import Path

import requests


def get_recent_commits():
    token = os.environ.get("YAFYX_TOKEN", "")
    headers = {"Authorization": f"token {token}"}

    repos_url = "https://api.github.com/users/yafyx/repos?per_page=100"
    repos_response = requests.get(repos_url, headers=headers)

    if repos_response.status_code != 200:
        print(
            f"Error: Repos API request failed with status code {repos_response.status_code}"
        )
        return []

    repos = repos_response.json()

    commits = []
    for repo in repos:
        repo_name = repo["name"]
        commits_url = (
            f"https://api.github.com/repos/yafyx/{repo_name}/commits?per_page=1"
        )
        commits_response = requests.get(commits_url, headers=headers)

        if commits_response.status_code != 200:
            print(
                f"Error: Commits API request failed for {repo_name} with status code {commits_response.status_code}"
            )
            continue

        repo_commits = commits_response.json()
        if repo_commits:
            commit = repo_commits[0]
            commits.append(
                {
                    "repo": repo_name,
                    "message": commit["commit"]["message"].split("\n")[
                        0
                    ],  # Get first line of commit message
                    "url": commit["html_url"],
                    "date": commit["commit"]["author"]["date"],
                }
            )

    # Sort commits by date, most recent first
    commits.sort(key=lambda x: x["date"], reverse=True)

    return commits


def update_readme(commits):
    root = Path(__file__).resolve().parent
    readme_path = root / "README.md"
    readme = readme_path.open().read()

    commits_md = "\n\n".join(
        f"[{commit['repo']}]({commit['url']}): {commit['message']} - {format_date(commit['date'])}"
        for commit in commits[:10]  # Limit to 10 most recent commits
    )

    readme = replace_chunk(readme, "recent_commits", commits_md)

    readme_path.open("w").write(readme)


def format_date(date_string):
    date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    return date.strftime("%d-%m-%Y")


def replace_chunk(content, marker, chunk):
    r = f"<!-- {marker} starts -->.*<!-- {marker} ends -->"
    return re.sub(
        r,
        f"<!-- {marker} starts -->\n{chunk}\n<!-- {marker} ends -->",
        content,
        flags=re.DOTALL,
    )


if __name__ == "__main__":
    commits = get_recent_commits()
    if commits:
        update_readme(commits)
    else:
        print("No commits found or error occurred. README not updated.")
