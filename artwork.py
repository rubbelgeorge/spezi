import requests
import re
from bs4 import BeautifulSoup
import argparse

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

    artwork_url = None
    lookup_resp = requests.get(f"https://itunes.apple.com/de/lookup?id={album_id}")
    if lookup_resp.ok:
        results = lookup_resp.json().get("results", [])
        print(results)
        if results:
            artwork_small = results[0].get("artworkUrl100")
            if artwork_small:
                artwork_url = re.sub(r"/\d+x\d+bb", "/3000x3000bb", artwork_small)

    return avc_url, hevc_url, artwork_url

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ambient video and artwork URLs from an iTunes album.")
    parser.add_argument("--album-id", required=True, help="The iTunes album ID.")
    args = parser.parse_args()
    album_id = args.album_id
    avc_url, hevc_url, artwork_url = get_album_video_urls(album_id)
    print(f"\nAVC:{avc_url}")
    print(f"HEVC:{hevc_url}")
    print(f"Artwork:{artwork_url}")