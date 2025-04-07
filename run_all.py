import subprocess

#todo automatically run all

scripts = [
    "1_edh16_scrape.py",
    "2_moxfield_scrape.py",
    "3_deck_preprocessing.py",
    "4_basic_decklist_analytics.py",
    "5_winrate_based_analytics.py"
]

if __name__ == "__main__":
    #todo: automatically initialize the scripts, so I don't need to type this out. Just look for scripts that are in the same directory
    for script in scripts:
        subprocess.run(["python", script], check=True)
