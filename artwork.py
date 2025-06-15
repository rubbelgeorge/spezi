import requests
import re
from bs4 import BeautifulSoup
import argparse
import json

def get_album_video_urls(album_id):
    url = f"https://music.apple.com/de/album/{album_id}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    video_tag = soup.find("amp-ambient-video")
    if not video_tag or "src" not in video_tag.attrs:
        m3u8_url = None
    else:
        m3u8_url = video_tag["src"]

    avc_url = None
    hevc_url = None

    if m3u8_url:
        m3u8_content = requests.get(m3u8_url, headers=headers).text

        max_avc_bw = 0
        max_hevc_bw = 0

        stream_pattern = re.compile(r'#EXT-X-STREAM-INF:(.*?)\n(https://[^\s]+)')
        matches = stream_pattern.findall(m3u8_content)

        for attributes, stream_url in matches:
            resolution_match = re.search(r'RESOLUTION=(\d+x\d+)', attributes)
            codec_match = re.search(r'CODECS="([^"]+)"', attributes)
            bandwidth_match = re.search(r'BANDWIDTH=(\d+)', attributes)
            if resolution_match and codec_match and bandwidth_match:
                resolution = resolution_match.group(1)
                codec = codec_match.group(1)
                bandwidth = int(bandwidth_match.group(1))
                if resolution == "1080x1080" and "avc1" in codec and bandwidth > max_avc_bw:
                    max_avc_bw = bandwidth
                    avc_url = stream_url
                elif resolution == "2160x2160" and "hvc1" in codec and bandwidth > max_hevc_bw:
                    max_hevc_bw = bandwidth
                    hevc_url = stream_url

    # Replaced artwork logic: Bendodson API with dynamic best uncompressed selection
    artwork_url = None
    session = requests.Session()
    bendodson_url = "https://itunesartwork.bendodson.com/api.php"
    params = {
        "query": album_id,
        "entity": "album",
        "country": "de",
        "type": "request"
    }

    try:
        response1 = session.get(bendodson_url, params=params, headers=headers)
        response1.raise_for_status()
        url2 = response1.json()["url"]

        response2 = session.get(url2, headers=headers)
        response2.raise_for_status()

        text = response2.text
        if text.startswith('callback(') and text.endswith(')'):
            text = text[len('callback('):-1]
        apple_data = json.loads(text)

        post_data = {
            "json": json.dumps(apple_data),
            "type": "data",
            "entity": "album"
        }
        response3 = session.post(bendodson_url, data=post_data, headers=headers)
        response3.raise_for_status()
        final_data = response3.json()

        candidates = []
        for result in final_data:
            uncompressed = result.get("uncompressed")
            if uncompressed:
                filename = uncompressed.split('/')[-1]
                candidates.append((len(filename), filename, uncompressed))

        if candidates:
            candidates.sort()
            artwork_url = candidates[0][2]
    except Exception as e:
        print(f"Failed to fetch uncompressed artwork: {e}")

    return avc_url, hevc_url, artwork_url

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ambient video and artwork URLs from an iTunes album.")
    parser.add_argument("--album-id", help="The iTunes album ID.")
    parser.add_argument("--track-id", help="The iTunes track ID to resolve its album.")
    args = parser.parse_args()

    if not args.album_id and not args.track_id:
        parser.error("Either --album-id or --track-id must be provided.")

    if args.track_id:
        track_lookup = requests.get(f"https://itunes.apple.com/lookup?id={args.track_id}")
        if track_lookup.ok:
            results = track_lookup.json().get("results", [])
            if results:
                args.album_id = results[0].get("collectionId")
                print(f"Resolved track ID {args.track_id} to album ID {args.album_id}")
            else:
                print("No album found for given track ID.")
                exit(1)
        else:
            print("Failed to fetch album for track ID.")
            exit(1)

    album_id = args.album_id
    avc_url, hevc_url, artwork_url = get_album_video_urls(album_id)
    print(f"\nAVC:{avc_url}")
    print(f"HEVC:{hevc_url}")
    print(f"Artwork:{artwork_url}")