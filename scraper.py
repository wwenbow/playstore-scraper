#!/usr/local/bin/python3

from bs4 import BeautifulSoup
import json
import requests
import sys
import asyncio
import aiohttp
import tqdm
import argparse
import os
import traceback


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
def save_info(url, package, sem, outdir):
    info = yield from get_info(url, sem)
    if info == 'blacklist':
        with open(outdir + '/blacklist.txt', 'a') as blacklist:
            blacklist.write(package + '\n')
    else:
        with open(outdir + '/appdata.json', 'a') as outfile:
            json.dump(info, outfile)
            outfile.write('\n')
    return



def get_app_info(soup):
    appinfo = {}
    try:
        appinfo['package'] = soup.find('div', class_='details-wrapper')['data-docid']
        appinfo['icon'] = soup.find('img', alt='Cover art')['src']
        appinfo['name'] = soup.find('div', class_='id-app-title').contents[0]
        appinfo['developer'] = soup.find('a', class_='document-subtitle primary').contents[1].contents[0]
        appinfo['genre'] = soup.find('span', itemprop='genre').contents[0]

        rating_badge = soup.find('img', class_='content-rating-badge')
        if rating_badge is None:
            appinfo['rated'] = 'Unrated'
        else:
            appinfo['rated'] = rating_badge['alt']

        score = soup.find('div', class_='score')
        if score is None:
            appinfo['score'] = 'Unscored'
        else:
            appinfo['score'] = score.contents[0]
    except AttributeError as e:
        print('package {} failed to get some data returning what we have'.format(appinfo['package']))
        traceback.print_exc()
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
    parser = argparse.ArgumentParser(description='Scrape the play store for package meta data')
    parser.add_argument('-o', '--output', help='output directory')
    args = parser.parse_args()

    if args.output is None:
        print('please specify output directory')
        sys.exit(1)

    os.mkdir(args.output)

    baseurl = 'https://play.google.com/store/apps/details'
    country = 'ph'

    sem = asyncio.Semaphore(10)
    loop = asyncio.get_event_loop()
    tasks = []

    with open('packages.txt') as pkglist:
        for package in pkglist.readlines():
            package = package.splitlines()[0]
            print(package)

            url = '{}?id={}&gl={}'.format(baseurl, package, country)
            tasks.append(save_info(url, package, sem, args.output))

    loop.run_until_complete(wait_with_progress(tasks))
    loop.close()
    return 0


if __name__ == "__main__":
    main()
