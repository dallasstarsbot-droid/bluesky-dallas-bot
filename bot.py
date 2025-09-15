# bot.py  — simple, reliable crossposter (text + image URLs; videos linked)
import os, json, logging
from datetime import datetime
import requests
import snscrape.modules.twitter as sntwitter
from atproto import Client

logging.basicConfig(level=logging.INFO)
TWITTER_USER = "DallasStars"
STATE_FILE = "last_posted.json"

BSKY_HANDLE = os.getenv("BSKY_HANDLE")            # e.g. "yourname.bsky.social"
BSKY_APP_PASSWORD = os.getenv("BSKY_APP_PASSWORD")# app password you generated

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {"last_id": None}

def save_state(state):
    json.dump(state, open(STATE_FILE, "w"))

def get_latest_tweet(username):
    scraper = sntwitter.TwitterUserScraper(username)
    try:
        return next(scraper.get_items())
    except StopIteration:
        return None

def make_post_text(tweet):
    text = tweet.content or ""
    # Attach image URLs inline (reliable)
    if getattr(tweet, "media", None):
        for m in tweet.media:
            # snscrape media objects vary slightly — try common attributes
            url = getattr(m, "fullUrl", None) or getattr(m, "url", None)
            if url:
                text += f"\n\nImage: {url}"
    # If tweet has video/gif, add a link to the original X post
    if getattr(tweet, "video", None) or any(getattr(m, "type", "").lower() in ("video", "animated_gif", "gif") for m in (getattr(tweet, "media", []) or [])):
        tweet_url = f"https://x.com/{TWITTER_USER}/status/{tweet.id}"
        text += f"\n\n🎥 Original video: {tweet_url}"
    return text

def main():
    if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
        logging.error("Set BSKY_HANDLE and BSKY_APP_PASSWORD environment variables.")
        return

    client = Client()
    client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
    logging.info("Logged into Bluesky")

    state = load_state()
    latest = get_latest_tweet(TWITTER_USER)
    if not latest:
        logging.info("No tweets found.")
        return

    latest_id = str(latest.id)
    if state.get("last_id") == latest_id:
        logging.info("No new tweet since last run.")
        return

    post_text = make_post_text(latest)
    # Post text to Bluesky (text-only). This is simple and usually works.
    client.send_post(text=post_text)
    logging.info("Posted to Bluesky: %s", post_text[:120])

    # Save state
    state["last_id"] = latest_id
    save_state(state)
    logging.info("Saved state (last_id=%s)", latest_id)

if __name__ == "__main__":
    main()
