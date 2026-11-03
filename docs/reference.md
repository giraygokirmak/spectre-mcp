<p align="center">
  <img src="../assets/headers/reference.svg" alt="Reference" />
</p>

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

## IDs Are Strings

Every ID parameter (`tweet_id`, `user_id`, `list_id`, `community_id`, `reply_to`, `quote_tweet`) is typed as a **string** in the tool schema:

```python
get_tweet("2111332908657148356")
```

X IDs are 64-bit integers (~2.1e18 for modern tweets), well past JSON's 2^53 safe-integer limit. Clients and model APIs that parse JSON numbers as IEEE-754 doubles round them silently: `2111332908657148356` becomes `2111332908657148416`, and the tool dutifully reports a perfectly good tweet as "not found or deleted". A string never round-trips through a float, so the exact ID reaches X.

Accepted forms: a numeric string (`"2111332908657148356"`), a full URL (`https://x.com/user/status/2111332908657148356`), or a plain integer (backwards compatibility). Anything else fails loudly with a validation error rather than querying the wrong tweet.

## Limitations

- **Authenticated accounts required** — X blocks unauthenticated access
- **Rate limited** — ~300 requests/hour/account (auto-rotation handles this)
- **~3200 tweet cap** on user timelines (X's own limit)
- **ToS risk** — automated access violates X's terms
- **Cookies expire** — re-add every ~2 weeks when searches return empty
