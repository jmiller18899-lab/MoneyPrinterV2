import re
import sys
import json
import os

import tweepy
from termcolor import colored
from typing import List, Optional
from datetime import datetime

from cache import *
from config import *
from status import *
from llm_provider import generate_text


class Twitter:
    """
    Class for the Bot, that grows a Twitter account via the X/Twitter API v2.
    """

    def __init__(
        self,
        account_uuid: str,
        account_nickname: str,
        topic: str,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
    ) -> None:
        self.account_uuid: str = account_uuid
        self.account_nickname: str = account_nickname
        self.topic: str = topic

        if not all([api_key, api_secret, access_token, access_token_secret]):
            raise ValueError(
                "Twitter API credentials are required. "
                "Set api_key, api_secret, access_token, and access_token_secret on the account."
            )

        self._client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

    def post(self, text: Optional[str] = None) -> None:
        post_content: str = text if text is not None else self.generate_post()
        now: datetime = datetime.now()

        print(colored(" => Posting to Twitter:", "blue"), post_content[:30] + "...")

        self._client.create_tweet(text=post_content)

        self.add_post({"content": post_content, "date": now.strftime("%m/%d/%Y, %H:%M:%S")})
        success("Posted to Twitter successfully!")

    def get_posts(self) -> List[dict]:
        if not os.path.exists(get_twitter_cache_path()):
            with open(get_twitter_cache_path(), "w") as file:
                json.dump({"accounts": []}, file, indent=4)

        with open(get_twitter_cache_path(), "r") as file:
            parsed = json.load(file)
            for account in parsed["accounts"]:
                if account["id"] == self.account_uuid:
                    return account.get("posts") or []

        return []

    def add_post(self, post: dict) -> None:
        posts = self.get_posts()
        posts.append(post)

        with open(get_twitter_cache_path(), "r") as file:
            previous_json = json.loads(file.read())
            for account in previous_json["accounts"]:
                if account["id"] == self.account_uuid:
                    account["posts"].append(post)

            with open(get_twitter_cache_path(), "w") as f:
                f.write(json.dumps(previous_json))

    def generate_post(self) -> str:
        if get_verbose():
            info("Generating a post...")

        completion = generate_text(
            f"Generate a Twitter post about: {self.topic} in {get_twitter_language()}. "
            "The Limit is 2 sentences. Choose a specific sub-topic of the provided topic."
        )

        if completion is None:
            error("Failed to generate a post. Please try again.")
            sys.exit(1)

        completion = re.sub(r"\*", "", completion).replace('"', "")

        if get_verbose():
            info(f"Length of post: {len(completion)}")
        if len(completion) >= 260:
            return completion[:257].rsplit(" ", 1)[0] + "..."

        return completion
