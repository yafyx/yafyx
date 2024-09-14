import os
import re
from datetime import datetime
from pathlib import Path

import requests


def get_recent_commits():
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Authorization": f"token {token}"}
    url = "https://api.github.com/users/yafyx/events"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: API request failed with status code {response.status_code}")
        return []

    try:
        events = response.json()
    except ValueError:
        print("Error: Unable to parse JSON response")
        return []

    if not isinstance(events, list):
        print(f"Error: Unexpected response format. Expected a list, got {type(events)}")
        return []

    commits = []
    for event in events:
        if not isinstance(event, dict):
            print(f"Warning: Skipping event, expected dict, got {type(event)}")
            continue

        if event.get("type") == "PushEvent":
            payload = event.get("payload", {})
            repo = event.get("repo", {})
            for commit in payload.get("commits", []):
                repo_name = repo.get("name", "Unknown")
                commit_message = commit.get("message", "").split("\n")[
                    0
                ]  # Get first line of commit message
                commit_sha = commit.get("sha", "")
                commit_url = (
                    f"https://github.com/{repo_name}/commit/{commit_sha}"
                    if commit_sha
                    else "#"
                )
                commits.append(
                    {
                        "repo": repo_name,
                        "message": commit_message,
                        "url": commit_url,
                        "date": event.get("created_at", ""),
                    }
                )
                if len(commits) == 5:  # Limit to 5 recent commits
                    return commits
    return commits


def update_readme(commits):
    root = Path(__file__).resolve().parent
    readme_path = root / "README.md"
    readme = readme_path.open().read()

    commits_md = "\n".join(
        f"* [{commit['repo']}]({commit['url']}): {commit['message']} - {commit['date'].split('T')[0]}"
        for commit in commits
    )

    readme = replace_chunk(readme, "recent_commits", commits_md)

    readme_path.open("w").write(readme)


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
