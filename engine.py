import requests
from bs4 import BeautifulSoup
from browser import render_page
from parser import extract_question
from solver import solve

def run_quiz(start_url, email, secret):
    url = start_url

    while True:
        html = render_page(url)
        soup = BeautifulSoup(html, "lxml")
        question = extract_question(html)
        answer = solve(question, soup)

        submit_url = soup.find("form")["action"]

        payload = {
            "email": email,
            "secret": secret,
            "url": url,
            "answer": answer
        }

        response = requests.post(submit_url, json=payload).json()

        if response.get("url"):
            url = response["url"]
        else:
            return response
