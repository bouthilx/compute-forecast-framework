#!/usr/bin/env python3
"""
Script to create GitHub labels for the labeler action.
Run with: python scripts/setup_github_labels.py
"""

import requests

# Labels to create based on .github/labeler.yml
LABELS = [
    {"name": "package", "color": "0366d6", "description": "Changes to package code"},
    {
        "name": "documentation",
        "color": "0075ca",
        "description": "Documentation updates",
    },
    {"name": "tests", "color": "d73a49", "description": "Test-related changes"},
    {"name": "ci", "color": "28a745", "description": "CI/CD workflow changes"},
    {"name": "dependencies", "color": "6f42c1", "description": "Dependency updates"},
]


def create_labels(repo_owner, repo_name, token):
    """Create labels in GitHub repository."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    for label in LABELS:
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/labels"

        response = requests.post(url, json=label, headers=headers)

        if response.status_code == 201:
            print(f"✅ Created label: {label['name']}")
        elif response.status_code == 422:
            print(f"ℹ️  Label already exists: {label['name']}")
        else:
            print(f"❌ Failed to create label {label['name']}: {response.status_code}")
            print(response.json())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create GitHub labels for PR validation"
    )
    parser.add_argument("--owner", required=True, help="Repository owner")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument("--token", required=True, help="GitHub token")

    args = parser.parse_args()

    create_labels(args.owner, args.repo, args.token)
