import asyncio
import json
import math
from typing import List, Optional, TypedDict
from urllib.parse import urljoin

import httpx
from loguru import logger as log
from parsel import Selector
from search_responses import scrape_location_data, client
import os
import csv


class Preview(TypedDict):
    url: str
    name: str


def parse_search_page(response: httpx.Response) -> List[Preview]:
    """parse result previews from TripAdvisor search page"""
    log.info(f"parsing search page: {response.url}")
    parsed = []
    # Search results are contain in boxes which can be in two locations.
    # this is location #1:
    selector = Selector(response.text)
    for box in selector.css("span.listItem"):
        title = box.css("div[data-automation=hotel-card-title] a ::text").getall()[1]
        url = box.css("div[data-automation=hotel-card-title] a::attr(href)").get()
        parsed.append(
            {
                "url": urljoin(str(response.url), url),  # turn url absolute
                "name": title,
            }
        )
    if parsed:
        return parsed
    # location #2
    for box in selector.css("div.listing_title>a"):
        parsed.append(
            {
                "url": urljoin(
                    str(response.url), box.xpath("@href").get()
                ),  # turn url absolute
                "name": box.xpath("text()").get("").split(". ")[-1],
            }
        )
    return parsed


async def scrape_search_hotel_urls(
    query: str, max_pages: Optional[int] = None
) -> List[Preview]:
    # log.info(f"{query}: scraping first search results page")
    try:
        location_data = (await scrape_location_data(query, client))[
            0
        ]  # take first result
    except IndexError:
        log.error(f"could not find location data for query {query}")
        return []

    hotel_search_url = "https://www.tripadvisor.com" + location_data["HOTELS_URL"]
    log.success(f"found hotel search url: {hotel_search_url}")

    first_page = await client.get(hotel_search_url)
    if first_page.status_code != 200:
        log.error(f"Scraper is being blocked. Status Code: {first_page.status_code}")
        log.error(f"Response Content: {first_page.text}")
        return []

    # Create a Selector object to parse the response content
    selector = Selector(text=first_page.text)

    # Parse the first page
    results = parse_search_page(first_page)
    if not results:
        log.error(f"query {query} found no results")
        return []

    # Extract pagination metadata
    page_size = len(results)
    total_results = selector.xpath("//span/text()").re(r"(\d*\,*\d+) properties")[0]
    total_results = int(total_results.replace(",", ""))
    next_page_url = selector.css('a[aria-label="Next page"]::attr(href)').get()
    next_page_url = urljoin(hotel_search_url, next_page_url)  # turn url absolute
    total_pages = int(math.ceil(total_results / page_size))

    if max_pages and total_pages > max_pages:
        log.debug(
            f"{query}: only scraping {max_pages} max pages from {total_pages} total"
        )
        total_pages = max_pages

    # Scrape remaining pages
    log.info(
        f"{query}: found {total_results=}, {page_size=}. Scraping {total_pages} pagination pages"
    )
    other_page_urls = [
        next_page_url.replace(f"oa{page_size}", f"oa{page_size * i}")
        for i in range(1, total_pages)
    ]
    assert len(set(other_page_urls)) == len(other_page_urls)

    to_scrape = [client.get(url) for url in other_page_urls]
    for response in asyncio.as_completed(to_scrape):
        results.extend(parse_search_page(await response))

    log.success(f"Scraped {len(results)} search results for {query}")

    return results


def save_to_csv(data: List[Preview], filename: str) -> None:
    """Save search results to a CSV file in the 'datasets' folder."""
    # Ensure the 'datasets' directory exists
    if not os.path.exists("datasets"):
        os.makedirs("datasets")

    # Save the file in the 'datasets' folder
    filepath = os.path.join("datasets", filename)

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["url", "name"])
        writer.writeheader()
        writer.writerows(data)

    log.success(f"Data saved to {filepath}")


if __name__ == "__main__":

    async def run():
        place = "Goa"
        result = await scrape_search_hotel_urls(place, max_pages=5)
        save_to_csv(result, f"{place}.csv")
        print(json.dumps(result, indent=2))

    asyncio.run(run())
