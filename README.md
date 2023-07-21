# Web Scraper API
This is a simple asynchronous web scraping API built using FastAPI, aiohttp, and BeautifulSoup. The API allows users to scrape specified websites and return the processed data. The scraping tasks are processed asynchronously in the background, and the results are sent to a registered webhook.

## Endpoints
The API provides the following endpoints:

- POST /register - Registers a new client and returns a client ID (API key)
- POST /webhook/{client_id} - Registers a webhook for a client
- GET /scrape/{base_url} - Starts a new scraping job

## Installation
You can clone this project and install the dependencies with pip:

``` sh
git clone https://github.com/yourusername/webscraper-api.git
cd webscraper-api
pip install -r requirements.txt
```
## Usage
Run the FastAPI application:

``` sh
uvicorn main:app --host 0.0.0.0 --port 8000
```
Then you can access the API at http://localhost:8000.

To start a scraping job, first register a new client:

```sh
curl -X POST http://localhost:8000/register
```
This will return a client ID that you can use to access the other endpoints. Then, register a webhook:

```sh
curl -X POST http://localhost:8000/webhook/{client_id} -d '{"webhook_url": "http://example.com/webhook"}'
```
Finally, you can start a scraping job:

```sh
curl http://localhost:8000/scrape/{base_url}?client_id={client_id}
```
This will start a new scraping job for the specified base URL. The results will be sent to the registered webhook URL when the job is finished.

## Note
Replace {client_id} and {base_url} with actual client_id and the website you want to scrape respectively in above curl commands.

## License

[MIT](https://choosealicense.com/licenses/mit/)
