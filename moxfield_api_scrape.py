import pandas as pd
import time
import random
import sys
import os
import requests
from urllib.parse import urlparse

def extract_deck_id(url):
    """Extract the deck ID from a Moxfield URL."""
    # Parse the URL
    parsed_url = urlparse(url)

    # The path will be something like /decks/some-deck-id
    path_parts = parsed_url.path.split('/')

    # The deck ID should be the last part of the path
    if len(path_parts) >= 3 and path_parts[1] == 'decks':
        return path_parts[2]

    return None

def scrape_deck_pages(csv_file_path="edh16_scrape.csv", output_dir="deck_lists", export_id="b8c9ef4b-34fe-4ed8-8d4d-9759552b7b3a"):
    """
    Download deck lists using the Moxfield API.

    Args:
        csv_file_path: Path to the CSV file containing deck information
        output_dir: Directory to save the downloaded deck lists
        export_id: The export ID to use in the API request
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # Load the CSV file into a pandas DataFrame
    try:
        df = pd.read_csv(csv_file_path)
        print(f"Successfully loaded {len(df)} records from {csv_file_path}")
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Check if the Weblink column exists
    if 'Weblink' not in df.columns:
        print("Error: CSV file does not contain a 'Weblink' column.")
        return

    # Create a summary file
    summary_file = os.path.join(output_dir, "deck_summary.csv")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("Deck Title,Placement,Total Players,Wins,Losses,Draws,Deck URL,Deck ID,API URL,Download Status\n")

    # Set up a session for making requests
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/plain',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.moxfield.com/',
        'Origin': 'https://www.moxfield.com'
    })

    # Iterate through each URL in the DataFrame
    for index, row in df.iterrows():
        url = row['Weblink']
        title = row['Title']
        placement = row.get('Placement', 'Unknown')
        players = row.get('Total Players', 'Unknown')
        wins = row.get('Wins', 'Unknown')
        losses = row.get('Losses', 'Unknown')
        draws = row.get('Draws', 'Unknown')

        # Create a safe filename from the title
        safe_title = "".join([c if c.isalnum() or c in " -_" else "_" for c in title])
        safe_title = safe_title.strip().replace(' ', '_')
        if len(safe_title) > 100:  # Truncate if too long
            safe_title = safe_title[:100]

        # Add index to ensure uniqueness
        filename = f"{index+1:03d}_{safe_title}"

        # Skip if URL is not valid
        if url == "No link found" or not url.startswith('http'):
            print(f"Skipping invalid URL for entry {index+1}: {url}")
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","","","Skipped - Invalid URL"\n')
            continue

        print(f"\n{'='*80}")
        print(f"Processing entry {index+1}: {title}")
        print(f"URL: {url}")
        print(f"{'='*80}")

        try:
            # Extract the deck ID from the URL
            deck_id = extract_deck_id(url)

            if not deck_id:
                print(f"Could not extract deck ID from URL: {url}")
                with open(summary_file, 'a', encoding='utf-8') as f:
                    f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","","","Failed - Could not extract deck ID"\n')
                continue

            print(f"Extracted deck ID: {deck_id}")

            # Add a random delay to avoid being blocked
            delay = random.uniform(2, 5)
            print(f"Waiting {delay:.2f} seconds before request...")
            time.sleep(delay)

            # Construct the API URL
            api_url = f"https://api.moxfield.com/v2/decks/all/{deck_id}/download?exportId={export_id}&arenaOnly=false"
            print(f"Making API request to: {api_url}")

            # Make the request
            response = session.get(api_url)

            # Check if the request was successful
            if response.status_code == 200:
                # Save the deck list to a file
                output_file_path = os.path.join(output_dir, f"{filename}.txt")
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)

                print(f"Successfully downloaded deck list to: {output_file_path}")

                # Add to summary
                with open(summary_file, 'a', encoding='utf-8') as f:
                    f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","{api_url}","Success"\n')
            else:
                print(f"Failed to download deck list. Status code: {response.status_code}")
                print(f"Response: {response.text}")

                # Add detailed error information to the summary
                error_info = f"Failed - API Status {response.status_code}"
                if response.text:
                    # Truncate and clean the response text for CSV
                    error_text = response.text.replace('"', '""')[:100]
                    error_info += f" - {error_text}"

                with open(summary_file, 'a', encoding='utf-8') as f:
                    f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","{api_url}","{error_info}"\n')

                # Try to diagnose the issue
                if response.status_code == 404:
                    print("Diagnosis: The deck ID might be incorrect or the API endpoint has changed.")
                    print("Checking if deck exists by making a request to the main deck page...")

                    # Try to access the main deck API endpoint
                    check_url = f"https://api.moxfield.com/v2/decks/all/{deck_id}"
                    check_response = session.get(check_url)

                    if check_response.status_code == 200:
                        print(f"Deck exists but download endpoint failed. Export ID might be incorrect: {export_id}")
                    else:
                        print(f"Deck not found at {check_url} (Status: {check_response.status_code})")
                        print("The deck ID might be invalid or the deck might have been removed.")

        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","","","Failed - {str(e)}"\n')

    print(f"\nScraping completed! Results saved to {output_dir} directory")
    print(f"Summary file created at: {summary_file}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        # If both CSV file and export ID are provided
        scrape_deck_pages(sys.argv[1], export_id=sys.argv[2])
    elif len(sys.argv) > 1:
        # If only CSV file is provided
        scrape_deck_pages(sys.argv[1])
    else:
        # Use defaults
        scrape_deck_pages()
