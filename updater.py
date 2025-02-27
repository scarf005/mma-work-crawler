import itertools
import traceback
from tqdm.asyncio import tqdm_asyncio
from tqdm import tqdm
import json
import re
import logging
import asyncio
import itertools
import httpx
import time
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup as Soup

URL = "https://work.mma.go.kr"


def hangul_only(s: str):
    return re.sub("[^가-힇]", "", s)


async def __get(client: httpx.AsyncClient, url: str, post: bool):
    while True:
        try:
            if post:
                return parse_qs(urlparse(url).query)["cygonggo_no"][0], await client.get(url)
            return await client.get(url)
        except:
            logging.warning(f"Crawling {url} failed. Retrying...")
            traceback.print_exc()


async def crawl_list(start, end) -> list[httpx.Response]:
    pages = 200
    urls = {
        f"/caisBYIS/search/cygonggogeomsaek.do?pageIndex={i}" for i in range(start, end)
    }
    async with httpx.AsyncClient(verify=False, timeout=None) as client:
        return await tqdm_asyncio.gather(*[__get(client, URL+u, False) for u in urls])


def parse_list(response: httpx.Response) -> list[str]:
    parsed = Soup(response.read(), "html.parser")
    class_ = "title t-alignLt pl10px"
    titles = parsed.find_all("td", class_=class_)
    return [t.find("a")["href"] for t in titles]


async def crawl_posts(hrefs: list[str]):
    async with httpx.AsyncClient(verify=False, timeout=None) as client:
        return await tqdm_asyncio.gather(*[__get(client, URL+h, True) for h in hrefs])


def parse_post(response: tuple[str, httpx.Response]) -> dict[str, dict[str, str]]:
    cygonggo_no = response[0]
    parsed = Soup(response[1].read(), "html.parser")
    result = {"공고번호": cygonggo_no}
    for div in parsed.find_all("div", class_="step1"):
        div_title = hangul_only(div.find("h3").text.strip())
        for i, tr in enumerate(div.find_all("tr")):
            th = tr.find_all("th")
            td = tr.find_all("td")
            if th == []:
                if i == 0:  # 비고
                    result[hangul_only(div_title)] = td[0].get_text(
                        separator="\n", strip=True)
                break
            for head, data in zip(th, td):
                head = hangul_only(head.text)
                data = data.text.strip()
                if head == "전화번호" and head in result:
                    head = "담당자전화번호"
                result[head] = data
    return result


async def run():
    logging.info("Crawling lists")
    lists = await crawl_list(0, 200)
    hrefs = list(itertools.chain(*[parse_list(l) for l in lists]))
    logging.info("Crawling posts")
    posts = await crawl_posts(hrefs)
    logging.info("Parsing posts")
    return [parse_post(p) for p in tqdm(posts)]


if __name__ == "__main__":
    posts = asyncio.run(run())
    if not posts:
        exit(1)
    posts.sort(key=lambda x: x["급여조건"], reverse=True)
    with open("front/data.json", "w", encoding="utf-8") as data_json:
        json.dump(posts, data_json, ensure_ascii=False, indent=4)
    with open("front/time.json", "w", encoding="utf-8") as time_json:
        json.dump({"time": int(time.time())}, time_json)
