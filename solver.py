import re
from scraper import scrape_web_data
from arithmetic import solve_arithmetic
from downloader import load_file

def solve(question: str, soup):
    q = question.lower()

    # Arithmetic / word problem
    arith = solve_arithmetic(question)
    if arith is not None:
        return round(arith, 2)

    # File-based analysis
    link = soup.find("a")
    if link:
        data = load_file(link["href"])
        if hasattr(data, "columns"):
            col = data.select_dtypes("number").columns[0]
            if "sum" in q:
                return float(data[col].sum())
            if "max" in q:
                return float(data[col].max())
            if "min" in q:
                return float(data[col].min())
            if "count" in q:
                return int(len(data))

    # Web scraping based question
    url_match = re.findall(r"https?://\S+", question)
    if url_match:
        scraped = scrape_web_data(url_match[0])
        if hasattr(scraped, "sum"):
            return float(scraped.sum().sum())

    return "Alpha"
