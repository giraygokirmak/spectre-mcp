<h1 align="center">Tools</h1>

All 104 tools, grouped by feature. Tools marked `—` are destructive — see the [Safety Guide](../README.md#safety-guide).

### Account Pool (5)

Manage multiple X accounts with automatic rotation on rate limits.

| Tool | Description |
|------|-------------|
| `list_accounts()` | List all accounts with status |
| `pool_status()` | Pool health stats |
| `set_active_account(username)` | Set primary account |
| `set_auto_rotate(enabled)` | Enable/disable auto-rotation |
| `remove_account(username)` | — remove account from pool |

### Search (2)

| Tool | Description |
|------|-------------|
| `search(query, limit, mode)` | Search tweets. Supports `from:username`, `since:2026-01-01`, `#hashtag`, `filter:media` |
| `search_users(query, limit)` | Search users by name/keyword |

### Users (12)

| Tool | Description |
|------|-------------|
| `get_user(username)` | User profile by @handle |
| `get_user_tweets(username, limit)` | User's recent tweets |
| `get_user_tweets_and_replies(username, limit)` | User's tweets and replies |
| `get_user_media(username, limit)` | User's photos/videos/GIFs |
| `get_followers(username, limit)` | User's followers |
| `get_following(username, limit)` | Who a user follows |
| `get_user_likes(user_id, limit)` | A user's liked tweets |
| `get_user_highlights(user_id, limit)` | User's highlighted tweets |
| `get_verified_followers(user_id, limit)` | Blue-verified followers |
| `get_followers_you_know(user_id, limit)` | Mutual followers |
| `get_list_memberships(user_id, limit)` | Lists a user is a member of |
| `get_list_ownerships(user_id, limit)` | Lists owned by a user |

### Tweets (8)

| Tool | Description |
|------|-------------|
| `get_tweet(tweet_id)` | Single tweet by ID |
| `get_tweet_replies(tweet_id, limit)` | Replies to a tweet |
| `get_thread(tweet_id, limit)` | Full conversation thread |
| `get_retweeters(tweet_id, limit)` | Users who retweeted |
| `get_favoriters(tweet_id, limit)` | Users who liked a tweet |
| `get_tweet_edit_history(tweet_id)` | Edit history of a tweet |
| `get_similar_posts(tweet_id, limit)` | Similar/related posts |
| `get_community_notes(tweet_id)` | Community notes on a tweet |

### Timeline & Notifications (3)

| Tool | Description |
|------|-------------|
| `get_trends(category, limit)` | Trending topics (trending, news, sport, entertainment) |
| `get_home_timeline(limit)` | Home feed |
| `get_notifications(limit)` | Notifications timeline |

### Post & Media (3)

| Tool | Description |
|------|-------------|
| `post_tweet(text, reply_to?, quote_tweet?, media_ids?)` | Post a tweet with optional media |
| `upload_media(file_path)` | Upload image or video (jpg, png, gif, mp4, mov) — no API keys |
| `delete_tweet(tweet_id)` | — delete a tweet |

### Engagement (6)

| Tool | Description |
|------|-------------|
| `like_tweet(tweet_id)` | Like a tweet |
| `unlike_tweet(tweet_id)` | Unlike a tweet |
| `retweet(tweet_id)` | Retweet |
| `unretweet(tweet_id)` | Undo retweet |
| `bookmark_tweet(tweet_id)` | Bookmark a tweet |
| `unbookmark_tweet(tweet_id)` | Remove bookmark |

### Social (6)

| Tool | Description |
|------|-------------|
| `follow_user(user_id)` | — follow a user |
| `unfollow_user(user_id)` | — unfollow a user |
| `mute_user(user_id)` | Mute a user |
| `unmute_user(user_id)` | Unmute a user |
| `block_user(user_id)` | — block a user |
| `unblock_user(user_id)` | — unblock a user |

### Social Extended (3)

| Tool | Description |
|------|-------------|
| `remove_follower(user_id)` | — remove a follower |
| `pin_reply(tweet_id)` | Pin a reply to a conversation |
| `unpin_reply(tweet_id)` | Unpin a reply |

### DMs (9)

| Tool | Description |
|------|-------------|
| `send_dm(user_id, text)` | — send a direct message |
| `get_dm_inbox(limit)` | Recent DM conversations |
| `get_dm_conversation(conversation_id, limit)` | Messages in a conversation |
| `search_dm(query, limit)` | Search all DMs by text |
| `search_dm_groups(query, limit)` | Search DMs in group conversations |
| `search_dm_people(query, limit)` | Search for people in DMs |
| `get_dm_muted(limit)` | Muted DM conversations |
| `dm_block_user(user_id)` | Block a user in DMs |
| `dm_unblock_user(user_id)` | Unblock a user in DMs |

### Lists (10)

Full lifecycle: create → manage members → subscribe → delete.

| Tool | Description |
|------|-------------|
| `create_list(name, description?)` | Create a new list |
| `update_list(list_id, name, description?)` | Update list name/description |
| `delete_list(list_id)` | — delete a list |
| `add_list_member(list_id, user_id)` | Add user to list |
| `remove_list_member(list_id, user_id)` | Remove user from list |
| `get_list_timeline(list_id, limit)` | Tweets from a list |
| `get_list_members(list_id, limit)` | Members of a list |
| `get_list_subscribers(list_id, limit)` | List subscribers |
| `subscribe_list(list_id)` | Subscribe to a list |
| `unsubscribe_list(list_id)` | Unsubscribe from a list |

### Bookmark Folders (8)

| Tool | Description |
|------|-------------|
| `get_bookmark_folders()` | List all bookmark folders |
| `create_bookmark_folder(name)` | Create a folder |
| `edit_bookmark_folder(folder_id, name)` | Rename a folder |
| `delete_bookmark_folder(folder_id)` | — delete a folder |
| `add_tweet_to_folder(folder_id, tweet_id)` | Add tweet to folder |
| `remove_tweet_from_folder(folder_id, tweet_id)` | Remove tweet from folder |
| `get_bookmark_folder_timeline(folder_id, limit)` | Tweets in a folder |
| `search_bookmarks(query, limit)` | Search bookmarks by text |

### Bookmarks (2)

| Tool | Description |
|------|-------------|
| `get_bookmarks(limit)` | Your bookmarked tweets |
| `clear_all_bookmarks()` | — delete ALL bookmarks |

### Scheduled Tweets (4)

| Tool | Description |
|------|-------------|
| `schedule_tweet(text, execute_at, reply_to?)` | Schedule for future posting (ISO 8601 datetime) |
| `get_scheduled_tweets()` | List all scheduled tweets |
| `edit_scheduled_tweet(id, text, execute_at)` | Edit a scheduled tweet |
| `delete_scheduled_tweet(tweet_id)` | — delete a scheduled tweet |

### Draft Tweets (4)

| Tool | Description |
|------|-------------|
| `create_draft(text)` | Save a tweet draft |
| `get_drafts()` | List all drafts |
| `edit_draft(draft_id, text)` | Edit a draft |
| `delete_draft(tweet_id)` | — delete a draft |

### Communities (4)

| Tool | Description |
|------|-------------|
| `get_community_info(community_id)` | Community details |
| `get_community_tweets(community_id, limit)` | Community feed |
| `join_community(community_id)` | Join a community |
| `leave_community(community_id)` | — leave a community |

### Topics (3)

| Tool | Description |
|------|-------------|
| `get_topic_info(topic_id)` | Get topic details |
| `follow_topic(topic_id)` | Follow a topic |
| `unfollow_topic(topic_id)` | Unfollow a topic |

### Community Notes (2)

| Tool | Description |
|------|-------------|
| `get_community_notes(tweet_id)` | Get community notes on a tweet |
| `rate_community_note(note_id, rating)` | Rate a note as helpful / not_helpful |

> **Note:** Community Notes *creation* requires an eligible account (6+ months old, verified phone, enrolled in the program). Reading and rating notes works for all accounts.

### Account Settings & Profile (5)

| Tool | Description |
|------|-------------|
| `get_account_settings()` | View account settings |
| `update_profile(name?, bio?, location?, website?)` | — update profile info |
| `update_profile_image(file_path)` | — change avatar image |
| `update_profile_banner(file_path)` | — change banner image |
| `delete_profile_banner()` | — remove banner |

### Pin & Highlights (5)

| Tool | Description |
|------|-------------|
| `pin_tweet(tweet_id)` | — pin tweet to profile (replaces existing) |
| `unpin_tweet(tweet_id)` | Unpin tweet |
| `create_highlight(tweet_ids)` | — add tweets to profile highlights |
| `delete_highlight(highlight_id)` | — remove a highlight |
| `get_user_highlights(user_id, limit)` | Get user's highlighted tweets |

### Safety & Privacy (4)

| Tool | Description |
|------|-------------|
| `get_muted_accounts(limit)` | List all muted accounts |
| `get_blocked_accounts(limit)` | List all blocked accounts |
| `get_verified_followers(user_id, limit)` | Blue-verified followers |
| `get_user_likes(user_id, limit)` | A user's liked tweets |
