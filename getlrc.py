import os
import json
import requests
import argparse
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import xml.dom.minidom

def debug_print(title, data):
    """Print debug information in a formatted way"""
    print(f"\n{'='*20} {title} {'='*20}")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)
    print('='*60)

def get_access_token():
    """Get Apple Music access token"""
    response = requests.get('https://music.apple.com/us/browse')
    if response.status_code != 200:
        raise Exception("Failed to get music.apple.com! Please re-try...")

    import re
    indexJs = re.search('(?<=index)(.*?)(?=\.js")', response.text).group(1)
    debug_print("Found index.js", indexJs)
    
    response = requests.get(f'https://music.apple.com/assets/index{indexJs}.js')
    if response.status_code != 200:
        raise Exception("Failed to get js library! Please re-try...")

    accessToken = re.search('(?=eyJh)(.*?)(?=")', response.text).group(1)
    debug_print("Access Token", accessToken[:20] + "..." + accessToken[-20:])
    return accessToken

def parse_url(url):
    """Parse and validate Apple Music URL"""
    if not url.startswith('http'):
        url = f"https://{url}"

    try:
        urlopen(url)
    except (URLError, HTTPError):
        raise Exception("Invalid URL!")

    parsed = urlparse(url)
    if parsed.netloc != "music.apple.com":
        raise Exception("Not an Apple Music URL!")

    splits = url.split('/')
    id = splits[-1]
    kind = splits[4]

    if kind == "album":
        if len(id.split('?i=')) > 1:
            id = id.split('?i=')[1]
            kind = "song"

    debug_print("Parsed URL", {"kind": kind, "id": id})
    return kind, id

def get_lyrics(url, media_user_token):
    """Get lyrics from Apple Music"""
    # Get access token
    access_token = get_access_token()
    
    # Parse URL
    kind, id = parse_url(url)
    
    # Setup session
    session = requests.Session()
    session.headers = {
        'content-type': 'application/json;charset=utf-8',
        'authorization': f'Bearer {access_token}',
        'media-user-token': media_user_token,
        'accept': 'application/json',
        'origin': 'https://music.apple.com',
        'referer': 'https://music.apple.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    debug_print("Request Headers", session.headers)

    # Get storefront info
    response = session.get("https://amp-api.music.apple.com/v1/me/storefront")
    debug_print("Storefront Response Status", response.status_code)
    if response.status_code != 200:
        debug_print("Storefront Error Response", response.text)
        raise Exception("Invalid media-user-token!")
    
    storefront_data = response.json()
    debug_print("Storefront Data", storefront_data)
    
    storefront = storefront_data["data"][0]["id"]
    language = storefront_data["data"][0]["attributes"]["defaultLanguageTag"]
    
    # Get song/album info
    api_url = f'https://amp-api.music.apple.com/v1/catalog/{storefront}/{kind}s/{id}'
    session.params = {
        'include[songs]': 'albums,lyrics,syllable-lyrics',
        'l': language
    }
    debug_print("API Request URL", api_url)
    debug_print("API Request Params", session.params)
    
    response = session.get(api_url)
    debug_print("API Response Status", response.status_code)
    if response.status_code != 200:
        debug_print("API Error Response", response.text)
        raise Exception("Failed to get lyrics!")
        
    data = response.json()
    debug_print("API Response Data", data)
    
    if "errors" in data:
        debug_print("API Errors", data["errors"])
        raise Exception(f"API Error: {data['errors'][0]['detail']}")
        
    return data

def parse_ttml(ttml_content):
    """Parse TTML content and convert to LRC format"""
    try:
        # Parse the TTML content
        root = ET.fromstring(ttml_content)
        
        # Define the TTML namespace
        ns = {'ttml': 'http://www.w3.org/ns/ttml'}
        
        # Get all p elements (paragraphs) which contain the lyrics
        lyrics = []
        for p in root.findall('.//ttml:p', ns):
            # Get the begin time
            begin = p.get('begin')
            # Convert time format from seconds to [mm:ss.xx]
            if begin:
                try:
                    # Handle different time formats
                    if ':' in begin:
                        # Format: mm:ss.xxx
                        minutes, seconds = begin.split(':')
                        total_seconds = float(minutes) * 60 + float(seconds)
                    else:
                        # Format: ss.xxx
                        total_seconds = float(begin)
                    
                    minutes = int(total_seconds // 60)
                    seconds = total_seconds % 60
                    time_str = f"[{minutes:02d}:{seconds:06.3f}]"
                except ValueError:
                    time_str = "[00:00.000]"
            else:
                time_str = "[00:00.000]"
            
            # Get the text content
            text = ''.join(p.itertext()).strip()
            if text:
                lyrics.append(f"{time_str}{text}")
        
        return lyrics
    except Exception as e:
        debug_print("TTML Parse Error", str(e))
        return []

def format_xml(xml_string):
    """Format XML string with proper indentation"""
    try:
        # Parse the XML string
        root = ET.fromstring(xml_string)
        
        # Convert to string with proper formatting
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = xml.dom.minidom.parseString(rough_string)
        
        # Get formatted string with proper indentation
        return reparsed.toprettyxml(indent="  ")
    except Exception as e:
        print(f"Warning: Could not format XML: {e}")
        return xml_string

def save_lyrics(data, output_file):
    """Save lyrics to file"""
    if "data" not in data:
        debug_print("No Data Found", "The response doesn't contain a 'data' field")
        raise Exception("No data found in response!")
        
    # Extract lyrics
    lyrics = []
    ttml_content = None
    
    if "data" in data:
        debug_print("Data Structure", "Found 'data' field in response")
        if isinstance(data["data"], list):
            debug_print("Data Type", "Response data is a list (album)")
            # Album
            for song in data["data"]:
                debug_print("Processing Song", song.get("id", "unknown"))
                if "relationships" in song:
                    debug_print("Song Relationships", song["relationships"].keys())
                    if "lyrics" in song["relationships"]:
                        lyric_data = song["relationships"]["lyrics"]["data"][0]
                        if "attributes" in lyric_data and "ttml" in lyric_data["attributes"]:
                            ttml_content = lyric_data["attributes"]["ttml"]
                            lyrics.extend(parse_ttml(ttml_content))
        else:
            debug_print("Data Type", "Response data is an object (single song)")
            # Single song
            if "relationships" in data["data"]:
                debug_print("Song Relationships", data["data"]["relationships"].keys())
                if "lyrics" in data["data"]["relationships"]:
                    lyric_data = data["data"]["relationships"]["lyrics"]["data"][0]
                    if "attributes" in lyric_data and "ttml" in lyric_data["attributes"]:
                        ttml_content = lyric_data["attributes"]["ttml"]
                        lyrics.extend(parse_ttml(ttml_content))
    
    if not lyrics:
        debug_print("No Lyrics", "No lyrics were found in the response")
        raise Exception("No lyrics found!")
    
    # Save LRC format
    lrc_file = output_file if output_file.endswith('.lrc') else f"{output_file}.lrc"
    with open(lrc_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lyrics))
    print(f"LRC lyrics saved to {lrc_file}")
    
    # Save TTML format
    if ttml_content:
        ttml_file = output_file.replace('.lrc', '.ttml') if output_file.endswith('.lrc') else f"{output_file}.ttml"
        with open(ttml_file, 'w', encoding='utf-8') as f:
            f.write(format_xml(ttml_content))
        print(f"TTML lyrics saved to {ttml_file}")

def main():
    parser = argparse.ArgumentParser(description="Simple Apple Music Lyrics Downloader")
    parser.add_argument('url', help="Apple Music URL for a song")
    parser.add_argument('--token', required=True, help="Your Apple Music media-user-token")
    parser.add_argument('--output', '-o', default='lyrics.lrc', help="Output file name (default: lyrics.lrc)")
    
    args = parser.parse_args()
    
    try:
        data = get_lyrics(args.url, args.token)
        save_lyrics(data, args.output)
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 