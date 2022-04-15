import tweepy
import time
import requests
import logging
import mimetypes

from sys import stdout
from pymongo import MongoClient
from json import JSONDecodeError

from .env import (
    CONSUMER_KEY, CONSUMER_SECRET,
    ACCESS_KEY, ACCESS_SECRET, CHECK_DELAY,
    CAPY_LIFE_LINK, CAPY_API_LINK,
    MONGO_HOST, MONGO_PORT, MONGO_DB
)

logger = logging.getLogger("flappycapy")
logger.setLevel(logging.DEBUG)
consoleHandler = logging.StreamHandler(stdout)
logger.addHandler(consoleHandler)
mongo = MongoClient(
    host=MONGO_HOST, port=MONGO_PORT
)
collection = mongo[MONGO_DB]

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
twitter = tweepy.API(auth)


def main():
    while True:
        logger.info(f"Waiting {CHECK_DELAY} seconds till next check.")
        time.sleep(CHECK_DELAY)

        with requests.get(CAPY_API_LINK) as resp:
            if resp.status_code != 200:
                logger.warn((
                    f"HTTP Request to \"{CAPY_API_LINK}\""
                    f" gave status code {resp.status_code}"
                ))
                continue

            try:
                json = resp.json()
            except JSONDecodeError as error:
                logger.warn(error)
                continue

            record = collection.used.find_one({
                "_id": json["_id"]
            })
            if record:
                continue

            with requests.get(json["image"]) as img_resp:
                if resp.status_code != 200:
                    logger.warn((
                        f"HTTP Request to \"{json['image']}\""
                        f" gave status code {resp.status_code}"
                    ))
                    continue

                file_ext = mimetypes.guess_extension(
                    img_resp.headers["Content-Type"]
                )
                if file_ext is None:
                    logger.warn("Unable to guess mime type.")
                    continue

                media = twitter.simple_upload(
                    filename="capy" + file_ext, file=img_resp.content
                )
                twitter.update_status(
                    (f"Meet {json['name']}!\n"
                     f"Submit a Capybara at {CAPY_LIFE_LINK}"),
                    media_ids=[media.media_id]
                )

                try:
                    pass
                except Exception as error:
                    logger.warn((
                        "Unable to tweet capybara due to follow error:\n" +
                        str(error)
                    ))
                    continue

                collection.used.insert_one({
                    "_id": json["_id"]
                })

                logger.info(
                    f"Capybara named {json['name']} has been tweeted."
                )
