import os
import glob
from collections import Counter

def read_deck_file(file_path):
    """Read a deck file and return a set of unique cards."""
    with open(file_path, 'r') as file:
        # Read all lines and strip whitespace
        cards = [line.strip() for line in file.readlines() if line.strip()]
    return set(cards)

def main():
    """Find cards that appear in all decks, 95% of decks, and 90% of decks."""
    # Get all deck files from the processed_decklists directory
    deck_files = glob.glob("processed_decklists/*.txt")
    total_decks = len(deck_files)

    if total_decks == 0:
        print("No deck files were found.")
        return

    # Read all deck files
    all_decks = []
    card_counter = Counter()

    for file_path in deck_files:
        cards = read_deck_file(file_path)
        print(f"Deck {os.path.basename(file_path)}: {len(cards)} unique cards")
        all_decks.append(cards)

        # Count occurrences of each card
        for card in cards:
            card_counter[card] += 1

    # Calculate thresholds
    threshold_100 = total_decks
    threshold_95 = int(total_decks * 0.95)
    threshold_90 = int(total_decks * 0.90)

    # Find cards that meet each threshold
    cards_100_percent = {card for card, count in card_counter.items() if count >= threshold_100}
    cards_95_percent = {card for card, count in card_counter.items() if count >= threshold_95}
    cards_90_percent = {card for card, count in card_counter.items() if count >= threshold_90}

    # Print results
    print(f"\nAnalyzed {total_decks} decks")

    print(f"\nFound {len(cards_100_percent)} cards that appear in 100% of decks:")
    for card in sorted(cards_100_percent):
        print(f"- {card}")

    print(f"\nFound {len(cards_95_percent)} cards that appear in at least 95% of decks:")
    for card in sorted(cards_95_percent):
        print(f"- {card}")

    print(f"\nFound {len(cards_90_percent)} cards that appear in at least 90% of decks:")
    for card in sorted(cards_90_percent):
        print(f"- {card}")

    # Save results to files
    with open("cards_100_percent.txt", "w") as f:
        for card in sorted(cards_100_percent):
            f.write(f"{card}\n")

    with open("cards_95_percent.txt", "w") as f:
        for card in sorted(cards_95_percent):
            f.write(f"{card}\n")

    with open("cards_90_percent.txt", "w") as f:
        for card in sorted(cards_90_percent):
            f.write(f"{card}\n")

    print(f"\nResults saved to cards_100_percent.txt, cards_95_percent.txt, and cards_90_percent.txt")

if __name__ == "__main__":
    main()
