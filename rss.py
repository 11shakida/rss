import os
import sys
from pytz import utc
import feedparser
from sql import db
from time import sleep, time
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from apscheduler.schedulers.background import BackgroundScheduler


if os.path.exists("config.env"):
    load_dotenv("config.env")


try:
    api_id = int(os.environ.get("API_ID"))   # Get it from my.telegram.org
    api_hash = os.environ.get("API_HASH")   # Get it from my.telegram.org
    feed_urls = list(set(i for i in os.environ.get("FEED_URLS").split("|")))  # RSS Feed URL of the site.
    bot_token = os.environ.get("BOT_TOKEN")   # Get it by creating a bot on https://t.me/botfather
    log_channel = int(os.environ.get("LOG_CHANNEL"))   # Telegram Channel ID where the bot is added and have write permission. You can use group ID too.
    check_interval = int(os.environ.get("INTERVAL", 10))   # Check Interval in seconds.  
    max_instances = int(os.environ.get("MAX_INSTANCES", 3))   # Max parallel instance to be used.
except Exception as e:
    print(e)
    print("One or more variables missing. Exiting !")
    sys.exit(1)


for feed_url in feed_urls:
    if db.get_link(feed_url) == None:
        db.update_link(feed_url, "*")


app = Client(":memory:", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def humanbytes(size):
    if not size:
        return ""
    power = 2 ** 10
    raised_to_pow = 0
    dict_power_n = {0: "", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"

def create_feed_checker(feed_url):
    def check_feed():
        FEED = feedparser.parse(feed_url)
        entry = FEED.entries[0]
        if entry.title_detail.base != db.get_link(feed_url).link:
            if "eztv.re" in entry.title_detail.base:
                msg = f"<b>Title:</b> {entry.title}\n\n"
                if entry.tags[0].term:
                    msg += f"<b>Category:</b> {entry.tags[0].term}\n"
                msg += f"<b>Torrent Site:</b> EZTV\n"
                msg += f"<b>Size:</b> {humanbytes(int(entry.links[1].length))}\n"
                if entry.torrent_seeds:
                    msg += f"<b>Seeds:</b> {entry.torrent_seeds}\n"
                if entry.torrent_peers:
                    msg += f"<b>Peers:</b> {entry.torrent_peers}\n"
                if entry.links[1].href:
                    msg += f"<b>Torrent Link:</b> {entry.links[1].href}\n\n"
                if entry.torrent_magneturi:
                    msg += f"<b>Magnet Link:</b> <code>{entry.torrent_magneturi}</code>\n\n"
                msg += f"<b>Published On:</b> {entry.published}"
            else:
                msg = f"{entry}"
            try:
                app.send_message(log_channel, msg)
                db.update_link(feed_url, entry.id)
            except FloodWait as e:
                print(f"FloodWait: {e.x} seconds")
                sleep(e.x)
            except Exception as e:
                print(e)
        else:
            print(f"Checked RSS FEED: {entry.id}")
    return check_feed


scheduler = BackgroundScheduler()
for feed_url in feed_urls:
    feed_checker = create_feed_checker(feed_url)
    scheduler.add_job(feed_checker, "interval", seconds=check_interval, max_instances=max_instances, timezone=utc)
scheduler.start()
app.run()
