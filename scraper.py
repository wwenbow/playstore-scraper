#!/usr/local/bin/python3

from bs4 import BeautifulSoup
import json
import requests
import sys
import asyncio
import aiohttp
import tqdm


@asyncio.coroutine
def wait_with_progress(coros):
    for f in tqdm.tqdm(asyncio.as_completed(coros), total=len(coros)):
        yield from f


@asyncio.coroutine
def get_url(*args, **kwargs):
    response = yield from aiohttp.request('GET', *args, **kwargs)
    resp = { 'code' : response.status, 'page' : (yield from response.text()) }
    response.close()
    return resp


@asyncio.coroutine
def get_info(url, sem):
    with (yield from sem):
        response = yield from get_url(url)
        if response['code'] != 200:
            return 'blacklist'
        else:
            soup = BeautifulSoup(response['page'], 'html.parser')
            appinfo = get_app_info(soup)
            similar_items = get_similar_items(soup)
            appinfo['similar'] = similar_items
            return appinfo


@asyncio.coroutine
def save_info(url, package, sem):
    info = yield from get_info(url, sem)
    if info == 'blacklist':
        with open('blacklist.txt', 'a') as blacklist:
            blacklist.write(package + '\n')
    else:
        with open('appdata.json', 'a') as outfile:
            json.dump(info, outfile)
            outfile.write('\n')
    return



def get_app_info(soup):
    appinfo = {}
    try:
        appinfo['icon'] = soup.find('img', alt='Cover art')['src']
        appinfo['name'] = soup.find('div', class_='id-app-title').contents[0]
        appinfo['score'] = soup.find('div', class_='score').contents[0]
        appinfo['genre'] = soup.find('span', itemprop='genre').contents[0]
        appinfo['developer'] = soup.find('a', class_='document-subtitle primary').contents[1].contents[0]

        rating_badge = soup.find('img', class_='content-rating-badge')
        if rating_badge is None:
            appinfo['rated'] = 'Unrated'
        else:
            appinfo['rated'] = rating_badge['alt']
    except AttributeError as e:
        print(soup.title)
        print(e)
        sys.exit(1)
    finally:
        return appinfo


def get_similar_items(soup):
    similar_items = []
    cards = soup.find('div', class_='rec-cluster').contents[3]
    for card in cards.children:
        if (card != ' '):
            similar_items.append(card.find('div', class_='card-content')['data-docid'])
    return similar_items


def main():
    baseurl = 'https://play.google.com/store/apps/details'
    country = 'ph'

    sem = asyncio.Semaphore(10)
    loop = asyncio.get_event_loop()
    tasks = []

    with open('packagesC.txt') as pkglist:
        for package in pkglist.readlines():
            package = package.splitlines()[0]
            print(package)

            url = '{}?id={}&gl={}'.format(baseurl, package, country)
            tasks.append(save_info(url, package, sem))
            # r = requests.get(url)
            # if r.status_code != 200:
            #     print('blacklisted')
            #     blacklist.write(package + '\n')
            # else:
            #     soup = BeautifulSoup(r.text, 'html.parser')
            #
            #     appinfo = getAppInfo(soup)
            #     similar_items = getSimilarItems(soup)
            #     appinfo['similar'] = similar_items
            #
            #     json.dump(appinfo, outfile)
            #     outfile.write('\n')

    loop.run_until_complete(wait_with_progress(tasks))
    loop.close()


if __name__ == "__main__":
    main()
