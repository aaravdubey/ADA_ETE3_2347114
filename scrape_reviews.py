import asyncio
import json
import math
import csv
from typing import List, Dict, Optional
from httpx import AsyncClient, Response
from parsel import Selector
from loguru import logger as log
import re
import os

client = AsyncClient(
    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    },
    follow_redirects=True,
)


def parse_hotel_page(result: Response) -> Dict:
    """parse hotel data from hotel pages"""
    selector = Selector(result.text)
    basic_data = json.loads(
        selector.xpath("//script[contains(text(),'aggregateRating')]/text()").get()
    )
    description = selector.css("div.fIrGe._T::text").get()
    amenities = []
    for feature in selector.xpath(
        "//div[contains(@data-test-target, 'amenity')]/text()"
    ):
        amenities.append(feature.get())
    reviews = []
    for review in selector.xpath("//div[@data-reviewid]"):
        title = review.xpath(
            ".//div[@data-test-target='review-title']/a/span/span/text()"
        ).get()
        text = review.xpath(
            ".//div[@class='_T FKffI bmUTE']/div[@class='fIrGe _T']/span[@class='orRIx Ci _a C ']"
        ).get()
        text = re.sub(r'<[^>]+>', '', text).strip()
        rate = review.xpath(
            ".//div[@data-test-target='review-rating']/svg/title/text()"
        ).get()
        rate = (
            rate.split(".")[0]
            if rate
            else None
        )
        trip_data = review.xpath(
            ".//span[span[contains(text(),'Date of stay')]]/text()"
        ).get().strip()
        reviews.append(
            {"title": title, "text": text, "rate": rate, "tripDate": trip_data}
        )

    return {
        "basic_data": basic_data,
        "description": description,
        "featues": amenities,
        "reviews": reviews,
    }


async def scrape_hotel_reviews(url: str, max_review_pages: Optional[int] = None) -> Dict:
    """Scrape hotel data and reviews"""
    first_page = await client.get(url)
    assert first_page.status_code == 200, "request is blocked"
    hotel_data = parse_hotel_page(first_page)

    # get the number of total review pages
    _review_page_size = 10
    total_reviews = int(hotel_data["basic_data"]["aggregateRating"]["reviewCount"])
    total_review_pages = math.ceil(total_reviews / _review_page_size)

    # get the number of review pages to scrape
    if max_review_pages and max_review_pages < total_review_pages:
        total_review_pages = max_review_pages

    # scrape all review pages concurrently
    review_urls = [
        # note: "or" stands for "offset reviews"
        url.replace("-Reviews-", f"-Reviews-or{_review_page_size * i}-")
        for i in range(1, total_review_pages)
    ]

    # fetch all review pages concurrently
    tasks = [client.get(review_url) for review_url in review_urls]
    responses = await asyncio.gather(*tasks)

    for response in responses:
        data = parse_hotel_page(response)
        hotel_data["reviews"].extend(data["reviews"])

    # print(f"scraped {len(hotel_data['reviews'])} reviews from {url}")
    log.info(f"scraped {len(hotel_data['reviews'])} reviews from {url}")
    return hotel_data


def save_to_csv(hotel_data: Dict, url: str) -> str:
    """Save hotel data to a CSV file in the 'datasets' folder."""
    
    # Ensure the 'datasets' directory exists
    if not os.path.exists('datasets'):
        os.makedirs('datasets')
    
    hotel_name = extract_hotel_name_from_url(url)
    filename = f"{hotel_name}_reviews.csv"
    
    # Save the file in the 'datasets' folder
    filepath = os.path.join('datasets', filename)
    
    with open(filepath, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Title", "Text", "Rating", "Trip Date"])

        for review in hotel_data["reviews"]:
            writer.writerow([
                review["title"],
                review["text"],
                review["rate"],
                review["tripDate"],
            ])
    
    log.success(f"Saved {len(hotel_data['reviews'])} reviews to {filename}")
    return filename

def extract_hotel_name_from_url(url: str) -> str:
    match = re.search(r'Reviews-(.*?)-', url)
    if match:
        hotel_name = re.sub(r'[^A-Za-z0-9]+', '_', match.group(1))
        return hotel_name.strip('-')
    return "hotel"

async def run():
    url = "https://www.tripadvisor.com/Hotel_Review-g190327-d264936-Reviews-1926_Le_Soleil_Hotel_Spa-Sliema_Island_of_Malta.html"
    hotel_data = await scrape_hotel_reviews(url, max_review_pages=3)
    
    # Save the data to CSV
    save_to_csv(hotel_data, url)


if __name__ == "__main__":
    asyncio.run(run())
