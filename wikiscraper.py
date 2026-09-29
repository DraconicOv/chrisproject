
import argparse

import requests
from bs4 import BeautifulSoup, NavigableString
import json
import re
from typing import List, Tuple
import requests
import time
import sys
import subprocess

YOUTUBE_SEARCH_URL = "https://www.youtube.com/results"
MAX_RESULTS = 3
COOLDOWN_TIME = 0.5 


def extract_link_or_contents_text(item: BeautifulSoup):
    text = item.find('a').get_text() if item.find('a') else item.get_text()
    return text
    # return re.sub(r"[^\w\s()']+", "", text).strip()

def extract_song_titles(text: str):
    text = re.sub(r"\s*\[\s*\d+\s*\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    matches = re.findall(r"[^,]+?\(\d{4}\)", text)
    if matches:
        return [m.strip() for m in matches]

    return [text]

def check_sibling(sibling):
    # print(sibling)
    if sibling and (sibling.find_all(id="See_also") or  sibling.find_all(id="References")):
        return True

def get_artists_and_songs(url: str) -> Tuple[List[str], List[str]]:
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    songs = []
    artists = []
    container = soup.find('div', class_="mw-content-ltr mw-parser-output")
    for list in container.find_all('ul'):
        if check_sibling(list.find_next_sibling('div')):
            break
        for item in list.find_all('li'):
            if item.find('ul'): # this one has a sub-list, assumedly song names
                for song in item.find('ul').find_all('li'):
                    song = extract_link_or_contents_text(song)
                    songs.extend(extract_song_titles(song))
                    # if the song is actually multiple song names, extract each song. Ain't Nothing Gonna Keep Me From You (1978), The Stuff That Dreams Are Made Of (1978), Moonlight Madness (1979), With You Love (1979)
                continue
            # this item is an artist's name (hopefully)
            artists.append(extract_link_or_contents_text(item))
        if check_sibling(list.find_previous_sibling('div')):
            break
    return (artists, songs)





def _extract_yt_initial_data(html: str) -> dict:
    match = re.search(r"ytInitialData\s*=\s*(\{.*?\});", html, re.DOTALL)
    if not match:
        match = re.search(r"var ytInitialData = (\{.*?\});", html, re.DOTALL)
    if not match:
        print(html)
        raise ValueError("Unable to locate YouTube initial data")
        
    return json.loads(match.group(1))


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def search_by_artist(artist_name: str) -> List[str]:
    query = f"{artist_name} radio songs"
    response = requests.get(
        YOUTUBE_SEARCH_URL,
        params={"search_query": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()

    data = _extract_yt_initial_data(response.text)
    links: List[str] = []
    seen = set()

    for node in _walk(data):
        video_id = node.get("videoId")
        if video_id and video_id not in seen and "title" in node:
            seen.add(video_id)
            links.append(f"https://www.youtube.com/watch?v={video_id}")
            if len(links) == MAX_RESULTS:
                break

    return links

def search_by_song(song) -> List[str]:
    query = f"{song} song"
    response = requests.get(
        YOUTUBE_SEARCH_URL,
        params={"search_query": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()

    data = _extract_yt_initial_data(response.text)
    links: List[str] = []
    seen = set()

    for node in _walk(data):
        video_id = node.get("videoId")
        if video_id and video_id not in seen and "title" in node:
            seen.add(video_id)
            links.append(f"https://www.youtube.com/watch?v={video_id}")

    return links





def main() -> None:
    if (sys.argv.__len__() == 1):
        print("Usage: wikivideopopulator.exe -a article -t timeout")
        return

    parser = argparse.ArgumentParser(description="Scrape a Wikipedia page and download matching YouTube audio.")
    parser.add_argument("-a", "--article", required=True, help="Wikipedia article URL")
    parser.add_argument("-t", "--timeout", type=float, default=COOLDOWN_TIME, help="Delay between requests")
    parsed_args = parser.parse_args()

    article = parsed_args.article
    timeout = parsed_args.timeout
    videos = []
    title = article.split("/wiki/")
    if (len(title) > 1):
        title = title[1].split("#")[0]
        article = f'https://en.wikipedia.org/w/index.php?title={title}&useparsoid=0'
    artists, songs = get_artists_and_songs(article)
    for artist in artists:
        videos.extend(search_by_artist(artist))
        time.sleep(timeout)
    for song in songs:
        videos.extend(search_by_song(song))
        time.sleep(timeout)
    cookie_file = '"C:\\Users\\Chris\\OneDrive\\Documents\\yt-dlp_win\\edge_cookies.txt'
    for video in videos:
        subprocess.run(["powershell", "-Command", f'C:\\Users\\Chris\\OneDrive\\Documents\\yt-dlp_win\\yt-dlp -x --audio-format mp3 --cookies {cookie_file} --embed-thumbnail --add-metadata {video} | Tee-Object -FilePath:C:\\Users\\Chris\\OneDrive\\Documents\\yt-dlp_win\\logmp3.txt -Append'])
    

if __name__ == "__main__":
    main()
