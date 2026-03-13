# BitScale MCP Server

Connect your [BitScale](https://bitscale.ai) workspace to Claude via the [Model Context Protocol](https://modelcontextprotocol.io) (MCP).

## Setup

### 1. Install `uv` (one-time)

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
**Windows**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Add to Claude Desktop config

Open `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows) and add:

```json
{
  "mcpServers": {
    "bitscale": {
      "command": "uvx",
      "args": ["bitscale-mcp"],
      "env": {
        "BITSCALE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

That's it. No cloning, no pip install — `uvx` pulls and runs the package automatically.

---

## Tools

| Tool | Description |
|------|-------------|
| `get_workspace_details` | Get workspace name, plan, and member info |
| `list_grids` | List all Grids with optional search & pagination |
| `get_grid_details` | Fetch a Grid's column schema and row data |
| `run_grid` | Trigger a Grid run (full or selected rows) |
| `get_run_status` | Poll the status of a Grid run |
| `rotate_api_key` | Rotate the workspace API key |

---

## Usage Examples

> *"List all my BitScale grids"*

> *"Run the Leads Enrichment grid"*

> *"What columns does my Outbound grid have?"*

> *"Check the status of run xyz456 on grid abc123"*

---

## Claude Code

```bash
claude mcp add bitscale \
  --command uvx \
  --args bitscale-mcp \
  --env BITSCALE_API_KEY=your_api_key_here
```

---

## API Reference

Requests hit `https://api.bitscale.ai/api/v1`, authenticated via `X-API-KEY`. Default rate limit: **5 req/s** per workspace.

| Endpoint | Method | Tool |
|----------|--------|------|
| `/workspace` | GET | `get_workspace_details` |
| `/grids` | GET | `list_grids` |
| `/grids/:gridId` | GET | `get_grid_details` |
| `/grids/:gridId/run` | POST | `run_grid` |
| `/grids/:gridId/runs/:runId` | GET | `get_run_status` |
| `/rotate-api-key` | POST | `rotate_api_key` |

---

## ⚠️ API Key Rotation

Calling `rotate_api_key` immediately invalidates the current key. Update `BITSCALE_API_KEY` in your config and restart Claude Desktop after rotating.

---

## License

MIT