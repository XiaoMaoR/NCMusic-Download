from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from concurrent.futures import ThreadPoolExecutor
from random import randrange
from hashlib import md5
import urllib.parse
import requests
import json

AES_KEY = b"e82ckenh8dichen8"
COOKIE = "你的COOKIE"
GLOBAL_EXECUTOR = ThreadPoolExecutor(max_workers=20)
session = requests.Session()
session.trust_env = False
session.proxies = {}

# 音质对照
# levels = {
#     'standard': "标准音质",
#     'exhigh': "极高音质",
#     'lossless': "无损音质",
#     'hires': "Hires音质",
#     'sky': "沉浸环绕声",
#     'jyeffect': "高清环绕声",
#     'jymaster': "超清母带"
# }

# 解析原始cookies
# def parse_cookies(text: str):
#     cookie_ = [item.strip().split('=', 1) for item in text.strip().split(';') if item]
#     cookie_ = {k.strip(): v.strip() for k, v in cookie_}
#     return cookie_

# 工具

def hex_digest(data):
    return "".join([hex(d)[2:].zfill(2) for d in data])

def hash_digest(text):
    HASH = md5(text.encode("utf-8"))
    return HASH.digest()

def hash_hex_digest(text):
    return hex_digest(hash_digest(text))

def post(url, params, cookie):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154',
        'Referer': '',
    }

    cookies = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "xiaomao"
    }

    cookies.update(cookie)
    response = session.post(url, headers=headers, cookies=cookies, data={"params": params})
    return response.text

# 调用

def get_id(id):
    if '163cn.tv' in id:
        response = session.get(id, allow_redirects=False)
        id = response.headers.get('Location')
    if 'music.163.com' in id: # type: ignore
        index = id.find('id=') + 3 # type: ignore
        id = id[index:].split('&')[0] # type: ignore
    return id

def get_size(value):
    units = ["B", "KB", "MB", "GB", "TB"]
    size = 1024.0
    for i in range(len(units)):
        if (value / size) < 1:
            return "%.2f%s" % (value, units[i])
        value = value / size
    return value

def get_url(id, level, cookies):
    url = "https://interface3.music.163.com/eapi/song/enhance/player/url/v1"

    config = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "xiaomao",
        "requestId": str(randrange(20000000, 30000000))
    }

    payload = {
        'ids': [id],
        'level': level,
        'encodeType': 'flac',
        'header': json.dumps(config),
    }
    # 实际为c51,但是叫sky更好听
    if level == 'sky':
        payload['immerseType'] = 'c51'
    url2 = urllib.parse.urlparse(url).path.replace("/eapi/", "/api/")
    digest = hash_hex_digest(f"nobody{url2}use{json.dumps(payload)}md5forencrypt")
    params = f"{url2}-36cd479b6b5-{json.dumps(payload)}-36cd479b6b5-{digest}"
    padder = padding.PKCS7(algorithms.AES(AES_KEY).block_size).padder()
    padded_data = padder.update(params.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
    encryptor = cipher.encryptor()
    enc = encryptor.update(padded_data) + encryptor.finalize()
    params = hex_digest(enc)
    response = post(url, params, cookies)
    return json.loads(response)

def get_name(id):
    urls = "https://interface3.music.163.com/api/v3/song/detail"
    data = {'c': json.dumps([{"id":id,"v":0}])}
    response = session.post(url=urls, data=data)
    return response.json()

def get_lyric(id, cookies):
    url = "https://interface3.music.163.com/api/song/lyric"
    data = {'id': id, 'cp': 'false', 'tv': '0', 'lv': '0', 'rv': '0', 'kv': '0', 'yv': '0', 'ytv': '0', 'yrv': '0'}
    response = session.post(url=url, data=data, cookies=cookies)
    return response.json()

def get_song(url, level='exhigh'):
    song_id = get_id(url)
    url = get_url(song_id, level, COOKIE)
    name = get_name(url['data'][0]['id'])
    lyric = get_lyric(url['data'][0]['id'], COOKIE)
    if url['data'][0]['url'] is not None:
        output_data = {
            'song_name': name['songs'][0]['name'],  # 歌曲名称
            'song_picUrl': name['songs'][0]['al']['picUrl'],  # 歌曲封面图片
            'song_alname': name['songs'][0]['al']['name'],  # 专辑名称
            'song_arname': ', '.join([ar['name'] for ar in name['songs'][0]['ar']]),  # 歌手名称
            'music_quality': url['data'][0]['level'],  # 音质等级
            'file_size': get_size(url['data'][0]['size']),  # 文件大小
            'song_url': url['data'][0]['url'],  # 音频链接
            'lyrics': lyric['lrc']['lyric'],  # 歌词
            'translated_lyrics': lyric.get('tlyric', {}).get('lyric', None),  # 翻译歌词
        }
        return output_data
    else:
        return None

def search_songs(search_name: str, limit: int = 10, offset: int = 0, type: int = 1, cover: bool = False):
    payload = {
        "csrf_token": "hlpretag=",
        "hlposttag": "",
        "s": search_name,
        "type": type,
        "offset": offset,
        "total": "true",
        "limit": limit
    }

    response = session.get(url=f"https://music.163.com/api/search/get/web", params=payload)
    if type == 1:
        songs = response.json()["result"]["songs"]
        def process_song(song):
            song_id = song["id"]
            name = song["name"]
            artist_info = [artist["name"] for artist in song["artists"]]
            album_name = song["album"]["name"]
            duration = song["duration"] / 1000 / 60
            alias = song.get("alias", [])
            transnames = song.get("transNames", [])
            if cover:
                cover_url = f"{get_name(song_id)['songs'][0]['al']['picUrl']}?param=130y130"
            else:
                cover_url = ""

            song_info = {
                "id": song_id,
                "cover": cover_url,
                "name": name,
                "songer": artist_info,
                "album": album_name,
                "long": round(duration, 2)
            }

            if alias:
                song_info["alias"] = ", ".join(alias)
            if transnames:
                song_info["transnames"] = ", ".join(transnames)
            return song_info
        results = list(GLOBAL_EXECUTOR.map(process_song, songs))
        return results