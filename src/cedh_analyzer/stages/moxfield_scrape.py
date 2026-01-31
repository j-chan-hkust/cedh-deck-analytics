"""Stage 2: Scrape individual decklists from Moxfield."""

import asyncio
import csv
import random
import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

from .base import Stage, StageResult
from ..state import save_state
from ..config import SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX, MAX_RETRIES


class MoxfieldScrapeStage(Stage):
    """Scrape individual decklists from Moxfield."""
    
    name = "Moxfield Scrape"
    description = "Downloading decklists from Moxfield"
    
    def is_complete(self) -> bool:
        return self.state.stage_moxfield_complete
    
    async def run(self) -> StageResult:
        """Execute the Moxfield scraping stage."""
        if self.is_complete():
            return StageResult(success=True, message="Already complete")
        
        output_dir = Path(self.state.output_dir)
        csv_file = output_dir / "edh16_scrape.csv"
        deck_lists_dir = output_dir / "deck_lists"
        deck_lists_dir.mkdir(parents=True, exist_ok=True)
        
        if not csv_file.exists():
            return StageResult(
                success=False,
                message="EDH16 scrape data not found. Run stage 1 first.",
            )
        
        # Load deck data
        decks = self._load_deck_data(csv_file)
        if not decks:
            return StageResult(success=False, message="No decks to process")
        
        # Check for already processed decks
        processed = self._get_processed_decks(deck_lists_dir)
        remaining = [d for d in decks if d["deck_id"] not in processed]
        
        total = len(decks)
        already_done = total - len(remaining)
        
        if not remaining:
            self.state.decks_scraped = total
            self.state.stage_moxfield_complete = True
            save_state(self.state)
            return StageResult(
                success=True,
                message=f"All {total} decklists already downloaded",
            )
        
        try:
            scraped = await asyncio.to_thread(
                self._scrape_decklists,
                remaining,
                deck_lists_dir,
                already_done,
                total,
            )
            
            self.state.decks_scraped = already_done + scraped
            self.state.stage_moxfield_complete = True
            save_state(self.state)
            
            return StageResult(
                success=True,
                message=f"Scraped {scraped} new decklists ({self.state.decks_scraped} total)",
            )
            
        except Exception as e:
            save_state(self.state)  # Save progress even on error
            return StageResult(success=False, message=f"Error: {str(e)}")
    
    def _load_deck_data(self, csv_file: Path) -> list[dict]:
        """Load deck data from CSV."""
        decks = []
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("url") and row.get("deck_id"):
                    decks.append(row)
        return decks
    
    def _get_processed_decks(self, deck_lists_dir: Path) -> set[str]:
        """Get set of already processed deck IDs."""
        processed = set()
        for file in deck_lists_dir.glob("*.txt"):
            # Extract deck_id from filename (format: NNN_deck_id.txt)
            parts = file.stem.split("_", 1)
            if len(parts) > 1:
                processed.add(parts[1])
        return processed
    
    def _init_driver(self) -> webdriver.Chrome | None:
        """Initialize a stealth Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options,
            )
            
            stealth(
                driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            return driver
        except Exception:
            return None
    
    def _scrape_decklists(
        self,
        decks: list[dict],
        output_dir: Path,
        already_done: int,
        total: int,
    ) -> int:
        """Scrape decklists using Selenium."""
        driver = self._init_driver()
        if not driver:
            raise RuntimeError("Failed to initialize WebDriver")
        
        scraped = 0
        
        try:
            for idx, deck in enumerate(decks):
                current = already_done + idx + 1
                
                url = deck["url"]
                deck_id = deck["deck_id"]
                filename = f"{current:03d}_{deck_id}.txt"
                output_file = output_dir / filename
                
                if "moxfield" in url:
                    success = self._scrape_moxfield_deck(driver, url, output_file)
                elif "topdeck.gg" in url:
                    success = self._scrape_topdeck_deck(driver, url, output_file)
                else:
                    continue
                
                if success:
                    scraped += 1
                
                # Random delay between requests
                time.sleep(random.uniform(SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX))
        
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        
        return scraped
    
    def _scrape_moxfield_deck(
        self,
        driver: webdriver.Chrome,
        url: str,
        output_file: Path,
    ) -> bool:
        """Scrape a single deck from Moxfield."""
        for retry in range(MAX_RETRIES):
            try:
                driver.get(url)
                
                # Check for error page
                try:
                    driver.find_element(
                        By.XPATH,
                        "//*[contains(text(), 'Page Not Found') or contains(text(), 'does not exist')]",
                    )
                    return False  # Page not found
                except Exception:
                    pass
                
                # Wait for deck header
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "deckheader-name"))
                    )
                except TimeoutException:
                    time.sleep(2)
                
                # Click "More" button
                try:
                    more_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "subheader-more"))
                    )
                    more_button.click()
                    time.sleep(1)
                    
                    # Click "Export"
                    export_options = driver.find_elements(
                        By.XPATH, "//a[contains(text(), 'Export')]"
                    )
                    if export_options:
                        export_options[0].click()
                        time.sleep(1)
                        
                        # Get deck list from textarea
                        text_area = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, "//textarea[contains(@class, 'form-control')]")
                            )
                        )
                        
                        deck_text = text_area.get_attribute("value")
                        
                        if deck_text:
                            with open(output_file, "w", encoding="utf-8") as f:
                                f.write(deck_text)
                            return True
                
                except Exception:
                    pass
                
                if retry < MAX_RETRIES - 1:
                    time.sleep(random.uniform(2, 4))
            
            except WebDriverException:
                if retry < MAX_RETRIES - 1:
                    time.sleep(random.uniform(3, 6))
        
        return False
    
    def _scrape_topdeck_deck(
        self,
        driver: webdriver.Chrome,
        url: str,
        output_file: Path,
    ) -> bool:
        """Scrape a single deck from TopDeck.gg."""
        try:
            driver.get(url)
            content = driver.page_source
            
            res = re.findall(r"(?<=decklistText).+?(?=;)", content, re.DOTALL)
            if not res:
                return False
            
            res = res[0]
            decklist = res.split("Mainboard~~\n")[1].split("\n\n")[0].split("\n")
            commanders = res.split("~~Commanders~~\n")[1].split("\n\n~~Mainboard~~")[0].split("\n")
            decklist.extend(commanders)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(decklist))
            
            return True
        
        except Exception:
            return False
