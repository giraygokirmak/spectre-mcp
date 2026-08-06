<h1 align="center">Reference</h1>

## X Query Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `from:username` | `from:elonmusk` | Tweets by a user |
| `since:YYYY-MM-DD` | `since:2026-01-01` | After date |
| `until:YYYY-MM-DD` | `until:2026-06-01` | Before date |
| `#hashtag` | `#python` | Hashtag search |
| `filter:media` | `AI filter:media` | Only media tweets |
| `filter:links` | `AI filter:links` | Only tweets with links |
| `lang:en` | `AI lang:en` | Language filter |
| `min_retweets:N` | `AI min_retweets:100` | Minimum retweets |
| `min_faves:N` | `AI min_faves:50` | Minimum likes |
| `-"term"` | `AI -"GPT"` | Exclude term |
| `OR` | `python OR rust` | Either term |

## CLI

```bash
spectre add <username> <cookies>     Add account via browser cookies
spectre remove <username>            Remove an account
spectre list                         List all accounts
spectre status                       Pool health check
spectre serve                        Start MCP server (default)
spectre help                         Show help
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SPECTRE_DB` | `~/.spectre/accounts.db` | Account pool database path |
| `SPECTRE_PROXY` | none | Global proxy (`socks5://user:pass@host:port`) |
| `TWS_HTTP_BACKEND` | `httpx` | Set to `curl_cffi` for TLS fingerprinting |
| `TWS_TELEMETRY` | `0` | Disable telemetry |
| `SPECTRE_OP_*` | built-in | Override GraphQL operation IDs (when they rotate) |

## Limitations

- **Authenticated accounts required** — X blocks unauthenticated access
- **Rate limited** — ~300 requests/hour/account (auto-rotation handles this)
- **~3200 tweet cap** on user timelines (X's own limit)
- **ToS risk** — automated access violates X's terms
- **Cookies expire** — re-add every ~2 weeks when searches return empty
