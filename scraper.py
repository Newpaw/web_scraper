import aiohttp
import asyncio
import time
import uuid
import json
import redis
import os


from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
from typing import List

from models import UrlData
from logging_conf import logger


redis_host_name = os.environ.get("REDIS_HOST_NAME", "localhost")

try:
    redis_instance = redis.Redis(host=redis_host_name, port=6379, db=0)
except redis.RedisError as e:
    logger.error(f"Nepodařilo se připojit k Redisu: {e}")
    redis_instance = None

async def fetch(session, url):
    """Fetch the content of url"""
    try:
        async with session.get(url) as response:
            final_url = str(response.url)
            content = await response.text()
            return content, final_url
    except UnicodeDecodeError as error:
        logger.info(f"Error fetching URL {url}: {error}")
        return "", url



async def fetch_robots(session, base_url):
    """Fetch the robots.txt file from base_url"""
    robots = RobotFileParser()
    robots_url = urljoin(base_url, "/robots.txt")
    content, _ = await fetch(session, robots_url)  # Unpack the tuple returned by fetch()
    if content:
        robots.parse(content.splitlines())
    return robots


async def parse(session, base_url, url, depth=0):
    """Parse the HTML of url"""
    if depth > 2:
        return None, []

    body, url = await fetch(session, url)  # Unpack the tuple returned by fetch()
    soup = BeautifulSoup(body, "html.parser")

    titles = {
        f"h{i}": (
            soup.find(f"h{i}").get_text(strip=True) if soup.find(f"h{i}") else None
        )
        for i in range(1, 6)
    }
    paragraphs = " ".join(p.get_text(" ", strip=True).replace('\u200d', ' ') for p in soup.find_all("p"))

    urls = []
    if depth < 2:
        urls = [
            urljoin(base_url, link["href"])
            for link in soup.find_all("a", href=True)
            if base_url in urljoin(base_url, link["href"])
        ]

    url_data = UrlData(
        id=str(uuid.uuid4()),  # Generate a new, unique ID for each record
        h1=titles.get("h1"),
        h2=titles.get("h2"),
        h3=titles.get("h3"),
        h4=titles.get("h4"),
        h5=titles.get("h5"),
        paragraf_content=paragraphs,
        url=url,
    )
    return url_data, urls

async def log_processed_records(records):
    """Log the number of processed records every 10 seconds"""
    while True:
        logger.warning(f'Processed {len(records)} records so far.')
        await asyncio.sleep(10) 


def store_to_redis(base_url, records):
    """Store the given records into Redis with the base URL as the key"""
    
    if redis_instance is not None:
        # Convert records into JSON format and store into Redis
        redis_instance.setex(base_url, 24 * 60 * 60, json.dumps([record.__dict__ for record in records]))
        logger.info(f"Data for url {base_url} are stored to redis.")

def get_from_redis(base_url):
    """Get the records associated with the base URL from Redis"""
    if redis_instance is not None and redis_instance.exists(base_url):
        logger.info(f"Use cached data for {base_url}")
        records_json = json.loads(redis_instance.get(base_url))
        # Convert back into UrlData objects
        records = [UrlData(**record_dict) for record_dict in records_json]
        return records
    return None

async def scrape_website_async(base_url:str, concurrent_tasks:int = 10) -> List[UrlData]:
    """
    An asynchronous function that scrapes a website and returns all the 
    collected data.

    Parameters:
        base_url (str): The base URL of the website to scrape. This should 
        start with 'http://' or 'https://'.
        
        concurrent_tasks (int): The maximum number of concurrent tasks 
        allowed for the scraping process. Default is 10.

    Returns:
        records (list): A list of records containing the scraped data.
    """
    records = get_from_redis(base_url)
    if records is not None:
        return records

    session = aiohttp.ClientSession()
    records = []
    urls_to_parse = [(base_url, 0)]
    tasks = set()
    sem = asyncio.Semaphore(concurrent_tasks)  # Limit the number of concurrent tasks

    # Fetch initial URL and get possible redirected base_url
    _, new_base_url = await fetch(session, base_url)
    robots = await fetch_robots(session, new_base_url)

    log_task = asyncio.create_task(log_processed_records(records))

    try:
        while urls_to_parse or tasks:  # Wait for tasks to complete
            if urls_to_parse and len(tasks) < concurrent_tasks:
                url, depth = urls_to_parse.pop(0)

                if not robots.can_fetch('*', url):
                    logger.warning(f'URL disallowed by robots.txt: {url}')
                    continue

                async with sem:
                    task = asyncio.create_task(parse(session, new_base_url, url, depth))
                    tasks.add(task)
            else:
                done_tasks, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done_tasks:
                    url_data, new_urls = task.result()
                    if url_data:
                        records.append(url_data)

                    urls_to_parse.extend((new_url, depth+1) for new_url in new_urls
                                         if new_url not in (url for url, _ in urls_to_parse))
    finally:
        await session.close()
        for task in tasks:
            task.cancel()
        log_task.cancel()
        await asyncio.gather(*tasks, log_task, return_exceptions=True)
    
    store_to_redis(base_url,records)
    return records

async def main():
    """Main function to test the web scraper"""
    base_url = "mluvii.com"
    for concurrent_tasks in [10100]:
        start = time.time()
        test = await scrape_website_async(f"https://{base_url}/", concurrent_tasks)
        end = time.time()
        print(
            f"Time taken with {concurrent_tasks} concurrent tasks: {end - start} seconds. {len(test)}"
        )

if __name__ == "__main__":
    #pass
    asyncio.run(main())
    
