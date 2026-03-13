#!/usr/bin/env python3
"""
BitScale MCP Server
Exposes BitScale API endpoints as tools for Claude via the Model Context Protocol.

Quickstart (no cloning needed):
    Add to your claude_desktop_config.json:
    {
      "mcpServers": {
        "bitscale": {
          "command": "uvx",
          "args": ["--from", "git+https://github.com/featherflow/bitscale-mcp", "bitscale-mcp"],
          "env": { "BITSCALE_API_KEY": "your_key_here" }
        }
      }
    }
"""

import os
import json
import httpx
from mcp.server.fastmcp import FastMCP

# ── Configuration ────────────────────────────────────────────────────────────

BITSCALE_API_BASE = "https://api.bitscale.ai/api/v1"
API_KEY = os.environ.get("BITSCALE_API_KEY", "")

# ── MCP Server ───────────────────────────────────────────────────────────────

mcp = FastMCP("BitScale")


def _headers() -> dict:
    """Return the auth headers required by the BitScale API."""
    if not API_KEY:
        raise RuntimeError(
            "BITSCALE_API_KEY environment variable is not set. "
            "Set it before starting the server."
        )
    return {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json",
    }


def _get(path: str, params: dict | None = None) -> dict:
    """Perform an authenticated GET request against the BitScale API."""
    url = f"{BITSCALE_API_BASE}{path}"
    with httpx.Client(timeout=30) as client:
        response = client.get(url, headers=_headers(), params=params)
    response.raise_for_status()
    return response.json()


def _post(path: str, body: dict | None = None) -> dict:
    """Perform an authenticated POST request against the BitScale API."""
    url = f"{BITSCALE_API_BASE}{path}"
    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=_headers(), json=body or {})
    response.raise_for_status()
    return response.json()


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_workspace_details() -> str:
    """
    Retrieve details about the current BitScale workspace associated with
    the API key, including workspace ID, name, plan, and member count.

    Returns workspace metadata such as id, name, plan tier, and members.
    """
    data = _get("/workspace")
    return json.dumps(data, indent=2)


@mcp.tool()
def list_grids(
    search: str = "",
    page: int = 1,
    limit: int = 20,
) -> str:
    """
    List all Grids (spreadsheet-like tables) in the current workspace.

    Args:
        search: Optional keyword to filter grids by name.
        page:   Page number for pagination (default: 1).
        limit:  Number of grids per page (default: 20, max: 100).

    Returns a paginated list of grids with their IDs, names, column
    definitions, and row counts.
    """
    params: dict = {"page": page, "limit": limit}
    if search:
        params["search"] = search
    data = _get("/grids", params=params)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_grid_details(grid_id: str) -> str:
    """
    Retrieve detailed information about a specific Grid, including its
    column schema and current data rows.

    Args:
        grid_id: The unique identifier of the grid (e.g. "abc123").

    Returns full grid metadata plus column definitions and row data.
    """
    if not grid_id:
        raise ValueError("grid_id must not be empty")
    data = _get(f"/grids/{grid_id}")
    return json.dumps(data, indent=2)


@mcp.tool()
def run_grid(
    grid_id: str,
    row_ids: list[str] | None = None,
) -> str:
    """
    Trigger a run (execution) of a specific Grid. Optionally run only
    a subset of rows by providing their IDs.

    Args:
        grid_id: The unique identifier of the grid to run.
        row_ids: Optional list of row IDs to run. If omitted, all rows
                 are processed.

    Returns a run object containing the run_id and initial status.
    Use get_run_status to poll for completion.
    """
    if not grid_id:
        raise ValueError("grid_id must not be empty")
    body: dict = {}
    if row_ids:
        body["rowIds"] = row_ids
    data = _post(f"/grids/{grid_id}/run", body)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_run_status(grid_id: str, run_id: str) -> str:
    """
    Check the status of a previously triggered Grid run.

    Args:
        grid_id: The unique identifier of the grid.
        run_id:  The unique identifier of the run (returned by run_grid).

    Returns the run object with status ("pending", "running", "completed",
    or "failed"), progress information, and any error details.
    """
    if not grid_id:
        raise ValueError("grid_id must not be empty")
    if not run_id:
        raise ValueError("run_id must not be empty")
    data = _get(f"/grids/{grid_id}/runs/{run_id}")
    return json.dumps(data, indent=2)


@mcp.tool()
def rotate_api_key() -> str:
    """
    Rotate the current workspace API key. The existing key is immediately
    invalidated and a new key is returned.

    WARNING: After calling this tool the BITSCALE_API_KEY environment
    variable must be updated with the returned key, and the MCP server
    must be restarted, otherwise subsequent tool calls will fail with 401.

    Returns the new API key string.
    """
    data = _post("/rotate-api-key")
    return json.dumps(data, indent=2)


# ── Entry Point ──────────────────────────────────────────────────────────────

def run():
    """Entry point used by the pyproject.toml console script."""
    mcp.run()


if __name__ == "__main__":
    run()