import sys
import re
import csv
from bs4 import BeautifulSoup

def extract_specific_divs(html_file_path="Magda, Brazen Outlaw _ EDHTop 16.html", output_file_path="edh16_scrape.csv"):
    # Read the HTML file
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
    except FileNotFoundError:
        print(f"Error: File '{html_file_path}' not found.")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all div elements with the specific class
    target_class = "group relative overflow-hidden rounded-lg bg-white shadow transition-shadow cursor-pointer hover:shadow-lg"
    divs = soup.find_all('div', class_=target_class)

    if not divs:
        print("No matching div elements found.")
        return

    # Open CSV file for writing
    with open(output_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        # Define CSV headers
        fieldnames = ['Title', 'Weblink', 'Placement', 'Total Players', 'Wins', 'Losses', 'Draws']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        # Extract and write information from each matching div
        for div in divs:
            # Extract weblink
            link_element = div.find('a')
            weblink = link_element.get('href') if link_element else "No link found"

            # Extract title/name
            title = link_element.text.strip() if link_element else "No title found"

            # Extract placement and number of players
            placement_text = div.find('span', class_="flex-1")
            placement = "Unknown"
            players = "Unknown"

            if placement_text:
                placement_match = re.search(r'(\d+)(?:st|nd|rd|th)', placement_text.text)
                if placement_match:
                    placement = placement_match.group(1)

                players_match = re.search(r'(\d+)\s+players', placement_text.text)
                if players_match:
                    players = players_match.group(1)

            # Extract wins, losses, and draws
            stats_text = div.find_all('span')[-1].text if div.find_all('span') else "No stats found"

            wins = re.search(r'Wins:\s*(\d+)', stats_text)
            wins = wins.group(1) if wins else "Unknown"

            losses = re.search(r'Losses:\s*(\d+)', stats_text)
            losses = losses.group(1) if losses else "Unknown"

            draws = re.search(r'Draws:\s*(\d+)', stats_text)
            draws = draws.group(1) if draws else "Unknown"

            # Write the row to CSV
            writer.writerow({
                'Title': title,
                'Weblink': weblink,
                'Placement': placement,
                'Total Players': players,
                'Wins': wins,
                'Losses': losses,
                'Draws': draws
            })

    print(f"Results have been saved to {output_file_path}")
    print(f"Total results found: {len(divs)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        extract_specific_divs()
    else:
        extract_specific_divs(sys.argv[1])
