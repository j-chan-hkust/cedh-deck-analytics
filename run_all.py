from s1_edh16_scrape import main as m1
from s2_moxfield_scrape import scrape_deck_pages
from s3_deck_preprocessing import preprocess_decklists
from s4_basic_decklist_analytics import analyze_card_usage
from s5_winrate_based_analytics import main as m5

# user input
############################################################################
edh_top16_link = "https://edhtop16.com/commander/The%20Gitrog%20Monster?timePeriod=ONE_MONTH&minEventSize=100"
# edh_top16_link = "https://edhtop16.com/commander/Kraum%2C%20Ludevic's%20Opus%20%2F%20Tymna%20the%20Weaver?timePeriod=ONE_MONTH&minEventSize=100"
############################################################################


m1(edh_top16_link)
scrape_deck_pages()
preprocess_decklists()
analyze_card_usage()
m5()
