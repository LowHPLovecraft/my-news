import dateutil.parser as da
import tornado
import tornado.httpclient as httpclient
import bs4
import asyncio
import certifi
import feedparser
import pytz
import datetime 
import json
import re

import twitch

from fnmatch import fnmatch
from xml.etree.ElementTree import fromstring
from rich.pretty import pprint

local_tz = pytz.timezone("Europe/London")

def get_now():
    return datetime.datetime.now().replace(tzinfo=pytz.utc).astimezone(local_tz)

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'
}

def parse_ignore_list(ignore_list):
    return [kw.strip() for kw in ignore_list.split(',')] if ignore_list else []

def try_parse_xml(res, encoding='utf-8', verbose=False):
    try:
        text = res.body.decode(encoding).replace('raquo', '#187;')
        return fromstring(text)
    except Exception as ex:
        if verbose:
            print(encoding, ex)
    return None

async def fetch(url):
    req = httpclient.AsyncHTTPClient().fetch(httpclient.HTTPRequest(url, ca_certs=certifi.where()))
    try:
        return await req
    except httpclient.HTTPError as ex:
        return ex

async def fetch_rss(url='', max_limit=5, skip=0, ignore_list=None):
    assert url
    ignore_list = parse_ignore_list(ignore_list)
    res = await fetch(url)
    items = []
    if isinstance(res, httpclient.HTTPError):
        return dict(error=f'- {res.code}: {url}')
    doc = feedparser.parse(res.body.decode())
    if not doc:
        return dict(error='cant parse')
    for i in doc.entries:
        if any(x in i.title for x in ignore_list):
            continue
        pub_date = i.get('published')
        items.append(dict(
            title=i.title, 
            link=i.link, 
            date=da.parse(pub_date) if pub_date else 0))
    return dict(title=doc.feed.get('title', f'rss> {url}'), items=list(sorted(items, key=lambda x: x['date'], reverse=1))[skip:skip+max_limit], link=url)

async def fetch_cdkeys():
    url = 'https://www.cdkeys.com/daily-deals'
    res = await fetch(url)
    soup = bs4.BeautifulSoup(res.body, 'html.parser')
    products = soup.find_all('a', {'class': 'product-item-link'})
    items = []
    for p in set(products):
        link = p.get('href')
        if not 'xbox-live' in link.lower():
            items.append(dict(title=p.get('title'), link=link))
    return dict(title=f'cdkeys', items=items, link=url)

async def fetch_hackersnews(max_limit=10):
    url = 'https://news.ycombinator.com/front'
    res = await fetch(url)
    soup = bs4.BeautifulSoup(res.body, 'html.parser')
    comments = [a for a in soup.select('span.subline a') if 'comments' in a.string]
    titles = soup.select('.titleline>a')
    items = []
    for title, comment in zip(titles, comments):
        items.append(dict(title=title.string, link=f'https://news.ycombinator.com/{comment["href"]}'))
    return dict(title=f'hackersnews', items=items[:max_limit], link=url)
        
async def fetch_top_twitch_streams(game_name="Tom Clancy's Rainbow Six Siege", max_limit=20, ignore_list=None):
    access_token = await twitch.generate_token()
    game_id = await twitch.get_game_id(game_name, access_token)
    streams = await twitch.get_streams(game_id, access_token)
    ignore_list = parse_ignore_list(ignore_list)
    streams = [stream for stream in streams if not any(fnmatch(stream['user_login'], kw) for kw in ignore_list)]
    items = []
    for stream in streams[:max_limit]:
        user = stream['user_login'] 
        link = f'https://twitchls.com/{user}'
        items.append(dict(title=f'{user} {stream["title"]}', link=link))
    return dict(title=f'twitch> {game_name}', items=items, link=f'https://twitch.tv/{game_name}')

async def fetch_r6_news():
    url = 'https://www.ubisoft.com/en-us/game/rainbow-six/siege/news-updates'
    res = await fetch(url)
    soup = bs4.BeautifulSoup(res.body, 'html.parser')
    items = []
    for item in soup.select('.updatesFeed__item'):
        items.append(dict(
            title=item.select('.updatesFeed__item__wrapper__content__title')[0]['data-innertext'],
            link=f'https://www.ubisoft.com{item["href"]}'))
    return dict(title='r6news', items=items, link=url)

async def fetch_weather(id=2650225):
    url = f'https://www.bbc.com/weather/{id}'
    res = await fetch(url)
    soup = bs4.BeautifulSoup(res.body, 'html.parser')
    def get_info(day):
        return (
            soup.select(f'#daylink-{day} > div.wr-day__title.wr-js-day-content-title > div > span.wr-date__longish')[0].text,
            soup.select(f'#daylink-{day} > div.wr-day__body > div.wr-day__weather-type-description-container > div')[0].text,
            soup.select(f'#daylink-{day} > div.wr-day__body > div.wr-day__details-container > div > div.wr-day__temperature > div > div.wr-day-temperature__high > span.wr-day-temperature__high-value > span > span.wr-value--temperature--c')[0].text)
    now_temp = soup.select('#wr-forecast > div.wr-time-slot-container > div > div.wr-time-slot-container__details-container > div.wr-time-slot-container__slots > div > div > div > div.wr-time-slot-list__item.wr-time-slot-list__item--time-slots > ol > li:nth-child(1) > button > div.wr-time-slot-primary.wr-js-time-slot-primary div.wr-time-slot-primary__body > div.wr-time-slot-primary__weather-curve > div > div > div.wr-time-slot-primary__temperature > span > span.wr-value--temperature--c')[0].text
    now_desc = soup.select('#daylink-0 > div:nth-child(4) > div:nth-child(2) > div:nth-child(1)')[0].text
    items = [dict(title=f'{now_temp} {now_desc} - Today', link=url)]
    for day in range(1, 6):
        week_day, desc, temp = get_info(day)
        items.append(dict(title=f'{temp} {desc} - {week_day}', link=url))
    return dict(title='weather', items=items, link=url)

async def fetch_upcoming_r6_matches(max_limit=5):
    from dateutil.parser import parse
    import pytz
    import datetime
    local_tz = pytz.timezone("Europe/London")
    url = 'https://liquipedia.net/rainbowsix/Main_Page'
    res = await fetch(url)
    soup = bs4.BeautifulSoup(res.body, 'html.parser')
    def strip(s):
        return s.replace(' (page does not exist)', '')
    items = []
    for table in soup.find_all('table', class_='infobox_matches_content'):
        attr = table.select('span[data-stream-twitch]')
        if attr:
            teams = table.select('span.team-template-text > a')
            if len(teams) != 2:
                continue
            team_l, team_r = teams
            a = table.select('span.league-icon-small-image a')[0]
            title = f"[{a['title']}] {strip(team_l['title'])} vs {strip(team_r['title'])}"
            try:
                when = parse(table.select_one('.timer-object-countdown-only').contents[0]).replace(tzinfo=pytz.utc).astimezone(local_tz)
                now = get_now()
                when_title = when.strftime('%b %d %H:%M') if now < when else 'LIVE'
                title = f"{title} - {when_title}"
            except Exception as ex:
                print(ex)
            link = f"https://liquipedia.net{a['href']}"
            item = dict(title=title, link=link)
            if not item in items:
                items.append(item)
    return dict(items=items[:max_limit], title='liquipedia', link=url)

async def fetch_twitch_streamer_vods(name, max_limit=5):
    return await twitch.get_vods(name, max_limit=5)

async def fetch_epic_free_games(max_limit=5):
    import pprint
    items = []
    res = await fetch('https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=GB&allowCountries=GB')
    data = json.loads(res.body.decode())['data']
    for i in data['Catalog']['searchStore']['elements']:
        try:
            if i['promotions'] and i['promotions']:
                promos_now = i['promotions']['promotionalOffers']
                if promos_now and promos_now[0]['promotionalOffers']:
                    active_now = any(i['discountSetting']['discountPercentage']==0 for i in promos_now[0]['promotionalOffers'])
                    if active_now:
                        try:
                            url = f"https://store.epicgames.com/en-US/p/{i['catalogNs']['mappings'][0]['pageSlug']}"
                        except:
                            url = 'https://store.epicgames.com/en-US/free-games'
                        title = f"{i['title']}"
                        items.insert(0, dict(title=title, link=url))
                promos_future = i['promotions']['upcomingPromotionalOffers']
                if promos_future and promos_future[0]['promotionalOffers']:
                    active_future = any(i['discountSetting']['discountPercentage']==0 for i in promos_future[0]['promotionalOffers'])
                    if active_future:
                        try:
                            url = f"https://store.epicgames.com/en-US/p/{i['catalogNs']['mappings'][0]['pageSlug']}"
                        except:
                            url = 'https://store.epicgames.com/en-US/free-games'
                        title = f"Soon: {i['title']}"
                        items.append(dict(title=title, link=url))
        except:
            pprint.pprint(i)
    return dict(title='epic free games', items=items[:max_limit], link='https://epicgames.com/freegames')

async def fetch_movies_in_theatres(max_limit=20, ignore_list=None):
    domain = 'https://www.cineworld.co.uk/cinemas/edinburgh/037'
    res = await fetch('https://www.cineworld.co.uk/uk/data-api-service/v1/feed/10108/byName/now-playing?lang=en_GB')
    data = json.loads(res.body.decode())
    items = []
    ignore_list = parse_ignore_list(ignore_list)
    for i in data['body']['posters']:
        title = f"{i['featureTitle']} | {'/'.join(i['attributes'])}"
        url = i['url']
        if not any(x in title for x in ignore_list):
            items.append(dict(title=title, link=url))
    return dict(title='movies in theater', items=items[:max_limit], link=domain)

async def fetch_downdetector(service='rainbow-six'):
    url = f'https://downdetector.co.uk/status/{service}/'
    res = await fetch(url)
    ys = re.findall(r"y: (\d+)", res.body.decode('raw_unicode_escape'), re.DOTALL)
    mid = len(ys)//2
    return dict(title=url, items=[dict(title=f"Reports: {'-'.join(ys[mid-5:mid])}", link=url)])

async def fetch_rotten_tomatoes():
    res = await fetch('https://www.rottentomatoes.com/browse/movies_at_home/')
    doc = bs4.BeautifulSoup(res.body, 'html.parser')
    items = []
    for i in doc.find_all('a', {'data-track': 'scores'}):
        attrs = i.find('score-pairs-deprecated').attrs
        audiencescore = attrs['audiencescore']
        criticsscore = attrs['criticsscore']
        if audiencescore and criticsscore:
            title = f"{i.span.text.strip()} | audience/{audiencescore} critics/{criticsscore}"
            items.append(dict(title=title, link=f"https://www.rottentomatoes.com{i.attrs['href']}"))
    return dict(title='rotten tomatoes', items=items)

if __name__ == '__main__':
    import pprint
    pprint.pprint(asyncio.run(fetch_movies_in_theatres()))
    