<p align="center">
  <img src="assets/spectre-logo.png" width="180" alt="Spectre" />
</p>

<h1 align="center">Spectre MCP</h1>

<p align="center">
  <em>The fastest X/Twitter automation for AI agents.</em>
</p>

<p align="center">
  104 tools · no browser · no API keys · no monthly fees
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> · <a href="docs/tools.md">Tools</a> · <a href="#why-spectre">Why Spectre?</a> · <a href="#safety-guide">Safety</a> · <a href="docs/integrations.md">Integrations</a> · <a href="docs/reference.md">Reference</a>
</p>

---

<p align="center">
  <img src="assets/headers/why.svg" alt="Why Spectre?" />
</p>

Spectre is an MCP server that gives AI agents 104 tools for X/Twitter automation — from search and posting to DMs, lists, and communities. Under the hood, it talks directly to X's internal GraphQL and REST APIs. No browser to spin up, no Puppeteer to maintain, no DOM scraping that breaks on UI changes.

| | **Spectre** | **XActions** | **twikit** |
|--|:-:|:-:|:-:|
| **Architecture** | Direct GraphQL/REST | Puppeteer (headless browser) | Python API wrapper |
| **Speed** | <1s per request | 3–10s (browser startup) | ~1s per request |
| **Memory** | ~10 MB | ~200 MB+ (Chromium) | ~10 MB |
| **MCP Server** | ✓ 104 tools | ~50 API tools | ✗ None |
| **Account Pool** | ✓ Multi-account auto-rotation | ✗ Single auth_token | ✗ Single session |
| **Browser Required** | ✗ Never | ✓ Always | ✗ Never |
| **DOM Breakage Risk** | ✗ None | ~ breaks on UI changes | ✗ None |
| **Media Upload** | ✓ Cookie-based (no API keys) | ~ requires API keys | ✗ |
| **Lists** | ✓ Full CRUD + members + subscribe | ✗ | ✗ |
| **Drafts & Scheduled** | ✓ Full CRUD | ~ Basic | ✗ |
| **Bookmark Folders** | ✓ Full CRUD + timeline | ✗ | ✗ |
| **DM Search** | ✓ All / groups / people | ✗ | ✗ |
| **Community Notes** | ✓ Read + rate | ✗ | ✗ |
| **Highlights** | ✓ Create, delete, get | ✗ | ✗ |
| **Notifications** | ✓ Full timeline | ✗ | ✗ |
| **Language** | Python | JavaScript | Python |

---

<p align="center">
  <img src="assets/headers/quickstart.svg" alt="Quick Start" />
</p>

### 1. Install

```bash
pipx install spectre-mcp    # or: uv tool install spectre-mcp
```

### 2. Add Your X Account

Extract cookies from your browser:

1. Open **x.com** and make sure you're logged in
2. Open **DevTools** (`F12` or `Ctrl+Shift+I`)
3. Go to **Storage** → **Cookies** → select **`https://x.com`**
4. Find and copy these two values:
   - **`auth_token`** — long hex string (e.g. `a1b2c3d4...`)
   - **`ct0`** — 160-character hex string

```bash
spectre add myaccount "auth_token=a1b2c3d4...; ct0=e5f6a7b8..."
```

> **Tip:** `ct0` is exactly 160 hex characters. Double-check you copied the full value — partial cookies will fail silently.

### 3. Configure Your MCP Client

Add to your MCP client config (`~/.hermes/config.yaml`, `claude_desktop_config.json`, `.cursor/mcp.json`, or equivalent):

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

For client-specific setup (Hermes skill, Claude, Cursor, Python), see [Integrations](docs/integrations.md).

> **No `uv`?** Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`
> Or use `python3 -m spectre.server` to run from a local clone.

---

<p align="center">
  <img src="assets/headers/safety.svg" alt="Safety Guide" />
</p>

Spectre marks every destructive tool in the [tools reference](docs/tools.md) with a `—`. Agents should respect these warnings.

### Always Confirm Before Calling

| Tool | Why |
|------|-----|
| `post_tweet` | Public, live immediately |
| `delete_tweet` | Permanent |
| `pin_tweet` | Replaces existing pin silently |
| `update_profile*` | Changes your public profile |
| `follow_user` / `unfollow_user` | Visible to the other user |
| `block_user` | Blocked user loses access to your content |
| `send_dm` | Sent immediately, no recall |
| `create_highlight` | Adds to your public profile |

### Safe to Use Freely (Read-Only)

All `get_*`, `search_*`, `list_*` tools. `pool_status`, `get_muted_accounts`, `get_blocked_accounts`, `get_scheduled_tweets`, `get_drafts`, `get_bookmarks`, `get_trends`, `get_home_timeline`, `get_notifications`.

### Rate Limits

- ~300 requests/hour/account
- Spectre auto-rotates to the next account on rate limits
- Use `set_auto_rotate(false)` to lock to a single account
- Rate limit errors include `retry_after_seconds`

---

<p align="center">
  <img src="assets/headers/reference.svg" alt="Reference" />
</p>

- [All 104 Tools](docs/tools.md) — every tool, grouped by feature
- [Integrations](docs/integrations.md) — Hermes, Claude, Cursor, Python
- [Reference](docs/reference.md) — X query operators, CLI, env vars, limitations

---

## License

MIT
