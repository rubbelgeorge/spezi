import requests
import re

def get_apple_artist_image(artist_id, region="us", width=3000, height=3000):
    url = f"https://music.apple.com/{region}/artist/{artist_id}"
    response = requests.get(url)
    html = response.text

    match = re.search(r'<meta property="og:image" content="(https://[^"]+)"', html)
    if not match:
        raise Exception("og:image tag not found")

    og_image = match.group(1)
    # Replace size pattern with desired dimensions and style
    high_res = re.sub(r'[\d]+x[\d]+[a-z]*', f"{width}x{height}cc", og_image)
    return high_res

import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <artist_id>")
        sys.exit(1)
    artist_id_input = sys.argv[1]
    print(get_apple_artist_image(artist_id_input))