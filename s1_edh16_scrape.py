import os
import re
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from utils import create_timestamped_dir, extract_deck_id

#todo improve the user input experience - automatically prompt the user for the weblink, or read the weblink from a config file
#todo update the code to upload all files into their own new directory - no need to faff around rearranging stuff
def scrape_edhtop16(url):
    # Set up Selenium with Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Load the page
        print(f"Loading URL: {url}")
        driver.get(url)
        time.sleep(3)  # Give initial page time to load

        # First, scroll down to ensure all initial content is loaded
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Try different selectors for the "Load More" button
        load_more_selectors = [
            "//button[contains(text(), 'Load More')]",
            "//button[contains(text(), 'load more')]",
            "//a[contains(text(), 'Load More')]",
            "//div[contains(@class, 'load-more')]",
            "//button[contains(@class, 'load')]",
            "//button[contains(@id, 'load')]",
            "//span[contains(text(), 'Load More')]"
        ]

        # Keep clicking "Load More" until it's no longer available
        click_count = 0
        max_attempts = 100  # Increased limit to ensure we get all content

        while click_count < max_attempts:
            button_found = False

            # Try each selector
            for selector in load_more_selectors:
                try:
                    # Find all matching elements
                    elements = driver.find_elements(By.XPATH, selector)

                    # Try each element that matches the selector
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(1)
                            element.click()
                            print(f"Clicked 'Load More' button ({click_count + 1})")
                            click_count += 1
                            button_found = True
                            time.sleep(3)  # Wait for content to load
                            break

                    if button_found:
                        break

                except (NoSuchElementException, StaleElementReferenceException) as e:
                    continue

            if not button_found:
                print("No more 'Load More' buttons found.")
                break

        print(f"Loaded all content after {click_count} clicks")

        # Get the fully loaded page source
        html_content = driver.page_source

        # Now use BeautifulSoup to parse the content
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract the commander name from the title
        title_text = soup.title.text
        commander_name = title_text.split('|')[0].strip()

        # Find all deck entries using the correct class structure
        deck_entries = soup.find_all('div', class_='group relative overflow-hidden rounded-lg bg-white shadow-sm transition-shadow cursor-pointer hover:shadow-lg')
        print(f"Found {len(deck_entries)} deck entries")

        decks = []
        for entry in deck_entries:
            # Extract deck name and URL (from the first <a> tag)
            deck_link = entry.find('a')
            if not deck_link:
                continue

            url = deck_link['href'].strip() #you have to do this because they sometimes make a small typo and add a space!!

            deck_id = extract_deck_id(url)

            # Skip if not a valid Moxfield URL
            if "moxfield.com" in url and not deck_id:
                continue

            # Create deck info dictionary with the required fields
            deck_info = {
                'commander': commander_name,
                'deck_id': deck_id,
                'url': url,
                'name': ''.join(filter(str.isalnum, deck_link.text.strip())) #leave only alphanumerics to filter out emojis and other nonsense
            }

            # Extract tournament name (from the second <a> tag)
            tournament_link = entry.find_all('a')
            if len(tournament_link) > 1:
                deck_info['tournament'] = tournament_link[1].text.strip()
            else:
                deck_info['tournament'] = ""

            # Extract date
            date_span = entry.find('span', class_='line-clamp-1 text-sm opacity-70')
            if date_span:
                deck_info['date'] = date_span.text.strip()
            else:
                deck_info['date'] = ""

            # Extract placement info from the div with class "absolute bottom-0"
            # Extract placement info from the div with class "absolute bottom-0"
            placement_div = entry.find('div', class_='bottom-0')
            if placement_div:
                # Find both spans within the flex container
                spans = placement_div.find_all('span')

                # First span contains placement info
                if len(spans) > 0:
                    placement_text = spans[0].get_text(strip=True)
                    # Handle "4th / 63 players" format
                    parts = [p.strip() for p in placement_text.split('/')]
                    if len(parts) >= 2:
                        # Extract placement number (remove ordinal suffix)
                        placement = re.search(r'\d+', parts[0]).group() if re.search(r'\d+', parts[0]) else ""
                        # Extract total players
                        total_players = re.search(r'\d+', parts[1]).group() if re.search(r'\d+', parts[1]) else ""

                        deck_info['placement'] = placement
                        deck_info['total_players'] = total_players

                # Second span contains win/loss record
                if len(spans) > 1:
                    record_text = spans[1].get_text(strip=True)
                    # Handle "Wins: 2 / Losses: 3 / Draws: 0" format
                    wins = re.search(r'Wins:\s*(\d+)', record_text)
                    losses = re.search(r'Losses:\s*(\d+)', record_text)
                    draws = re.search(r'Draws:\s*(\d+)', record_text)

                    deck_info['wins'] = wins.group(1) if wins else ""
                    deck_info['losses'] = losses.group(1) if losses else ""
                    deck_info['draws'] = draws.group(1) if draws else ""
            else:
                deck_info['placement'] = ''
                deck_info['total_players'] = ''
                deck_info['wins'] = ""
                deck_info['losses'] = ""
                deck_info['draws'] = ""

            # Debug output
            print(f"Deck: {deck_info['name']}")
            print(f"  Placement: {deck_info['placement']} / {deck_info['total_players']}")
            print(f"  Record: W{deck_info['wins']} L{deck_info['losses']} D{deck_info['draws']}")

            decks.append(deck_info)

        return {
            'commander': commander_name,
            'decks': decks
        }

    finally:
        # Always close the driver
        driver.quit()

def main(url):

    # Scrape the data
    data = scrape_edhtop16(url)

    # Define CSV headers based on the expected columns
    headers = [
        'commander', 'deck_id', 'url', 'name', 'tournament',
        'date', 'placement', 'total_players', 'wins', 'losses', 'draws'
    ]

    # Create timestamped output directory and save CSV
    output_dir = create_timestamped_dir(url)
    output_file = os.path.join(output_dir, "edh16_scrape.csv")

    # Always write a new file (overwrite mode)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        # Write header
        f.write(','.join(headers) + '\n')

        # Write data rows
        for deck in data['decks']:
            row = [
                deck.get('commander', ''),
                deck.get('deck_id', ''),
                deck.get('url', ''),
                deck.get('name', ''),
                deck.get('tournament', ''),
                deck.get('date', ''),
                deck.get('placement', ''),
                deck.get('total_players', ''),
                deck.get('wins', ''),
                deck.get('losses', ''),
                deck.get('draws', '')
            ]
            f.write(','.join([str(item).replace(',', ' ') for item in row]) + '\n')

    print(f"Scraped {len(data['decks'])} decks for {data['commander']}")
    print(f"Data saved to {output_file}")
