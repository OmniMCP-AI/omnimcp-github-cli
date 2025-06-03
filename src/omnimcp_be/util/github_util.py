import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class RepositoryInfo:
    """
    Data class to represent GitHub repository information.
    """

    repo_url: str
    org_name: str
    repo_name: str
    full_repo_url: str
    branch: Optional[str] = None
    base_dir: Optional[str] = None

    @property
    def full_name(self) -> str:
        """Returns the full name of the repository in format org_name/repo_name"""
        return f"{self.org_name}/{self.repo_name}"

    @property
    def api_url(self) -> str:
        """Returns the GitHub API URL for this repository"""
        return f"https://api.github.com/repos/{self.full_name}"


def is_github_repo_url(url: str) -> bool:
    """
    Check if the provided URL is a valid GitHub repository URL.

    Args:
        url: The URL to check

    Returns:
        bool: True if it's a valid GitHub repo URL, False otherwise
    """
    if url is None:
        return False

    # Pattern to match GitHub repository URLs
    # Matches: https://github.com/username/repo, github.com/username/repo,
    # git@github.com:username/repo.git, etc.
    github_patterns = [
        r"^https?://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?.*$",
        r"^git@github\.com:[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+\.git$",
    ]

    for pattern in github_patterns:
        if re.match(pattern, url):
            return True

    return False


def extract_github_info(url: str) -> RepositoryInfo:
    if not is_github_repo_url(url):
        raise Exception("Invalid GitHub URL")

    # Extract org_name and repo_name
    org_name = ""
    repo_name = ""

    clean_url = url
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4]

    # Handle SSH URL format (git@github.com:org/repo.git)
    if clean_url.startswith("git@"):
        parts = clean_url.split(":")
        if len(parts) >= 2:
            path_parts = parts[1].split("/")
            if len(path_parts) >= 2:
                org_name = path_parts[0]
                repo_name = path_parts[1]
    else:
        # Handle HTTPS URL format
        url_parts = clean_url.split("/")
        if len(url_parts) >= 5 and "github.com" in url_parts:
            github_index = url_parts.index("github.com")
            if len(url_parts) > github_index + 2:
                org_name = url_parts[github_index + 1]
                # Handle additional paths
                repo_name = url_parts[github_index + 2].split("/")[0]

    # Pattern to match GitHub URLs with tree path
    tree_pattern = (
        r"^(https?://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)(/tree/([^/]+))(/.*)?$"
    )
    match = re.match(tree_pattern, url)

    repo_url = url
    branch = None
    base_dir = None

    if match:
        repo_url = match.group(1)
        branch = match.group(3)  # Extract the branch name
        base_dir_match = match.group(4)

        if base_dir_match:
            # Remove leading slash
            base_dir = base_dir_match.lstrip("/")

            # Extract the last directory from the path as repo_name if base_dir exists
            if base_dir:
                base_dir_parts = base_dir.rstrip("/").split("/")
                if base_dir_parts:
                    repo_name = base_dir_parts[-1]

    return RepositoryInfo(
        repo_url=repo_url,
        org_name=org_name,
        repo_name=repo_name,
        branch=branch,
        base_dir=base_dir,
        full_repo_url=url,
    )


if __name__ == "__main__":
    test_url = "https://github.com/smithery-ai/reference-servers/tree/main/src/sequentialthinking"
    repo_info = extract_github_info(test_url)
    print(f"Repository URL: {repo_info.repo_url}")
    print(f"Organization: {repo_info.org_name}")
    print(f"Repository: {repo_info.repo_name}")
    print(f"Full Name: {repo_info.full_name}")
    print(f"Branch: {repo_info.branch}")
    print(f"Base Directory: {repo_info.base_dir}")
    print(f"API URL: {repo_info.api_url}")
    print(f"Full Repository URL: {repo_info.full_repo_url}")
