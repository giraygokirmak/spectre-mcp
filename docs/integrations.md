<h1 align="center">Integrations</h1>

Spectre works with any client that supports the [Model Context Protocol](https://modelcontextprotocol.io). The server command is always `uvx spectre-mcp`.

## Hermes Agent (Recommended)

Spectre was built for [Hermes Agent](https://github.com/NousResearch/hermes-agent). Install the MCP server and skill for best results:

1. Add the MCP server to `~/.hermes/config.yaml`:
   ```yaml
   mcp_servers:
     spectre:
       command: "uvx"
       args: ["spectre-mcp"]
       timeout: 120
   ```
2. Install the skill (Hermes discovers skills at `~/.hermes/skills/<category>/<name>/SKILL.md`):
   ```bash
   mkdir -p ~/.hermes/skills/mcp/spectre
   cp SKILL.md ~/.hermes/skills/mcp/spectre/SKILL.md
   ```
3. Reload in your Hermes session:
   ```
   /reload-mcp
   /reload-skills
   ```

The skill gives Hermes full context on all 104 tools — parameter types, safe vs. destructive tools, usage patterns, and error handling.

## Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spectre": {
      "command": "uvx",
      "args": ["spectre-mcp"]
    }
  }
}
```

Claude automatically discovers all 104 tools. No skill file needed — the tool descriptions are self-documenting.

## Cursor / Windsurf / Cline

Add to `.cursor/mcp.json` (or equivalent):

```json
{
  "mcpServers": {
    "spectre": {
      "command": "uvx",
      "args": ["spectre-mcp"]
    }
  }
}
```

## Custom Integration (Python)

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server = StdioServerParameters(command="uvx", args=["spectre-mcp"])
async with stdio_client(server) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        # Use any of the 104 tools
```

## Updating

`uvx` always pulls the latest version from PyPI automatically. For manual upgrades:

```bash
pipx upgrade spectre-mcp    # pipx
uv tool upgrade spectre-mcp  # uv
```
