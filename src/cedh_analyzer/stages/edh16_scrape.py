"""Stage 1: Scrape tournament data from EDHTop16."""

import asyncio
import csv
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from .base import Stage, StageResult
from ..state import AnalysisState, save_state


def extract_deck_id(url: str) -> str | None:
    """Extract deck ID from a Moxfield or TopDeck URL."""
    match = re.search(r"/decks/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    # Fallback for topdeck.gg URLs
    return url.split("/")[-1] if url else None


class EDH16ScrapeStage(Stage):
    """Scrape tournament results from EDHTop16."""
    
    name = "EDH16 Scrape"
    description = "Fetching tournament data from EDHTop16"
    
    def is_complete(self) -> bool:
        return self.state.stage_edh16_complete
    
    async def run(self) -> StageResult:
        """Execute the EDH16 scraping stage."""
        if self.is_complete():
            return StageResult(success=True, message="Already complete")
        
        try:
            data = await asyncio.to_thread(
                self._scrape_edh16, self.state.commander_url
            )
            
            if not data or not data.get("decks"):
                return StageResult(
                    success=False,
                    message="No decks found at the specified URL",
                )
            
            # Save results to CSV
            output_dir = Path(self.state.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "edh16_scrape.csv"
            
            self._save_to_csv(data, output_file)
            
            # Update state
            self.state.commander_name = data["commander"]
            self.state.deck_count = len(data["decks"])
            self.state.stage_edh16_complete = True
            save_state(self.state)
            
            return StageResult(
                success=True,
                message=f"Scraped {len(data['decks'])} decks for {data['commander']}",
                data=data,
            )
            
        except Exception as e:
            return StageResult(success=False, message=f"Error: {str(e)}")
    
    def _scrape_edh16(self, url: str) -> dict:
        """Scrape EDHTop16 page using Selenium."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            time.sleep(3)
            
            # Scroll to load content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Click "Load More" buttons
            load_more_selectors = [
                "//button[contains(text(), 'Load More')]",
                "//button[contains(text(), 'load more')]",
                "//span[contains(text(), 'Load More')]",
            ]
            
            click_count = 0
            max_clicks = 100
            
            while click_count < max_clicks:
                button_found = False
                
                for selector in load_more_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                driver.execute_script(
                                    "arguments[0].scrollIntoView(true);", element
                                )
                                time.sleep(0.5)
                                element.click()
                                click_count += 1
                                button_found = True
                                time.sleep(2)
                                break
                        if button_found:
                            break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                
                if not button_found:
                    break
            
            # Parse the page
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Extract commander name
            title_text = soup.title.text if soup.title else "Unknown Commander"
            commander_name = title_text.split("|")[0].strip()
            
            # Find deck entries
            deck_entries = soup.find_all(
                "div",
                class_=lambda c: c and "group" in c and "relative" in c and "rounded-lg" in c,
            )
            
            decks = []
            for entry in deck_entries:
                deck_link = entry.find("a")
                if not deck_link:
                    continue
                
                deck_url = deck_link.get("href", "").strip()
                deck_id = extract_deck_id(deck_url)
                
                if not deck_id:
                    continue
                
                deck_info = {
                    "commander": commander_name,
                    "deck_id": deck_id,
                    "url": deck_url,
                    "name": "".join(filter(str.isalnum, deck_link.text.strip())),
                }
                
                # Extract tournament name
                tournament_links = entry.find_all("a")
                if len(tournament_links) > 1:
                    deck_info["tournament"] = tournament_links[1].text.strip()
                else:
                    deck_info["tournament"] = ""
                
                # Extract date
                date_span = entry.find("span", class_=lambda c: c and "text-sm" in c)
                deck_info["date"] = date_span.text.strip() if date_span else ""
                
                # Extract placement and record
                placement_div = entry.find("div", class_=lambda c: c and "bottom-0" in c)
                if placement_div:
                    spans = placement_div.find_all("span")
                    
                    if spans:
                        placement_text = spans[0].get_text(strip=True)
                        parts = [p.strip() for p in placement_text.split("/")]
                        if len(parts) >= 2:
                            placement_match = re.search(r"\d+", parts[0])
                            total_match = re.search(r"\d+", parts[1])
                            deck_info["placement"] = placement_match.group() if placement_match else ""
                            deck_info["total_players"] = total_match.group() if total_match else ""
                        else:
                            deck_info["placement"] = ""
                            deck_info["total_players"] = ""
                    
                    if len(spans) > 1:
                        record_text = spans[1].get_text(strip=True)
                        wins = re.search(r"Wins:\s*(\d+)", record_text)
                        losses = re.search(r"Losses:\s*(\d+)", record_text)
                        draws = re.search(r"Draws:\s*(\d+)", record_text)
                        
                        deck_info["wins"] = wins.group(1) if wins else ""
                        deck_info["losses"] = losses.group(1) if losses else ""
                        deck_info["draws"] = draws.group(1) if draws else ""
                    else:
                        deck_info["wins"] = ""
                        deck_info["losses"] = ""
                        deck_info["draws"] = ""
                else:
                    deck_info["placement"] = ""
                    deck_info["total_players"] = ""
                    deck_info["wins"] = ""
                    deck_info["losses"] = ""
                    deck_info["draws"] = ""
                
                decks.append(deck_info)
            
            return {"commander": commander_name, "decks": decks}
        
        finally:
            driver.quit()
    
    def _save_to_csv(self, data: dict, output_file: Path) -> None:
        """Save scraped data to CSV."""
        headers = [
            "commander", "deck_id", "url", "name", "tournament",
            "date", "placement", "total_players", "wins", "losses", "draws",
        ]
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for deck in data["decks"]:
                writer.writerow({h: deck.get(h, "") for h in headers})
