import pandas as pd
import time
import random
import sys
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException, InvalidSessionIdException
from selenium_stealth import stealth

def scrape_deck_pages(csv_file_path="edh16_scrape.csv", output_dir="deck_lists"):
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

    # Create or load summary file
    summary_file = os.path.join(output_dir, "deck_summary.csv")

    # Check for existing summary file to determine already processed decks
    processed_urls = set()
    if os.path.exists(summary_file):
        try:
            summary_df = pd.read_csv(summary_file)
            # Extract URLs of successfully processed decks
            successful_entries = summary_df[summary_df['Download Status'] == 'Success']
            processed_urls = set(successful_entries['Deck URL'].tolist())
            print(f"Found {len(processed_urls)} already successfully processed decks")
        except Exception as e:
            print(f"Error reading existing summary file: {e}")
            # Create a new summary file if there was an error reading the existing one
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("Deck Title,Placement,Total Players,Wins,Losses,Draws,Deck URL,Deck ID,Download Status\n")
    else:
        # Create a new summary file if it doesn't exist
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("Deck Title,Placement,Total Players,Wins,Losses,Draws,Deck URL,Deck ID,Download Status\n")

    # Function to initialize the WebDriver
    def init_driver():
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

            # Apply stealth settings
            stealth(driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
            )

            # Additional anti-detection measures
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("WebDriver initialized with stealth settings")
            return driver
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            return None

    # Function to extract deck ID from URL
    def extract_deck_id(url):
        # Try to match the deck ID pattern in Moxfield URLs
        match = re.search(r'/decks/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        return None

    # Initialize the WebDriver
    driver = init_driver()
    if not driver:
        return

    # Iterate through each URL in the DataFrame
    for index, row in df.iterrows():
        url = row['Weblink']
        title = row['Title']
        placement = row.get('Placement', 'Unknown')
        players = row.get('Total Players', 'Unknown')
        wins = row.get('Wins', 'Unknown')
        losses = row.get('Losses', 'Unknown')
        draws = row.get('Draws', 'Unknown')

        # Extract deck ID from URL
        deck_id = extract_deck_id(url)
        if not deck_id:
            print(f"Could not extract deck ID from URL: {url}")
            deck_id = f"unknown_id_{index+1}"

        # Create filename using index and deck ID
        filename = f"{index+1:03d}_{deck_id}"
        output_file_path = os.path.join(output_dir, f"{filename}.txt")

        # Skip if URL is not valid
        if url == "No link found" or not url.startswith('http'):
            print(f"Skipping invalid URL for entry {index+1}: {url}")
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","Skipped - Invalid URL"\n')
            continue

        # Skip if already successfully processed
        if url in processed_urls or os.path.exists(output_file_path):
            print(f"Skipping already processed URL for entry {index+1}: {url}")
            continue

        print(f"\n{'='*80}")
        print(f"Processing entry {index+1}/{len(df)}: {title}")
        print(f"URL: {url}")
        print(f"Deck ID: {deck_id}")
        print(f"{'='*80}")

        max_retries = 3
        for retry in range(max_retries):
            try:
                # Check if driver is still valid, reinitialize if needed
                try:
                    # Simple test to see if driver is still responsive
                    driver.title
                except (WebDriverException, SessionNotCreatedException, InvalidSessionIdException):
                    print("WebDriver session is invalid. Reinitializing...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = init_driver()
                    if not driver:
                        print("Failed to reinitialize WebDriver. Exiting.")
                        return

                # Add a random delay to avoid being blocked
                delay = random.uniform(5, 10)
                print(f"Waiting {delay:.2f} seconds before request...")
                time.sleep(delay)

                # Load the page
                print(f"Navigating to {url}...")
                driver.get(url)

                # Wait for content to load
                print("Waiting for page content to load...")
                try:
                    # Wait up to 45 seconds for the deck name to appear
                    WebDriverWait(driver, 45).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "deckheader-name"))
                    )
                    print("Content loaded successfully!")
                except Exception as e:
                    print(f"Timeout waiting for content to load: {e}")
                    # Try waiting a bit more
                    time.sleep(7)

                # Look for the "More" button and click it
                try:
                    more_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "subheader-more"))
                    )
                    more_button.click()
                    print("Clicked on 'More' button")
                    time.sleep(2)  # Wait for dropdown to appear

                    # Look for the Export option in the dropdown
                    export_options = driver.find_elements(By.XPATH, "//a[contains(text(), 'Export')]")
                    if export_options:
                        export_options[0].click()
                        print("Clicked on 'Export' option")
                        time.sleep(2)  # Wait for the export modal to appear

                        # Wait for the text area to be populated
                        try:
                            text_area = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//textarea[contains(@class, 'form-control')]"))
                            )

                            # Get the deck list text
                            deck_list_text = text_area.get_attribute('value')

                            if deck_list_text:
                                # Save the text to a file
                                with open(output_file_path, 'w', encoding='utf-8') as f:
                                    f.write(deck_list_text)

                                print(f"Saved deck list to: {output_file_path}")

                                # Add to summary
                                with open(summary_file, 'a', encoding='utf-8') as f:
                                    f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","Success"\n')

                                # Add to processed URLs
                                processed_urls.add(url)

                                # Break out of retry loop on success
                                break
                            else:
                                print("Text area was empty")
                                if retry == max_retries - 1:  # Only write to summary on last retry
                                    with open(summary_file, 'a', encoding='utf-8') as f:
                                        f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","Failed - Empty text area"\n')

                        except Exception as e:
                            print(f"Error extracting deck list text: {e}")
                            if retry == max_retries - 1:  # Only write to summary on last retry
                                with open(summary_file, 'a', encoding='utf-8') as f:
                                    f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","Failed - Could not extract text"\n')

                        # Close the modal if it's still open
                        try:
                            close_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-close')]")
                            if close_buttons:
                                close_buttons[0].click()
                                print("Closed the export modal")
                        except:
                            pass
                    else:
                        print("Could not find 'Export' option in dropdown")
                        if retry == max_retries - 1:  # Only write to summary on last retry
                            with open(summary_file, 'a', encoding='utf-8') as f:
                                f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","Failed - No Export option"\n')

                except Exception as e:
                    print(f"Error trying to export deck list: {e}")
                    if retry == max_retries - 1:  # Only write to summary on last retry
                        with open(summary_file, 'a', encoding='utf-8') as f:
                            f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","Failed - {str(e)}"\n')

                print(f"\nFinished processing {url}")

            except (WebDriverException, SessionNotCreatedException, InvalidSessionIdException) as e:
                print(f"WebDriver error on retry {retry+1}/{max_retries}: {e}")
                try:
                    driver.quit()
                except:
                    pass

                # Reinitialize the driver
                print("Reinitializing WebDriver...")
                driver = init_driver()
                if not driver:
                    print("Failed to reinitialize WebDriver. Exiting.")
                    return

                # Wait a bit longer before retrying
                time.sleep(random.uniform(10, 15))

                if retry == max_retries - 1:  # Only write to summary on last retry
                    with open(summary_file, 'a', encoding='utf-8') as f:
                        f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","Failed - WebDriver error"\n')

            except Exception as e:
                print(f"Error processing URL {url} on retry {retry+1}/{max_retries}: {e}")
                if retry == max_retries - 1:  # Only write to summary on last retry
                    with open(summary_file, 'a', encoding='utf-8') as f:
                        f.write(f'"{title}",{placement},{players},{wins},{losses},{draws},"{url}","{deck_id}","Failed - General error"\n')

                # Wait before retrying
                time.sleep(random.uniform(7, 12))

    # Close the WebDriver
    try:
        driver.quit()
    except:
        pass

    print(f"\nScraping completed! Results saved to {output_dir} directory")
    print(f"Summary file created at: {summary_file}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        scrape_deck_pages(sys.argv[1])
    else:
        scrape_deck_pages()
