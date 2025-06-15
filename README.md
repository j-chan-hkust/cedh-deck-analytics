# cEDH decklist Analysis Tool

This tool helps analyze competitive EDH (cEDH) decklists. It scrapes tournament data from EDHTop16, fetches detailed decklists from Moxfield, and performs various analytics to help you understand card choices and deck construction trends.

## Prerequisites

- Python 3.8 or higher
- Chrome browser installed (for Selenium web scraping)
- Required Python packages (install using `pip install -r requirements.txt`)

## Installation

1. Clone this repository

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure you have Chrome browser installed on your system.

## Usage

### 1. Update the EDHTop16 URL

Edit the `1_edh16_scrape.py` file to set the URL of the EDHTop16 page you want to analyze. Look for the `url` variable in the `main()` function (around line 125) and update it with your desired URL. For example:

```python
url = "https://edhtop16.com/commander/Magda%2C%20Brazen%20Outlaw?timePeriod=THREE_MONTHS"
```

### 2. Run the Analysis

Execute the main runner script to perform the complete analysis:

```bash
python run_all.py
```

This will run all the relevant scripts.

### 3. View Results

The final output will be saved in `tagged_cards.txt`. Copy and paste the text directly into Moxfield to see the deck list. When importing to Moxfield, make sure to group by tag to see the categorized cards.

#### Tag Categories:

1. **Core and Essential Cards**
   - `#1_core`: Cards present in 100% of decks
   - `#2_essential`: Cards present in 95-99% of decks
   - `#3_common`: Cards present in 90-94% of decks

2. **Spice Cards (Tech Choices)**
   - `#4_high_spice`: Cards appearing in fewer than 3 decks (rare/experimental choices)
   - `#5_medium_spice`: Cards appearing in 3-10 decks (moderately played tech)
   - `#6_low_spice`: Cards appearing in more than 10 decks (established tech choices)

3. **Cautionary Tags**
   - `#7_potential_traps`: Cards that appear frequently but may not be optimal
   - `#8_bad_cards`: Cards that appear in the bottom 20% of win rates

## Requirements

The following Python packages are required (automatically installed via `requirements.txt`):

- beautifulsoup4
- selenium
- pandas
- webdriver-manager
- selenium-stealth
- numpy
- matplotlib
- requests
