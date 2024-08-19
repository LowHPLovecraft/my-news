import tornado
import certifi
import json
import os
from dotenv import load_dotenv

load_dotenv()

twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
twitch_secret = os.getenv('TWITCH_SECRET')

game_name = "Tom Clancy's Rainbow Six Siege"

def get_headers(access_token):
    return {"accept": "application/vnd.twitchtv.v5+json", "client-id": twitch_client_id, "Authorization": f"Bearer {access_token}"}
    
async def generate_token(host='id.twitch.tv'):
    if not twitch_secret or not twitch_client_id:
        print('- no twitch token found')
        return None
    url = f'https://{host}/oauth2/token?client_id={twitch_client_id}&client_secret={twitch_secret}&grant_type=client_credentials'
    req = tornado.httpclient.HTTPRequest(url=url, method='POST', ca_certs=certifi.where(), body='')
    res = await tornado.httpclient.AsyncHTTPClient().fetch(req)
    access_token = json.loads(res.body.decode())['access_token']
    return access_token

async def get_game_id(game_name, access_token):
    http_client = tornado.httpclient.AsyncHTTPClient()
    try:
        res = await http_client.fetch(
            tornado.httpclient.HTTPRequest(
                url=f'https://api.twitch.tv/helix/games?name={tornado.escape.url_escape(game_name)}',
                headers=get_headers(access_token)))
    except Exception as ex:
        print(ex)
    game_id = json.loads(res.body.decode())['data'][0]['id']
    return game_id

async def get_streams(game_id, access_token):
    http_client = tornado.httpclient.AsyncHTTPClient()    
    url = f'https://api.twitch.tv/helix/streams?game_id={game_id}&first=100&language=ru&language=en'
    try:
        res = await http_client.fetch(
            tornado.httpclient.HTTPRequest(
                url=url, 
                headers=get_headers(access_token)))
    except Exception as ex:
        print(ex)
    streams = json.loads(res.body.decode())['data']
    return streams
                            
async def get_vods(streamer, access_token=None, max_limit=5):
    import pytz
    from dateutil.parser import parse
    access_token = access_token or await generate_token()
    assert access_token
    http_client = tornado.httpclient.AsyncHTTPClient()    
    res = await http_client.fetch(
        tornado.httpclient.HTTPRequest(
            url=f'https://api.twitch.tv/helix/users?login={streamer}',
            headers=get_headers(access_token)))
    msg = json.loads(res.body.decode())
    id = msg['data'][0]['id']
    res = await http_client.fetch(
        tornado.httpclient.HTTPRequest(
            url=f'https://api.twitch.tv/helix/videos?user_id={id}',
            headers=get_headers(access_token)))
    def get_when(when):
        local_tz = pytz.timezone("Europe/London")
        return parse(when).replace(tzinfo=pytz.utc).astimezone(local_tz).strftime('%b %d %H:%M')
    return dict(
        title=f'vods> {streamer}', 
        items=[dict(title=f"{i['title']} - {get_when(i['created_at'])}", link=i['url']) for i in json.loads(res.body.decode())['data']][:max_limit],
        link=f'https://twitch.tv/{streamer}/videos')