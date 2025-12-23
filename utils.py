import os
from datetime import datetime
import re

def create_timestamped_dir(url):
    t = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    path = os.path.join("temp", "folder__" + t)
    os.makedirs(path, exist_ok=True)
    return path

def get_latest_output_dir():
    folders = os.listdir("temp")
    folders.sort()
    return os.path.join("temp", folders[-1])

# Function to extract deck ID from URL
def extract_deck_id(url):
    # Try to match the deck ID pattern in Moxfield URLs
    match = re.search(r'/decks/([a-zA-Z0-9_-]+)', url)
    if match:
        deck_id = match.group(1)
    # default to topdeck.gg pattern
    else:
        deck_id = url.split("/")[-1]
    return deck_id