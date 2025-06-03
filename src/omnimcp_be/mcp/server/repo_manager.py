"""
Repository manager for MCP servers.
"""

import os
import shutil
import subprocess
import tempfile
import uuid
from typing import Dict, Optional, Tuple

import structlog


class RepoManager:
    """Manages Git repositories for MCP servers."""

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the repository manager.

        Args:
            base_dir: Base directory for storing cloned repositories.
                     If None, a temporary directory will be used.
        """
        # 设置基础目录
        self.base_dir = (
            base_dir
            if base_dir is not None
            else os.path.join(tempfile.gettempdir(), "mcp_repo")
        )

        # 设置仓库目录
        self.repos_dir = os.path.join(self.base_dir, "mcp_repos")
        self.repos: Dict[str, str] = {}  # repo_id -> path
        self.logger = structlog.get_logger()

        # 创建仓库目录（如果不存在）
        os.makedirs(self.repos_dir, exist_ok=True)

    async def clone_repo(
        self, repo_url: str, branch: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Clone a Git repository.

        Args:
            repo_url: URL of the Git repository
            branch: Optional branch name to checkout

        Returns:
            Tuple of (repo_id, repo_path, org_name, repo_name)
        """
        repo_id = str(uuid.uuid4())
        repo_path = os.path.join(self.repos_dir, repo_id)

        try:
            # Clone the repository
            cmd = ["git", "clone"]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([repo_url, repo_path])

            self.logger.info(f"Running command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)

            self.repos[repo_id] = repo_path
            return repo_id, repo_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repository: {e.stderr}")
            # Clean up directory if it was created
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
            raise

    async def find_yaml(
        self, repo_path: str, base_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Find smithery.yaml or omnimcp.yaml file in the repository.

        Args:
            repo_path: Path to the repository
            base_dir: Optional base directory to look in

        Returns:
            Path to smithery.yaml or omnimcp.yaml if found, None otherwise
        """
        search_path = os.path.join(repo_path, base_dir) if base_dir else repo_path

        # Look for smithery.yaml or omnimcp.yaml in the specified directory
        for yaml_name in ["smithery.yaml", "omnimcp.yaml"]:
            yaml_path = os.path.join(search_path, yaml_name)
            if os.path.isfile(yaml_path):
                return yaml_path

        return None

    async def find_dockerfile(
        self, repo_path: str, base_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Find Dockerfile in the repository root.

        Args:
            repo_path: Path to the repository
            base_dir: Optional base directory to look in

        Returns:
            Path to Dockerfile if found, None otherwise
        """
        search_path = os.path.join(repo_path, base_dir) if base_dir else repo_path

        # 只检查根目录下的Dockerfile
        dockerfile_path = os.path.join(search_path, "Dockerfile")
        if os.path.isfile(dockerfile_path):
            return dockerfile_path

        return None

    async def cleanup_repo(self, repo_id: str) -> None:
        """
        Remove a cloned repository.

        Args:
            repo_id: ID of the repository to remove
        """
        if repo_id not in self.repos:
            return

        repo_path = self.repos[repo_id]

        try:
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
            del self.repos[repo_id]
            self.logger.info(f"Cleaned up repository {repo_id}")
        except Exception as e:
            self.logger.error(f"Error cleaning up repository {repo_id}: {e}")
            raise
