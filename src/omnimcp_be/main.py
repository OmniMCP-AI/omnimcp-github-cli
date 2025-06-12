import asyncio
import uuid
import json
import os
import time
import jwt
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Literal, List

import uvicorn
import structlog
import subprocess
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp_proxy.proxy_server import create_proxy_server
from mcp_proxy.sse_server import SseServerSettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.responses import Response, JSONResponse

from omnimcp_be.setting import SETTINGS
from omnimcp_be.mcp.server.repo_manager import RepoManager
from omnimcp_be.util.github_util import extract_github_info

repo_manager = RepoManager()

logger = structlog.get_logger(__name__)

def build_docker_image(
        build_path: str,
        dockerfile_path: str,
        image_tag: str,
        registry_username: Optional[str] = "rolexai",
        registry_password: Optional[str] = "dckr_pat_9_U23ZTfVFM9iAwUq1P8jSdvNvs"
) -> str:
    try:
        # 如果提供了认证信息，先登录Docker Registry
        if registry_username and registry_password:

            login_cmd = [
                "docker",
                "login",
                "https://registry-1.docker.io/v2/",
                "--username", registry_username,
                "--password", registry_password
            ]

            logger.info(f"Building Docker image, cmd: {' '.join(login_cmd)}")
            # 使用管道隐藏密码
            subprocess.run(
                login_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Docker registry login successful")

        # 构建Docker镜像
        cmd = [
            "docker",
            "build",
            "-t",
            image_tag,
            "-f",
            dockerfile_path,
            build_path,
        ]
        logger.info(f"Building Docker image, cmd: {' '.join(cmd)}")

        subprocess.run(cmd, capture_output=True, text=True, check=True)

        logger.info(f"Docker image {image_tag} built successfully")

        return image_tag

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to build Docker image: {e.stderr}")
        raise


def create_starlette_app(
    mcp_server: Server[object],
    *,
    endpoint: str = "/messages/",
    allow_origins: list[str] | None = None,
    debug: bool = False,
) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport(endpoint)

    async def handle_sse(request: Request) -> None:
        
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    middleware: list[Middleware] = []
    if allow_origins is not None:
        middleware.append(
            Middleware(
                CORSMiddleware,
                allow_origins=allow_origins,
                allow_methods=["*"],
                allow_headers=["*"],
            ),
        )

    return Starlette(
        debug=debug,
        middleware=middleware,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/login", endpoint=login, methods=["POST"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


async def run_sse_server(
    stdio_params: StdioServerParameters,
    sse_settings: SseServerSettings,
    endpoint: str = "/messages/",
) -> None:
    """Run the stdio client and expose an SSE server.

    Args:
        stdio_params: The parameters for the stdio client that spawns a stdio server.
        sse_settings: The settings for the SSE server that accepts incoming requests.

    """
    async with (
        stdio_client(stdio_params) as streams,
        ClientSession(*streams) as session,
    ):
        mcp_server = await create_proxy_server(session)

        # Bind SSE request handling to MCP server
        starlette_app = create_starlette_app(
            mcp_server,
            allow_origins=sse_settings.allow_origins,
            debug=(sse_settings.log_level == "DEBUG"),
            endpoint=endpoint,
        )

        # Configure HTTP server
        config = uvicorn.Config(
            starlette_app,
            host=sse_settings.bind_host,
            port=sse_settings.port,
            log_level=sse_settings.log_level.lower(),
        )
        http_server = uvicorn.Server(config)
        await http_server.serve()


async def run_docker_proxy(
        message_endpoint: Optional[str] = "/messages/",
) -> str:
    unique_id = str(uuid.uuid4())
    env_str = os.getenv("CONFIG", "{}")

    logger.info(f"Starting docker proxy, unique_id: {unique_id}")
    env = json.loads(env_str)
    repo_url = env.get("github_url")
    if repo_url is None:
        raise RuntimeError("Github URL must be configured")
    repository_info = extract_github_info(repo_url)
    (repo_id, repo_path) = await repo_manager.clone_repo(
        repository_info.repo_url, repository_info.branch
    )
    build_path = os.path.join(repo_path, repository_info.base_dir or "")
    dockerfile_path = await repo_manager.find_dockerfile(
        repo_path, repository_info.base_dir
    )

    build_docker_image(build_path, dockerfile_path, unique_id)

    # image_name = "asia-southeast1-docker.pkg.dev/xc-project-443209/repo/duckduckgo-mcp-server"

    args = ["run", "--rm", "-i", "--name", "duckduckgo-mcp-server"]

    if env:
        for key, value in env.items():
            args.append("-e")
            args.append(f"{key}={value}")
    args.append(unique_id)

    server_settings = SseServerSettings(
        bind_host="0.0.0.0",
        port=3333,
        allow_origins=["*"],
    )

    stdio_params = StdioServerParameters(
        command="docker",
        args=args,
        env=env,
    )

    logger.info(f"mcp stdio params: {stdio_params.model_dump_json()}")

    await run_sse_server(stdio_params, server_settings, message_endpoint)


if __name__ == '__main__':
    asyncio.run(run_docker_proxy())
