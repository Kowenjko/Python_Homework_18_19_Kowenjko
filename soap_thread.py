import asyncio
from pprint import pprint
import aiohttp
import aiofiles
import concurrent.futures as C_F
from multiprocessing import cpu_count
from bs4 import BeautifulSoup
from math import floor
import json
import tracemalloc
import time
from datetime import datetime
from concurrent.futures import as_completed

SELECTED_URL = "https://www.ukr.net/"


def write_txt(adress, dictionary):
    file = open(adress, 'a')
    file.write(dictionary)
    file.close()


def print_txt(title, start_time):
    adr = 'result.txt'
    write_txt(adr, '\n ')
    write_txt(adr, '-'*50)
    write_txt(adr, f'\n{title}\n')
    write_txt(adr, '-'*50)
    write_txt(adr, "\n\tCurent %d, Peak %d" %
              tracemalloc.get_traced_memory())
    write_txt(adr, f"\n\tAll done! {format(time.time()-start_time)}")


async def write_json(address, dictionary):
    async with aiofiles.open(address, mode='w', encoding="utf-8") as outfile:
        await outfile.write(json.dumps(dictionary, indent=4, sort_keys=False, ensure_ascii=False))
        outfile.close()


async def get_response():
    async with aiohttp.ClientSession() as Client:
        async with Client.get(SELECTED_URL) as response:
            if response.status != 200:
                response.raise_for_status()
            page = await response.text()
            soup = BeautifulSoup(page, features="html.parser")
            sections = soup.find_all('section', class_='items')[1:]
            return sections


async def get_items_from_section(section_id, section_list):
    items = section_list[section_id].find_all('div', class_='item')
    news_list = []
    for item in items:
        category = section_list[section_id].find('h2').text
        title = item.find('a').text
        url = item.find('a').get('href')
        source = item.find('span').text[1:-1]
        time = item.find('time').text
        news_list.append(get_object(category, title, url, source, time))
    return news_list


def start_parsing(id, section_list):
    return asyncio.run(get_items_from_section(id, section_list))


def get_object(category, title, url, source, time):
    return {'category': category, 'title': title, 'url': url, 'source': source, 'time': time}


def main():
    section_list = asyncio.run(get_response())
    ukr_data = {}
    NUM_SECTION = len(section_list)
    NUM_CORES = cpu_count()
    OUTPUT_FILE = './top_news.json'

    PAGES_PER_CORE = floor(NUM_SECTION/NUM_CORES)
    PAGES_FOR_FINAL = NUM_SECTION - PAGES_PER_CORE

    with C_F.ThreadPoolExecutor(NUM_CORES) as executor:
        futures = [executor.submit(start_parsing, i, section_list)
                   for i in range(NUM_SECTION)]

    C_F.wait(futures)
    data = []
    for f in as_completed(futures):
        data = data+f.result()
    ukr_data['site'] = SELECTED_URL
    ukr_data['date'] = datetime.today().strftime("%d.%m.%Y")
    ukr_data['news'] = data

    asyncio.run(write_json(OUTPUT_FILE, ukr_data))


if __name__ == "__main__":
    tracemalloc.start()
    start = time.time()
    main()
    print_txt('Parallelism - ThreadPoolExecutor', start)
    print("Current %d, Peak %d" % tracemalloc.get_traced_memory())
    print('All done! {}'.format(time.time() - start))
