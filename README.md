# BitScale MCP Server

Connect your [BitScale](https://bitscale.ai) workspace to Claude via the [Model Context Protocol](https://modelcontextprotocol.io) (MCP).

## Setup

### 1. Install `uv` (one-time)

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
or bew install uv
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
| `get_workspace_details` | Get workspace plan, credit balances, search limits, and member counts |
| `list_grids` | List all grids with optional search & pagination, returns column definitions |
| `get_grid_details` | Get a grid's full schema — columns, settings, and data sources |
| `get_grid_curl` | Get a ready-to-use curl command and API contract for running a grid — call this first to discover required inputs |
| `run_grid` | Run a grid by providing input values, supports sync and async modes |
| `get_run_status` | Poll the status of an async or timed-out grid run by request_id |
| `rotate_api_key` | Rotate the workspace API key (irreversible, invalidates current key) |

---

## Usage Examples

> *"List all my BitScale grids"*

> *"Show me the details of the Lead Enrichment grid"*

> *"Get the curl command for the Lead Enrichment grid"*

> *"Run the Lead Enrichment grid with company_name 'Acme Corp' and website 'acme.com'"*

> *"Find phone numbers for people at Stripe using my BitScale grid"*

> *"Check the status of run 550e8400-e29b-41d4-a716-446655440000"*

---

## How Grid Runs Work

1. **Discover grids** — call `list_grids` to find available grids and their IDs.
2. **Get the API contract** — call `get_grid_curl` with the grid ID to get the exact input fields required, a shaped request body, and a copy-paste curl command. This is the recommended way to understand what a grid needs before running it.
3. **Run the grid** — call `run_grid` with the grid ID and an `inputs` map of **human-readable labels** to values (as returned by `get_grid_curl`). In sync mode (default), results return directly within 120 seconds. In async mode, you get a `request_id` to poll.
4. **Poll if needed** — if the run is still processing, call `get_run_status` with the `request_id` every 2-5 seconds until status is `completed`.

### Input Labels vs Output Column UUIDs

This is an important distinction when using `run_grid`:

- **`inputs`** — uses **human-readable labels** like `"company_name"`, `"website"`, `"email"`. These labels are derived from the source columns configured on the grid's BitScale API data source. They are **not** column UUIDs. You can find the exact labels in the BitScale app by clicking the Data Source column → BitScale API source.

  ```json
  "inputs": {
    "company_name": "Acme Corp",
    "website": "acme.com"
  }
  ```

- **`output_columns`** — uses **column UUIDs** from `get_grid_details` to filter which enriched columns appear in the response.

  ```json
  "output_columns": [
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  ]
  ```

- **Response `outputs`** — keyed by **column UUIDs**, each containing `{value, name}` where `name` is the human-readable display name.

  ```json
  "outputs": {
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8": {
      "value": "AI-powered data enrichment platform",
      "name": "Company Description"
    }
  }
  ```

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

Requests hit `https://api.bitscale.ai/api/v1`, authenticated via `X-API-KEY` header. Default rate limit: **5 req/s** per workspace.

| Endpoint | Method | Tool |
|----------|--------|------|
| `/workspace` | GET | `get_workspace_details` |
| `/grids` | GET | `list_grids` |
| `/grids/:gridId` | GET | `get_grid_details` |
| `/grids/:gridId/curl` | GET | `get_grid_curl` |
| `/grids/:gridId/run` | POST | `run_grid` |
| `/run/status/:requestId` | GET | `get_run_status` |
| `/api-key/rotate` | POST | `rotate_api_key` |

---

## API Key Rotation

Calling `rotate_api_key` immediately invalidates the current key and returns a new one. Update `BITSCALE_API_KEY` in your config and restart Claude Desktop after rotating.

---

## License

MIT
