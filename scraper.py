import requests
import pandas as pd
from bs4 import BeautifulSoup

def scrape_web_data(url: str):
    html = requests.get(url, timeout=20).text
    soup = BeautifulSoup(html, "lxml")

    # Extract tables
    tables = pd.read_html(html)
    if tables:
        return tables[0]

    # Extract numbers from text
    text = soup.get_text(" ", strip=True)
    numbers = [int(x) for x in text.split() if x.isdigit()]
    return numbers
