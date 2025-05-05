from fastapi.responses import HTMLResponse
from fastapi import FastAPI, staticfiles
from pydantic import BaseModel
from typing import Literal
import NCMusicApi

app = FastAPI()
# WebUI完善中
# app.mount("/static", staticfiles.StaticFiles(directory="static"), name="static")

class GetFullSong(BaseModel):
    song_url: str
    song_level: Literal['standard','exhigh','LosslessFloat','hires','sky','jyeffect','jymaster']

class v1Api(BaseModel):
    song_url: str

@app.post("/api/v1/song_url")
async def get_song_url(data: GetFullSong):
    try:
        song_id = NCMusicApi.get_id(data.song_url)
        song_url = NCMusicApi.get_url(song_id, data.song_level, NCMusicApi.COOKIE)
        return {
            "song_id": song_url['data'][0]['id'],
            "song_url": song_url['data'][0]['url'],
            "song_level": song_url['data'][0]['level'],
            "file_size": NCMusicApi.get_size(song_url['data'][0]['size'])
        }
    except Exception as e:
        return {
            "error": str(e)
        }

@app.post("/api/v1/lyrcic")
async def get_lyric(data: v1Api):
    try:
        song_id = NCMusicApi.get_id(data.song_url)
        lyric = NCMusicApi.get_lyric(song_id, NCMusicApi.COOKIE)
        return {
            "lyrics": lyric['lrc']['lyric'],
            "translated_lyrics": lyric.get('tlyric', {}).get('lyric', None)
        }
    except Exception as e:
        return {
            "error": str(e)
        }

@app.post("/api/v1/about")
async def get_about(data: v1Api):
    try:
        song_id = NCMusicApi.get_id(data.song_url)
        about = NCMusicApi.get_about(song_id)
        return {
            "song_name": about['songs'][0]['name'],
            "song_name_cn": (about['songs'][0].get('tns') or about['songs'][0].get('alia') or [None])[0],
            "song_picUrl": about['songs'][0]['al']['picUrl'],
            "song_alname": about['songs'][0]['al']['name'],
            "song_arname": ', '.join([ar['name'] for ar in about['songs'][0]['ar']])
        }
    except Exception as e:
        return {
            "error": str(e)
        }

@app.post("/api/v2/song")
async def get_full_song(data: GetFullSong):
    try:
        song = NCMusicApi.get_song(data.song_url, data.song_level)
        return song
    except Exception as e:
        return {
            "error": str(e)
        }

@app.get("/api/v2/search")
async def search_songs(search_name: str, limit: int = 10, offset: int = 0, type: int = 1, cover: bool = False):
    try:
        songs = NCMusicApi.search_songs(search_name, limit, offset, type, cover)
        return songs
    except Exception as e:
        return {
            "error": str(e)
        }

# WebUI完善中
# @app.get("/",response_class=HTMLResponse)
# async def index():
#     with open("static/index.html", "r", encoding="utf-8") as f:
#         content = f.read()
#     return HTMLResponse(content=content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2333)