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


def _get(path: str, params: dict | None = None, timeout: int = 30) -> dict:
    """Perform an authenticated GET request against the BitScale API."""
    url = f"{BITSCALE_API_BASE}{path}"
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, headers=_headers(), params=params)
    response.raise_for_status()
    return response.json()


def _post(path: str, body: dict | None = None, timeout: int = 60) -> dict:
    """Perform an authenticated POST request against the BitScale API."""
    url = f"{BITSCALE_API_BASE}{path}"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=_headers(), json=body or {})
    response.raise_for_status()
    return response.json()


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_workspace_details() -> str:
    """
    Get details about the current BitScale workspace — plan info, credit
    balances, people/company search limits, and member counts.

    The workspace is identified automatically from the API key configured
    during MCP setup. No parameters needed.

    Returns: workspace id, name, plan (name, credits_included, billing_interval,
    next_billing_date, price), credits (total, used, remaining, plan_credits,
    rollover, topup), people_company_searches (limit, used, remaining),
    and members (total, owners, admins, editors).
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
    List all Grids in the workspace with their column definitions.

    Grids are spreadsheet-like tables in BitScale that hold data rows and
    enrichment/formula columns. Use this to discover available grids before
    running them.

    Args:
        search: Optional keyword to filter grids by name (case-insensitive
                substring match). Example: "leads" to find lead-related grids.
        page:   Page number for pagination (1-based, default: 1).
        limit:  Results per page (default: 20, max: 100).

    Returns: paginated list of grids, each with id, name, description,
    row_count, column_count, created_at, updated_at, and columns array.
    The columns array contains only runnable columns (type: enrichment,
    formula, or merge) with their id (column key), name, type, and
    dependencies.

    Use the grid id from the results to call get_grid_details or run_grid.
    """
    params: dict = {"page": page, "limit": limit}
    if search:
        params["search"] = search
    data = _get("/grids", params=params)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_grid_details(grid_id: str) -> str:
    """
    Get full metadata for a specific Grid, including all column definitions,
    grid settings, and attached data sources.

    Use this to inspect a grid's schema before running it — especially to
    find the input column keys needed for the run_grid tool.

    Args:
        grid_id: UUID of the grid. Found in the grid URL at
                 app.bitscale.ai/grid/{gridId}, or from list_grids results.

    Returns: grid id, name, description, row_count, created_at, updated_at,
    settings (auto_run, auto_dedupe, visibility, dedupe_column_id),
    columns (all columns including text, enrichment, formula, merge types
    with their id/key and name), and sources (data sources with schedule info).

    The column 'id' values are the keys you use in the 'inputs' parameter
    when calling run_grid. Text-type columns are typically the input columns.
    """
    if not grid_id:
        raise ValueError("grid_id must not be empty")
    data = _get(f"/grids/{grid_id}")
    return json.dumps(data, indent=2)


@mcp.tool()
def run_grid(
    grid_id: str,
    inputs: dict[str, str],
    mode: str = "sync",
    output_columns: list[str] | None = None,
    source_id: str | None = None,
) -> str:
    """
    Run a BitScale Grid by appending a new row with the given inputs and
    triggering all column enrichments.

    This is the primary tool for executing BitScale workflows. It adds a row
    to the grid, runs all enrichment/formula/merge columns, and returns the
    enriched outputs.

    IMPORTANT: Before calling this, use get_grid_details to find the correct
    input column keys for the grid. The 'inputs' keys must match the column
    keys shown in the grid's column definitions (text-type columns).

    Args:
        grid_id: UUID of the grid to run. Found in grid URL or list_grids.
        inputs:  Key-value map of input column keys to their values.
                 Example: {"company_name": "Acme Corp", "website": "acme.com"}
                 Use the column key (id) from get_grid_details, not the
                 display name.
        mode:    Execution mode — "sync" (default) or "async".
                 - sync: waits up to 120 seconds for completion, returns
                   outputs directly. If still processing, returns a
                   request_id to poll with get_run_status.
                 - async: returns a request_id immediately. Poll
                   get_run_status for results.
        output_columns: Optional list of column UUID keys to include in the
                        response. If omitted, all enriched columns are returned.
        source_id: Optional UUID of a specific BitScale API data source on
                   the grid. If omitted, the first available source is used.

    Returns:
    - sync completed: {mode, status: "completed", outputs: {column_id: {value, name}}}
    - sync timeout or async: {mode, status: "running", request_id, poll_url}

    If status is "running", use get_run_status with the returned request_id
    to poll for completion (every 2-5 seconds).
    """
    if not grid_id:
        raise ValueError("grid_id must not be empty")
    if not inputs:
        raise ValueError("inputs must not be empty — provide at least one input column key-value pair")

    body: dict = {
        "mode": mode,
        "inputs": inputs,
    }
    if output_columns:
        body["output_columns"] = output_columns
    if source_id:
        body["source_id"] = source_id

    # Sync mode can take up to 120s; use 130s timeout to avoid premature client timeout
    timeout = 135 if mode == "sync" else 30
    data = _post(f"/grids/{grid_id}/run", body, timeout=timeout)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_run_status(request_id: str) -> str:
    """
    Check the status of a previously triggered Grid run.

    Use this after run_grid returns a request_id (either from async mode or
    when sync mode times out after 120 seconds).

    Poll every 2-5 seconds until status is "completed" or "failed".
    Avoid polling more frequently as requests count toward the rate limit
    (5 req/sec per workspace).

    Args:
        request_id: The request_id UUID returned by run_grid.

    Returns: {mode, status, grid_id, outputs (when completed)}.
    Status is one of: "running", "completed", or "failed".
    When completed, outputs contains {column_id: {value, name}} for each
    enriched column.
    """
    if not request_id:
        raise ValueError("request_id must not be empty")
    data = _get(f"/run/status/{request_id}")
    return json.dumps(data, indent=2)


@mcp.tool()
def rotate_api_key() -> str:
    """
    Generate a new workspace API key and immediately invalidate the current one.

    WARNING: This action is irreversible. The moment this succeeds, the key
    used to call it stops working. All integrations must be updated with the
    new key immediately, and this MCP server must be restarted with the new
    BITSCALE_API_KEY environment variable.

    Returns: {"api_key": "sk-live-newkey..."} — the new workspace API key.
    """
    data = _post("/api-key/rotate")
    return json.dumps(data, indent=2)


# ── Entry Point ──────────────────────────────────────────────────────────────

def run():
    """Entry point used by the pyproject.toml console script."""
    mcp.run()


if __name__ == "__main__":
    run()
