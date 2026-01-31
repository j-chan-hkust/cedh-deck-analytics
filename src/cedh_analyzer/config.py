"""Configuration and constants for the cEDH Analyzer."""

from pathlib import Path

# Application info
APP_NAME = "cEDH Analyzer"
APP_VERSION = "2.0.0"

# Default commander URL (popular cEDH commander)
DEFAULT_COMMANDER_URL = (
    "https://edhtop16.com/commander/Kinnan%2C%20Bonder%20Prodigy"
    "?timePeriod=ONE_MONTH&minEventSize=100"
)

# Data directories
DATA_DIR = Path(".cedh_data")
STATE_FILE = DATA_DIR / "state.json"

# Tag categories
TAGS = {
    "core": "#1_core",           # 100% usage
    "essential": "#2_essential", # 95-99% usage
    "common": "#3_common",       # 90-94% usage
    "high_spice": "#4_high_spice",     # <3 appearances, top performers
    "medium_spice": "#5_medium_spice", # 3-10 appearances, top performers
    "low_spice": "#6_low_spice",       # >10 appearances, top performers
    "potential_traps": "#7_potential_traps",  # High appearance, low performance
    "bad_cards": "#8_bad_cards",  # Bottom performers
}

# Analysis thresholds
CORE_THRESHOLD = 99        # % for core cards
ESSENTIAL_THRESHOLD = 95   # % for essential cards
COMMON_THRESHOLD = 90      # % for common cards
HIGH_SPICE_COUNT = 3       # Max appearances for high spice
MEDIUM_SPICE_COUNT = 10    # Max appearances for medium spice

# Scraping settings
SCRAPE_DELAY_MIN = 2.0     # Minimum delay between requests
SCRAPE_DELAY_MAX = 5.0     # Maximum delay between requests
MAX_RETRIES = 3            # Max retries for failed requests
PAGE_LOAD_TIMEOUT = 30     # Seconds to wait for page load
