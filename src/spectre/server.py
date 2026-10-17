"""Spectre — MCP server for X/Twitter automation.

The fastest X/Twitter automation for AI agents. 104 tools.
Cookie-based auth, no paid API keys, automatic account rotation.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Annotated, Optional
from fastmcp import FastMCP
from pydantic import BeforeValidator, WithJsonSchema
from loguru import logger

# Silence twscrape's noisy INFO logs (migrations, account pool internals)
logging.getLogger("twscrape").setLevel(logging.WARNING)

from spectre.scraper import Scraper
from spectre.writer import Writer

# ── Server ──

mcp = FastMCP(
    "spectre",
    instructions="The fastest X/Twitter automation for AI agents. 104 tools. Direct GraphQL/REST API calls, no browser needed. Cookie-based auth with account pool rotation. Set up accounts via: spectre add <username> \"auth_token=xxx; ct0=yyy\"",
)

# Global instances, initialized lazily
_scraper: Optional[Scraper] = None
_writer: Optional[Writer] = None


def _get_scraper() -> Scraper:
    global _scraper
    if _scraper is None:
        db = os.environ.get("SPECTRE_DB", os.path.join(os.path.expanduser("~"), ".spectre", "accounts.db"))
        proxy = os.environ.get("SPECTRE_PROXY")
        _scraper = Scraper(db_path=db, proxy=proxy)
    return _scraper


def _get_writer() -> Writer:
    global _writer
    if _writer is None:
        scraper = _get_scraper()
        proxy = os.environ.get("SPECTRE_PROXY")
        db = os.environ.get("SPECTRE_DB", os.path.join(os.path.expanduser("~"), ".spectre", "accounts.db"))
        from twscrape.accounts_pool import AccountsPool
        pool = AccountsPool(db)
        _writer = Writer(pool=pool, proxy=proxy, db_path=db)
    return _writer


def _json(obj) -> str:
    """Serialize to pretty JSON."""
    if isinstance(obj, list):
        return json.dumps([o.model_dump() if hasattr(o, "model_dump") else o for o in obj], indent=2, default=str)
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(), indent=2, default=str)
    return json.dumps(obj, indent=2, default=str)


def _id(value) -> Optional[int]:
    """Coerce an X ID to an int, accepting a string.

    X IDs are 64-bit (e.g. 2111332908657148356) and overflow the IEEE-754
    safe-integer range (2**53), so clients that parse JSON as doubles silently
    round them - the call then fails with a bogus "not found". Every ID
    parameter is therefore declared as a string on the wire and converted here.
    Accepts digits, a numeric string, or a full x.com URL. None passes through.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Invalid X ID: {value!r}")
    if isinstance(value, int):
        return value
    s = str(value).strip().rstrip("/")
    if "/" in s:
        s = s.rsplit("/", 1)[-1]
    s = s.split("?")[0].split("#")[0]
    if not s.isdigit():
        raise ValueError(
            f"Invalid X ID: {value!r} - pass the numeric ID as a string "
            "(e.g. \"2111332908657148356\"), not a URL, handle or float."
        )
    return int(s)


# ID params are exposed as strings (see _id); optional ones as string | null.
XId = Annotated[int, BeforeValidator(_id), WithJsonSchema({"type": "string"})]
OptXId = Optional[XId]


# ══════════════════════════════════════════
#  ACCOUNT POOL MANAGEMENT
# ══════════════════════════════════════════

# Note: account setup (add/remove) is done via CLI: spectre add / spectre remove
# Only runtime pool management is exposed as MCP tools.

@mcp.tool()
async def list_accounts() -> str:
    """List all accounts in the pool with their status.

    Shows username, state (active/error/locked), and any error messages.
    Use this to check which accounts are available before operations.

    Returns:
        JSON array of accounts with status details.
    """
    scraper = _get_scraper()
    accounts = await scraper.list_accounts()
    if not accounts:
        return json.dumps({"message": "No accounts in pool. Add one with: spectre add <username> \"auth_token=xxx; ct0=yyy\""})
    return json.dumps(accounts, indent=2)


@mcp.tool()
async def set_active_account(username: str) -> str:
    """Set a specific account as the primary account for all operations.

    The named account will be used first for reads and writes.
    If it gets rate-limited, the pool falls back to other active accounts.

    Args:
        username: The @handle of the account to set as primary.

    Returns:
        Confirmation or error message.
    """
    scraper = _get_scraper()
    result = await scraper.set_active_account(username)
    # Also tell the writer about the preference
    writer = _get_writer()
    writer.set_preferred_account(username)
    return result


@mcp.tool()
async def set_auto_rotate(enabled: bool) -> str:
    """Enable or disable automatic account rotation on rate limits.

    When enabled (default): if the current account hits a rate limit,
    Spectre automatically switches to the next available account.
    The agent sees a note that rotation happened.

    When disabled: only the account set via set_active_account() is used.
    Rate limits are returned as errors instead of rotating silently.
    Use this when you're managing a specific account and don't want
    operations accidentally going through a different account.

    Args:
        enabled: True to enable auto-rotation (default), False to disable.

    Returns:
        Confirmation message.
    """
    writer = _get_writer()
    writer.set_auto_rotate(enabled)
    state = "enabled" if enabled else "disabled"
    return f"Auto-rotation {state}. {'Accounts will rotate automatically on rate limits.' if enabled else 'Only the active account will be used. Rate limits will be returned as errors.'}"


@mcp.tool()
async def remove_account(username: str) -> str:
    """Remove an account from the pool.

    Args:
        username: The @handle of the account to remove.

    Returns:
        Confirmation message.
    """
    scraper = _get_scraper()
    return await scraper.remove_account(username)


@mcp.tool()
async def pool_status() -> str:
    """Check account pool health — how many accounts are active, locked, or errored.

    Returns:
        JSON with pool statistics and per-account status.
    """
    scraper = _get_scraper()
    result = await scraper.pool_status()
    return _json(result)


# ══════════════════════════════════════════
#  SEARCH
# ══════════════════════════════════════════

@mcp.tool()
async def search(query: str, limit: int = 20, mode: str = "latest") -> str:
    """Search X/Twitter for tweets matching a query.

    Args:
        query: Search query. Supports X operators like "from:username", "since:2026-01-01", "#hashtag", "filter:media", "lang:en".
        limit: Max tweets to return (default 20, max 100).
        mode: Search mode — "latest" (chronological), "top" (relevance), or "media" (photos/videos only).

    Returns:
        JSON array of matching tweets with text, author, metrics, media URLs, etc.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.search(query, limit=limit, mode=mode)
    return _json(results)


@mcp.tool()
async def search_users(query: str, limit: int = 10) -> str:
    """Search X/Twitter for users by name or keyword.

    Args:
        query: Search term (name, keyword, etc.)
        limit: Max users to return (default 10, max 50).

    Returns:
        JSON array of matching user profiles.
    """
    limit = min(limit, 50)
    scraper = _get_scraper()
    results = await scraper.search_users(query, limit=limit)
    return _json(results)


# ══════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════

@mcp.tool()
async def get_user(username: str) -> str:
    """Get a user's X/Twitter profile by @handle.

    Args:
        username: The @handle (without the @). Example: "elonmusk"

    Returns:
        User profile with bio, follower counts, verification status, etc.
    """
    scraper = _get_scraper()
    result = await scraper.get_user(username)
    if result is None:
        return json.dumps({"error": f"User @{username} not found"})
    return _json(result)


@mcp.tool()
async def get_user_tweets(username: str, limit: int = 20) -> str:
    """Get a user's recent tweets.

    Args:
        username: The @handle (without the @).
        limit: Max tweets to return (default 20, max 100).

    Returns:
        JSON array of the user's recent tweets.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_user_tweets(username, limit=limit)
    return _json(results)


@mcp.tool()
async def get_user_media(username: str, limit: int = 20) -> str:
    """Get a user's media tweets (photos, videos, GIFs).

    Args:
        username: The @handle (without the @).
        limit: Max tweets to return (default 20, max 100).

    Returns:
        JSON array of the user's media tweets with image/video URLs.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_user_media(username, limit=limit)
    return _json(results)


@mcp.tool()
async def get_followers(username: str, limit: int = 20) -> str:
    """Get a user's followers.

    Args:
        username: The @handle (without the @).
        limit: Max followers to return (default 20, max 100).

    Returns:
        JSON array of follower profiles.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_followers(username, limit=limit)
    return _json(results)


@mcp.tool()
async def get_following(username: str, limit: int = 20) -> str:
    """Get who a user follows.

    Args:
        username: The @handle (without the @).
        limit: Max users to return (default 20, max 100).

    Returns:
        JSON array of followed user profiles.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_following(username, limit=limit)
    return _json(results)


# ══════════════════════════════════════════
#  TWEETS
# ══════════════════════════════════════════

@mcp.tool()
async def get_tweet(tweet_id: XId) -> str:
    """Get a single tweet by its ID.

    Args:
        tweet_id: The tweet ID as a string (X IDs overflow JSON numbers).

    Returns:
        Full tweet details including text, author, metrics, media, etc.
    """
    scraper = _get_scraper()
    result = await scraper.get_tweet(tweet_id)
    if result is None:
        return json.dumps({"error": f"Tweet {tweet_id} not found or deleted"})
    return _json(result)


@mcp.tool()
async def get_tweet_replies(tweet_id: XId, limit: int = 20) -> str:
    """Get replies to a tweet.

    Args:
        tweet_id: The tweet ID as a string (X IDs overflow JSON numbers).
        limit: Max replies to return (default 20, max 100).

    Returns:
        JSON array of reply tweets.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_tweet_replies(tweet_id, limit=limit)
    return _json(results)


@mcp.tool()
async def get_thread(tweet_id: XId, limit: int = 50) -> str:
    """Get the full conversation thread a tweet belongs to.

    Args:
        tweet_id: Any tweet ID in the thread (the API finds the full conversation).
        limit: Max tweets in thread (default 50).

    Returns:
        JSON array of tweets in the conversation, ordered chronologically.
    """
    scraper = _get_scraper()
    results = await scraper.get_thread(tweet_id, limit=limit)
    return _json(results)


@mcp.tool()
async def get_retweeters(tweet_id: XId, limit: int = 20) -> str:
    """Get users who retweeted a tweet.

    Args:
        tweet_id: The tweet ID as a string (X IDs overflow JSON numbers).
        limit: Max users to return (default 20, max 100).

    Returns:
        JSON array of user profiles who retweeted.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_retweeters(tweet_id, limit=limit)
    return _json(results)


# ══════════════════════════════════════════
#  TRENDS & TIMELINE
# ══════════════════════════════════════════

@mcp.tool()
async def get_trends(category: str = "trending", limit: int = 20) -> str:
    """Get trending topics on X/Twitter.

    Args:
        category: Trend category — "trending", "news", "sport", or "entertainment".
        limit: Max trends to return (default 20).

    Returns:
        JSON array of trending topics with names and tweet counts.
    """
    writer = _get_writer()
    result = await writer.get_trends(category=category, limit=limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_home_timeline(limit: int = 20) -> str:
    """Get the authenticated user's home timeline feed.

    Args:
        limit: Max tweets to return (default 20, max 100).

    Returns:
        JSON array of tweets from the home feed.
    """
    limit = min(limit, 100)
    writer = _get_writer()
    result = await writer.get_home_timeline(limit=limit)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  LISTS
# ══════════════════════════════════════════

@mcp.tool()
async def get_list_timeline(list_id: XId, limit: int = 20) -> str:
    """Get tweets from an X/Twitter list.

    Args:
        list_id: The list ID as a string.
        limit: Max tweets to return (default 20, max 100).

    Returns:
        JSON array of tweets from the list.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_list_timeline(list_id, limit=limit)
    return _json(results)


@mcp.tool()
async def get_list_members(list_id: XId, limit: int = 20) -> str:
    """Get members of an X/Twitter list.

    Args:
        list_id: The list ID as a string.
        limit: Max members to return (default 20, max 100).

    Returns:
        JSON array of member profiles.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_list_members(list_id, limit=limit)
    return _json(results)


# ══════════════════════════════════════════
#  COMMUNITIES
# ══════════════════════════════════════════

@mcp.tool()
async def get_community_tweets(community_id: XId, limit: int = 20) -> str:
    """Get tweets from an X/Twitter community.

    Args:
        community_id: The community ID as a string.
        limit: Max tweets to return (default 20, max 100).

    Returns:
        JSON array of community tweets.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_community_tweets(community_id, limit=limit)
    return _json(results)


@mcp.tool()
async def get_community_info(community_id: XId) -> str:
    """Get details about an X/Twitter community.

    Args:
        community_id: The community ID as a string.

    Returns:
        Community info: name, description, member count, etc.
    """
    scraper = _get_scraper()
    result = await scraper.get_community_info(community_id)
    if result is None:
        return json.dumps({"error": f"Community {community_id} not found"})
    return _json(result)


# ══════════════════════════════════════════
#  BOOKMARKS
# ══════════════════════════════════════════

@mcp.tool()
async def get_bookmarks(limit: int = 20) -> str:
    """Get the authenticated user's bookmarked tweets.

    Args:
        limit: Max bookmarks to return (default 20, max 100).

    Returns:
        JSON array of bookmarked tweets.
    """
    limit = min(limit, 100)
    scraper = _get_scraper()
    results = await scraper.get_bookmarks(limit=limit)
    return _json(results)


# ══════════════════════════════════════════
#  WRITE OPERATIONS
# ══════════════════════════════════════════

@mcp.tool()
async def post_tweet(text: str, reply_to: OptXId = None, quote_tweet: OptXId = None, media_ids: str = "") -> str:
    """Post a new tweet on X/Twitter.

    Args:
        text: Tweet content (max 280 chars for standard, 25k for Premium).
        reply_to: Optional tweet ID to reply to, as a string.
        quote_tweet: Optional tweet ID to quote, as a string.
        media_ids: Comma-separated media IDs from upload_media (e.g. "123456,789012").

    Returns:
        JSON with posted tweet ID and URL.
    """
    ids = [int(x.strip()) for x in media_ids.split(",") if x.strip()] if media_ids else None
    writer = _get_writer()
    result = await writer.post_tweet(text, reply_to=reply_to, quote_tweet=quote_tweet, media_ids=ids)
    return json.dumps(result, indent=2)


@mcp.tool()
async def upload_media(file_path: str) -> str:
    """Upload an image or video for use in tweets.

    Uses cookie-based auth. No API keys needed.
    Supports: jpg, png, gif, webp, mp4, mov (up to 5MB images, 512MB video).

    Args:
        file_path: Absolute path to the media file.

    Returns:
        JSON with media_id — pass it to post_tweet(media_ids=...).
    """
    writer = _get_writer()
    result = await writer.upload_media(file_path)
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_tweet(tweet_id: XId) -> str:
    """Delete a tweet you posted.

    Args:
        tweet_id: The tweet ID to delete, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.delete_tweet(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def like_tweet(tweet_id: XId) -> str:
    """Like a tweet.

    Args:
        tweet_id: The tweet ID to like, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.like(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unlike_tweet(tweet_id: XId) -> str:
    """Unlike a tweet.

    Args:
        tweet_id: The tweet ID to unlike, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.unlike(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def retweet(tweet_id: XId) -> str:
    """Retweet a tweet.

    Args:
        tweet_id: The tweet ID to retweet, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.retweet(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unretweet(tweet_id: XId) -> str:
    """Undo a retweet.

    Args:
        tweet_id: The tweet ID to unretweet, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.unretweet(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def bookmark_tweet(tweet_id: XId) -> str:
    """Bookmark a tweet.

    Args:
        tweet_id: The tweet ID to bookmark, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.bookmark(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unbookmark_tweet(tweet_id: XId) -> str:
    """Remove a bookmark.

    Args:
        tweet_id: The tweet ID to unbookmark, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.unbookmark(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def follow_user(user_id: XId) -> str:
    """Follow a user on X/Twitter.

    Args:
        user_id: The user ID to follow, as a string (X IDs overflow JSON numbers). Use get_user() first to get the ID.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.follow(user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unfollow_user(user_id: XId) -> str:
    """Unfollow a user on X/Twitter.

    Args:
        user_id: The user ID to unfollow, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.unfollow(user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def mute_user(user_id: XId) -> str:
    """Mute a user on X/Twitter.

    Args:
        user_id: The user ID to mute, as a string (X IDs overflow JSON numbers). Use get_user() first to get the ID.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.mute(user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unmute_user(user_id: XId) -> str:
    """Unmute a user on X/Twitter.

    Args:
        user_id: The user ID to unmute, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.unmute(user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def block_user(user_id: XId) -> str:
    """Block a user on X/Twitter.

    Args:
        user_id: The user ID to block, as a string (X IDs overflow JSON numbers). Use get_user() first to get the ID.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.block(user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unblock_user(user_id: XId) -> str:
    """Unblock a user on X/Twitter.

    Args:
        user_id: The user ID to unblock, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.unblock(user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def send_dm(user_id: XId, text: str) -> str:
    """Send a direct message to a user.

    Args:
        user_id: The user ID to message, as a string (X IDs overflow JSON numbers). Use get_user() first to get the ID.
        text: Message content.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.send_dm(user_id, text)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_dm_inbox(limit: int = 20) -> str:
    """Get DM inbox — list recent direct message conversations.

    Args:
        limit: Max conversations to return (default 20).

    Returns:
        JSON with conversations list (conversation_id, last message, sender, time).
    """
    writer = _get_writer()
    result = await writer.get_dm_inbox(limit=limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_dm_conversation(conversation_id: str, limit: int = 50) -> str:
    """Get messages in a direct message conversation.

    Args:
        conversation_id: The conversation ID (from get_dm_inbox).
        limit: Max messages to return (default 50).

    Returns:
        JSON array of messages with text, sender, and timestamp.
    """
    writer = _get_writer()
    result = await writer.get_dm_conversation(conversation_id, limit=limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def create_list(name: str, description: str = "") -> str:
    """Create a new X/Twitter list.

    Args:
        name: List name.
        description: Optional list description.

    Returns:
        JSON with new list ID.
    """
    writer = _get_writer()
    result = await writer.create_list(name, description)
    return json.dumps(result, indent=2)


@mcp.tool()
async def update_list(list_id: XId, name: str, description: str = "") -> str:
    """Update an X/Twitter list's name/description.

    Args:
        list_id: The list ID as a string.
        name: New list name.
        description: New description.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.update_list(list_id, name, description)
    return json.dumps(result, indent=2)


@mcp.tool()
async def add_list_member(list_id: XId, user_id: XId) -> str:
    """Add a user to an X/Twitter list.

    Args:
        list_id: The list ID as a string.
        user_id: The user ID to add, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.add_list_member(list_id, user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def remove_list_member(list_id: XId, user_id: XId) -> str:
    """Remove a user from an X/Twitter list.

    Args:
        list_id: The list ID as a string.
        user_id: The user ID to remove, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.remove_list_member(list_id, user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def join_community(community_id: XId) -> str:
    """Join an X/Twitter community.

    Args:
        community_id: The community ID as a string.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.join_community(community_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def leave_community(community_id: XId) -> str:
    """Leave an X/Twitter community.

    Args:
        community_id: The community ID as a string.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.leave_community(community_id)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  SCHEDULED TWEETS
# ══════════════════════════════════════════

@mcp.tool()
async def schedule_tweet(text: str, execute_at: str, reply_to: OptXId = None) -> str:
    """Schedule a tweet for future posting.

    Args:
        text: Tweet content (max 280 chars).
        execute_at: ISO 8601 datetime (e.g. "2026-06-25T14:00:00Z").
        reply_to: Optional tweet ID to reply to, as a string.

    Returns:
        JSON with scheduling confirmation.
    """
    writer = _get_writer()
    result = await writer.schedule_tweet(text, execute_at, reply_to=reply_to)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_scheduled_tweets() -> str:
    """Get all scheduled tweets.

    Returns:
        JSON with list of scheduled tweets.
    """
    writer = _get_writer()
    result = await writer.get_scheduled_tweets()
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_scheduled_tweet(tweet_id: str) -> str:
    """Delete a scheduled tweet.

    Args:
        tweet_id: The scheduled tweet ID.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.delete_scheduled_tweet(tweet_id)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  DRAFT TWEETS
# ══════════════════════════════════════════

@mcp.tool()
async def create_draft(text: str) -> str:
    """Save a tweet draft (not published).

    Args:
        text: Draft content.

    Returns:
        JSON with draft confirmation.
    """
    writer = _get_writer()
    result = await writer.create_draft(text)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_drafts() -> str:
    """Get all draft tweets.

    Returns:
        JSON with list of drafts.
    """
    writer = _get_writer()
    result = await writer.get_drafts()
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_draft(tweet_id: str) -> str:
    """Delete a draft tweet.

    Args:
        tweet_id: The draft tweet ID.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.delete_draft(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def edit_draft(draft_id: str, text: str) -> str:
    """Edit an existing draft tweet."""
    writer = _get_writer()
    result = await writer.edit_draft(draft_id, text)
    return json.dumps(result, indent=2)


@mcp.tool()
async def edit_scheduled_tweet(scheduled_id: str, text: str, execute_at: str) -> str:
    """Edit an existing scheduled tweet."""
    writer = _get_writer()
    result = await writer.edit_scheduled_tweet(scheduled_id, text, execute_at)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  BOOKMARK FOLDERS
# ══════════════════════════════════════════

@mcp.tool()
async def get_bookmark_folders() -> str:
    """Get all bookmark folders.

    Returns:
        JSON with list of bookmark folders.
    """
    writer = _get_writer()
    result = await writer.get_bookmark_folders()
    return json.dumps(result, indent=2)


@mcp.tool()
async def create_bookmark_folder(name: str) -> str:
    """Create a bookmark folder.

    Args:
        name: Folder name.

    Returns:
        JSON with new folder ID.
    """
    writer = _get_writer()
    result = await writer.create_bookmark_folder(name)
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_bookmark_folder(folder_id: str) -> str:
    """Delete a bookmark folder.

    Args:
        folder_id: The folder ID.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.delete_bookmark_folder(folder_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def edit_bookmark_folder(folder_id: str, name: str) -> str:
    """Rename a bookmark folder.

    Args:
        folder_id: The folder ID.
        name: New folder name.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.edit_bookmark_folder(folder_id, name)
    return json.dumps(result, indent=2)


@mcp.tool()
async def add_tweet_to_folder(folder_id: str, tweet_id: XId) -> str:
    """Add a bookmarked tweet to a folder.

    Args:
        folder_id: The folder ID.
        tweet_id: The tweet ID to add.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.add_tweet_to_folder(folder_id, tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def remove_tweet_from_folder(folder_id: str, tweet_id: XId) -> str:
    """Remove a tweet from a bookmark folder.

    Args:
        folder_id: The folder ID.
        tweet_id: The tweet ID to remove.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.remove_tweet_from_folder(folder_id, tweet_id)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  LISTS (Delete)
# ══════════════════════════════════════════

@mcp.tool()
async def delete_list(list_id: XId) -> str:
    """Delete an X/Twitter list.

    Args:
        list_id: The list ID as a string.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.delete_list(list_id)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  TOPICS
# ══════════════════════════════════════════

@mcp.tool()
async def follow_topic(topic_id: str) -> str:
    """Follow a topic on X/Twitter.

    Args:
        topic_id: The topic ID (numeric string).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.follow_topic(topic_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unfollow_topic(topic_id: str) -> str:
    """Unfollow a topic on X/Twitter.

    Args:
        topic_id: The topic ID (numeric string).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.unfollow_topic(topic_id)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  COMMUNITY NOTES
# ══════════════════════════════════════════

# create_community_note removed — requires Community Notes eligibility
# (6+ month account, verified phone, enrolled in program)
# Implementation preserved in writer.py for eligible accounts.

@mcp.tool()
async def get_community_notes(tweet_id: XId) -> str:
    """Get community notes on a tweet.

    Args:
        tweet_id: The tweet ID.

    Returns:
        JSON with community notes.
    """
    writer = _get_writer()
    result = await writer.get_community_notes(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def rate_community_note(note_id: str, rating: str) -> str:
    """Rate a community note as helpful or not helpful.

    Args:
        note_id: The note ID.
        rating: "helpful" or "not_helpful".

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.rate_community_note(note_id, rating)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  ACCOUNT SETTINGS & PROFILE
# ══════════════════════════════════════════

@mcp.tool()
async def get_account_settings() -> str:
    """Get the authenticated account's settings (language, timezone, country, etc.).

    Returns:
        JSON with account settings including language, country, timezone, protected status, etc.
    """
    writer = _get_writer()
    result = await writer.get_account_settings()
    return json.dumps(result, indent=2)


@mcp.tool()
async def update_profile(name: str = "", bio: str = "", location: str = "", website: str = "") -> str:
    """⚠️ DESTRUCTIVE — Update the authenticated account's profile info.

    WARNING: This immediately changes your public profile on X. All fields are optional —
    only provide the ones you want to change. Empty strings are ignored.

    Args:
        name: New display name (max 50 chars).
        bio: New bio/description (max 160 chars).
        location: New location text.
        website: New website URL.

    Returns:
        JSON with updated profile data.
    """
    writer = _get_writer()
    result = await writer.update_profile(
        name=name or None,
        bio=bio or None,
        location=location or None,
        website=website or None,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def update_profile_image(file_path: str) -> str:
    """⚠️ DESTRUCTIVE — Change the profile avatar image.

    WARNING: This immediately replaces your current profile picture.
    Supported: jpg, png, gif (max 2MB recommended).

    Args:
        file_path: Absolute path to the image file.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.update_profile_image(file_path)
    return json.dumps(result, indent=2)


@mcp.tool()
async def update_profile_banner(file_path: str) -> str:
    """⚠️ DESTRUCTIVE — Change the profile banner/header image.

    WARNING: This immediately replaces your current banner.
    Recommended size: 1500x500px. Supported: jpg, png, gif (max 5MB).

    Args:
        file_path: Absolute path to the image file.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.update_profile_banner(file_path)
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_profile_banner() -> str:
    """⚠️ DESTRUCTIVE — Remove the profile banner/header image.

    WARNING: This immediately removes your banner image.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.delete_profile_banner()
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  MUTED & BLOCKED ACCOUNTS
# ══════════════════════════════════════════

@mcp.tool()
async def get_muted_accounts(limit: int = 50) -> str:
    """List all accounts you've muted.

    Args:
        limit: Max accounts to return (default 50).

    Returns:
        JSON array of muted user profiles.
    """
    writer = _get_writer()
    result = await writer.get_muted_accounts(limit=limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_blocked_accounts(limit: int = 50) -> str:
    """List all accounts you've blocked.

    Args:
        limit: Max accounts to return (default 50).

    Returns:
        JSON array of blocked user profiles.
    """
    writer = _get_writer()
    result = await writer.get_blocked_accounts(limit=limit)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  DM EXTENSIONS
# ══════════════════════════════════════════

@mcp.tool()
async def search_dm(query: str, limit: int = 20) -> str:
    """Search direct messages by text.

    Args:
        query: Search text to find in DMs.
        limit: Max results (default 20).

    Returns:
        JSON with matching DM messages.
    """
    writer = _get_writer()
    result = await writer.search_dm(query, limit=limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def dm_block_user(user_id: XId) -> str:
    """Block a user from sending you DMs.

    Args:
        user_id: The user ID to block in DMs, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.dm_block_user(user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def dm_unblock_user(user_id: XId) -> str:
    """Unblock a user from DMs.

    Args:
        user_id: The user ID to unblock in DMs, as a string (X IDs overflow JSON numbers).

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.dm_unblock_user(user_id)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  PIN TWEET
# ══════════════════════════════════════════

@mcp.tool()
async def pin_tweet(tweet_id: XId) -> str:
    """⚠️ DESTRUCTIVE — Pin a tweet to your profile (replaces any existing pinned tweet).

    WARNING: If you already have a pinned tweet, it will be unpinned automatically.
    Only one tweet can be pinned at a time.

    Args:
        tweet_id: The tweet ID to pin.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.pin_tweet(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unpin_tweet(tweet_id: XId) -> str:
    """Unpin a tweet from your profile.

    Args:
        tweet_id: The tweet ID to unpin.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.unpin_tweet(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def remove_follower(user_id: XId) -> str:
    """⚠️ DESTRUCTIVE — Remove a follower from your account."""
    writer = _get_writer()
    result = await writer.remove_follower(user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def pin_reply(tweet_id: XId) -> str:
    """Pin a reply to a conversation."""
    writer = _get_writer()
    result = await writer.pin_reply(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unpin_reply(tweet_id: XId) -> str:
    """Unpin a reply from a conversation."""
    writer = _get_writer()
    result = await writer.unpin_reply(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_followers_you_know(user_id: XId, limit: int = 20) -> str:
    """Get mutual followers (followers you know)."""
    writer = _get_writer()
    result = await writer.get_followers_you_know(user_id, limit)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  PROFILE HIGHLIGHTS
# ══════════════════════════════════════════

@mcp.tool()
async def create_highlight(tweet_ids: str) -> str:
    """Add tweets to your profile highlights section.

    Args:
        tweet_ids: Comma-separated tweet IDs (e.g. "123456,789012").

    Returns:
        Confirmation JSON with the added tweet IDs.
    """
    ids = [int(x.strip()) for x in tweet_ids.split(",") if x.strip()]
    writer = _get_writer()
    result = await writer.create_highlight(ids)
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_highlight(highlight_id: str) -> str:
    """Remove a highlight from your profile.

    Args:
        highlight_id: The highlight ID.

    Returns:
        Confirmation JSON.
    """
    writer = _get_writer()
    result = await writer.delete_highlight(highlight_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_user_highlights(user_id: XId, limit: int = 20) -> str:
    """Get a user's profile highlight tweets.

    Args:
        user_id: The user ID as a string (X IDs overflow JSON numbers).
        limit: Max tweets to return (default 20).

    Returns:
        JSON array of highlighted tweets.
    """
    writer = _get_writer()
    result = await writer.get_user_highlights(user_id, limit=limit)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  VERIFIED FOLLOWERS & USER LIKES
# ══════════════════════════════════════════

@mcp.tool()
async def get_verified_followers(user_id: XId, limit: int = 20) -> str:
    """Get Blue-verified followers of a user.

    Args:
        user_id: The user ID as a string (X IDs overflow JSON numbers).
        limit: Max followers to return (default 20).

    Returns:
        JSON array of verified follower profiles.
    """
    writer = _get_writer()
    result = await writer.get_verified_followers(user_id, limit=limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_user_likes(user_id: XId, limit: int = 20) -> str:
    """Get a user's liked tweets.

    Args:
        user_id: The user ID as a string (X IDs overflow JSON numbers).
        limit: Max tweets to return (default 20, max 100).

    Returns:
        JSON array of liked tweets.
    """
    limit = min(limit, 100)
    writer = _get_writer()
    result = await writer.get_user_likes(user_id, limit=limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_bookmark_folder_timeline(folder_id: str, limit: int = 20) -> str:
    """Get tweets inside a specific bookmark folder.

    Args:
        folder_id: The bookmark folder ID.
        limit: Max tweets to return (default 20).

    Returns:
        JSON array of tweets in the folder.
    """
    writer = _get_writer()
    result = await writer.get_bookmark_folder_timeline(folder_id, limit=limit)
    return json.dumps(result, indent=2)


# ══════════════════════════════════════════
#  NEW TOOLS (v1.1.4)
# ══════════════════════════════════════════

@mcp.tool()
async def search_dm_groups(query: str, limit: int = 20) -> str:
    """Search DMs in group conversations."""
    writer = _get_writer()
    result = await writer.search_dm_groups(query, limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_dm_muted(limit: int = 20) -> str:
    """Get muted DM conversations."""
    writer = _get_writer()
    result = await writer.get_dm_muted(limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def search_dm_people(query: str, limit: int = 20) -> str:
    """Search for people in DMs."""
    writer = _get_writer()
    result = await writer.search_dm_people(query, limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_favoriters(tweet_id: XId, limit: int = 20) -> str:
    """Get users who liked a tweet."""
    writer = _get_writer()
    result = await writer.get_favoriters(tweet_id, limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_tweet_edit_history(tweet_id: XId) -> str:
    """Get edit history of a tweet."""
    writer = _get_writer()
    result = await writer.get_tweet_edit_history(tweet_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_similar_posts(tweet_id: XId, limit: int = 20) -> str:
    """Get similar/related posts to a tweet."""
    writer = _get_writer()
    result = await writer.get_similar_posts(tweet_id, limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def clear_all_bookmarks() -> str:
    """⚠️ DESTRUCTIVE — Delete ALL bookmarks. Cannot be undone."""
    writer = _get_writer()
    result = await writer.clear_all_bookmarks()
    return json.dumps(result, indent=2)


@mcp.tool()
async def search_bookmarks(query: str, limit: int = 20) -> str:
    """Search bookmarks by text."""
    writer = _get_writer()
    result = await writer.search_bookmarks(query, limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def subscribe_list(list_id: XId) -> str:
    """Subscribe to a list."""
    writer = _get_writer()
    result = await writer.subscribe_list(list_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def unsubscribe_list(list_id: XId) -> str:
    """Unsubscribe from a list."""
    writer = _get_writer()
    result = await writer.unsubscribe_list(list_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_list_memberships(user_id: XId, limit: int = 20) -> str:
    """Get lists a user is a member of."""
    writer = _get_writer()
    result = await writer.get_list_memberships(user_id, limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_list_ownerships(user_id: XId, limit: int = 20) -> str:
    """Get lists owned by a user."""
    writer = _get_writer()
    result = await writer.get_list_ownerships(user_id, limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_list_subscribers(list_id: XId, limit: int = 20) -> str:
    """Get subscribers of a list."""
    writer = _get_writer()
    result = await writer.get_list_subscribers(list_id, limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_topic_info(topic_id: str) -> str:
    """Get topic details by ID."""
    writer = _get_writer()
    result = await writer.get_topic_info(topic_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_notifications(limit: int = 20) -> str:
    """Get notifications timeline."""
    writer = _get_writer()
    result = await writer.get_notifications(limit)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_user_tweets_and_replies(username: str, limit: int = 20) -> str:
    """Get a user's tweets and replies."""
    writer = _get_writer()
    result = await writer.get_user_tweets_and_replies(username, limit)
    return json.dumps(result, indent=2)


# ── Entry point ──

def main():
    """Run the Spectre MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
