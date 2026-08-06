<p align="center">
  <img src="../assets/headers/safety.svg" alt="Safety" />
</p>

Spectre marks every destructive tool in the [tools reference](tools.md) with a `—`. Agents should respect these warnings.

## Always Confirm Before Calling

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

## Safe to Use Freely (Read-Only)

All `get_*`, `search_*`, `list_*` tools. `pool_status`, `get_muted_accounts`, `get_blocked_accounts`, `get_scheduled_tweets`, `get_drafts`, `get_bookmarks`, `get_trends`, `get_home_timeline`, `get_notifications`.

## Rate Limits

- ~300 requests/hour/account
- Spectre auto-rotates to the next account on rate limits
- Use `set_auto_rotate(false)` to lock to a single account
- Rate limit errors include `retry_after_seconds`
