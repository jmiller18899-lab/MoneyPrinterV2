import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from status import *
from config import *
from llm_provider import generate_text
from .Twitter import Twitter

_SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class AffiliateMarketing:
    """
    Handles affiliate marketing: scrapes Amazon product info via HTTP,
    generates an LLM pitch, and posts it to Twitter via the API.
    """

    def __init__(
        self,
        affiliate_link: str,
        fp_profile_path: str,
        twitter_account_uuid: str,
        account_nickname: str,
        topic: str,
    ) -> None:
        parsed_link = urlparse(affiliate_link)
        if parsed_link.scheme not in ["http", "https"] or not parsed_link.netloc:
            raise ValueError(
                f"Affiliate link is invalid. Expected a full URL, got: {affiliate_link}"
            )

        self.affiliate_link: str = affiliate_link
        self.fp_profile_path: str = fp_profile_path
        self.account_uuid: str = twitter_account_uuid
        self.account_nickname: str = account_nickname
        self.topic: str = topic

        self.scrape_product_information()

    def scrape_product_information(self) -> None:
        response = requests.get(self.affiliate_link, headers=_SCRAPE_HEADERS, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        title_el = soup.find(id="productTitle")
        self.product_title: str = title_el.get_text(strip=True) if title_el else "Unknown Product"

        bullets_el = soup.find(id="feature-bullets")
        if bullets_el:
            items = bullets_el.find_all("span", class_="a-list-item")
            self.features: str = " | ".join(
                i.get_text(strip=True) for i in items if i.get_text(strip=True)
            )
        else:
            self.features = ""

        if get_verbose():
            info(f"Product Title: {self.product_title}")
            info(f"Features: {self.features[:120]}…")

    def generate_pitch(self) -> str:
        self.pitch: str = (
            generate_text(
                f'I want to promote this product on my website. Generate a brief pitch about this '
                f'product, return nothing else except the pitch. Information:\n'
                f'Title: "{self.product_title}"\nFeatures: "{self.features}"'
            )
            + "\nYou can buy the product here: "
            + self.affiliate_link
        )
        return self.pitch

    def share_pitch(self, where: str) -> None:
        if where == "twitter":
            twitter = Twitter(
                self.account_uuid,
                self.account_nickname,
                self.fp_profile_path,
                self.topic,
            )
            twitter.post(self.pitch)
