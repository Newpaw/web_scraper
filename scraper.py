import logging
import aiohttp
import asyncio


from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from models import UrlData
from logging_conf import logger

async def fetch(session, url):
    try:
        async with session.get(url) as response:
            return await response.text()
    except UnicodeDecodeError as error:
        logger.error(f'Error fetching URL {url}: {error}')
        return ''


async def fetch_robots(session, base_url):
    robots = RobotFileParser()
    robots_url = urljoin(base_url, '/robots.txt')
    content = await fetch(session, robots_url)
    if content:
        robots.parse(content.splitlines())
    return robots


async def parse(session, base_url, url, depth=0, records_len=0):
    if depth > 2:
        return None, []

    body = await fetch(session, url)
    soup = BeautifulSoup(body, 'html.parser')

    titles = {f"h{i}": (soup.find(f"h{i}").get_text(strip=True)
                        if soup.find(f"h{i}") else None)
              for i in range(1, 6)}
    paragraphs = ' '.join(p.get_text(' ', strip=True)
                          for p in soup.find_all('p'))

    urls = []
    if depth < 2:
        urls = [urljoin(base_url, link['href'])
                for link in soup.find_all('a', href=True)
                if base_url in urljoin(base_url, link['href'])]

    url_data = UrlData(id=str(records_len), h1=titles.get('h1'), h2=titles.get('h2'), h3=titles.get('h3'), 
                       h4=titles.get('h4'), h5=titles.get('h5'), paragraf_content=paragraphs, url=url)
    return url_data, urls



async def scrape_website_async(base_url):
    """
    Asynchronous web scraping function.

    Parameters:
    base_url (str): The base URL to scrape data from.

    Returns:
    List[UrlData]: A list of UrlData objects, each containing data scraped from a specific URL.
    """
    async with aiohttp.ClientSession() as session:
        records = []
        urls_to_parse = [(base_url, 0)]

        robots = await fetch_robots(session, base_url)

        while urls_to_parse:
            url, depth = urls_to_parse.pop(0)

            if not robots.can_fetch('*', url):
                logger.warning(f'URL disallowed by robots.txt: {url}')
                continue

            url_data, new_urls = await parse(session, base_url, url, depth, len(records))
            if url_data:
                records.append(url_data)

            logging.debug(f'Processed {len(records)} records so far.')

            urls_to_parse.extend((new_url, depth+1) for new_url in new_urls
                                 if new_url not in (url for url, _ in urls_to_parse))

        return records



if __name__ == "__main__":
    pass
