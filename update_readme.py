import os
import re
from datetime import datetime
from pathlib import Path

import requests


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
        if repo_name == "yafyx":
            continue

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


def get_lastfm_recent_tracks(username, api_key, limit=3):
    url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={username}&api_key={api_key}&format=json&limit={limit}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tracks = data["recenttracks"]["track"]
        return [
            {
                "name": track["name"],
                "artist": track["artist"]["#text"],
                "image": track["image"][-1]["#text"],
            }
            for track in tracks
        ]
    else:
        print(
            f"Error: Last.fm API request failed with status code {response.status_code}"
        )
        return []


def get_lastfm_top_tracks(username, api_key, limit=3, period="1month"):
    url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user={username}&api_key={api_key}&format=json&limit={limit}&period={period}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tracks = data["toptracks"]["track"]
        return [
            {
                "name": track["name"],
                "artist": track["artist"]["name"],
                "image": track["image"][-1]["#text"],
            }
            for track in tracks
        ]
    else:
        print(
            f"Error: Last.fm API request failed with status code {response.status_code}"
        )
        return []


def update_readme(commits, recent_tracks, top_tracks):
    root = Path(__file__).resolve().parent
    readme_path = root / "README.md"
    old_readme = readme_path.open().read()

    commits_md = "\n\n".join(
        f"[{commit['repo']}]({commit['url']}): {commit['message']} - {format_date(commit['date'])}"
        for commit in commits[:10]  # Limit to 10 most recent commits
    )

    recent_tracks_md = "\n\n".join(
        f'<img src="{track["image"]}" width="48" height="48" align="left" style="margin-right: 10px;"/>'
        f'**{track["name"]}**<br>{track["artist"]}<br clear="left">'
        for track in recent_tracks
    )

    top_tracks_md = "\n\n".join(
        f'<img src="{track["image"]}" width="48" height="48" align="left" style="margin-right: 10px;"/>'
        f'**{track["name"]}**<br>{track["artist"]}<br clear="left">'
        for i, track in enumerate(top_tracks, 1)
    )

    new_readme = old_readme
    new_readme = replace_chunk(new_readme, "recent_commits", commits_md)
    new_readme = replace_chunk(new_readme, "recent_tracks", recent_tracks_md)
    new_readme = replace_chunk(new_readme, "top_tracks", top_tracks_md)

    if new_readme != old_readme:
        readme_path.open("w").write(new_readme)
        return True
    return False


if __name__ == "__main__":
    commits = get_recent_commits()

    lastfm_username = os.environ.get("LASTFM_USERNAME", "")
    lastfm_api_key = os.environ.get("LASTFM_API_KEY", "")

    if not lastfm_username or not lastfm_api_key:
        print("Error: Last.fm username or API key not set in environment variables.")
        exit(1)

    recent_tracks = get_lastfm_recent_tracks(lastfm_username, lastfm_api_key)
    top_tracks = get_lastfm_top_tracks(lastfm_username, lastfm_api_key)

    if commits and recent_tracks and top_tracks:
        tracks_changed = update_readme(commits, recent_tracks, top_tracks)
        if tracks_changed:
            print("TRACKS_CHANGED=true")
        else:
            print("TRACKS_CHANGED=false")
    else:
        print("Error occurred. README not updated.")
        exit(1)
