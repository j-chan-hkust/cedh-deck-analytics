import os
import sys
import glob
import re
from collections import Counter
from utils import get_latest_output_dir

def analyze_card_usage(input_dir=None, output_file=None):
    """
    Analyze the usage rate of cards across deck lists and output a single file
    with cards tagged based on their usage percentage:
    - 100% usage: #1_core
    - 95% usage: #2_essential
    - 90% usage: #3_common

    For cards with numbered suffixes (e.g., mountain1, mountain2), combine them
    and show the total count in the output.

    If no directories are specified, uses the most recent timestamped directory.

    Args:
        input_dir: Directory containing the processed deck list files
        output_file: File where tagged cards will be saved
    """
    # Find the latest output directory if not specified
    if input_dir is None:
        base_dir = get_latest_output_dir()
        if base_dir is None:
            print("Error: No timestamped directory found. Please run previous scripts first.")
            return
        input_dir = os.path.join(base_dir, "processed_decklists")

    if output_file is None:
        base_dir = base_dir if 'base_dir' in locals() else os.path.dirname(os.path.dirname(os.path.abspath(input_dir)))
        output_file = os.path.join(base_dir, "tagged_cards.txt")

    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        return

    print(f"Analyzing files from: {input_dir}")
    print(f"Saving results to: {output_file}")

    # Get all text files in the input directory
    deck_files = glob.glob(os.path.join(input_dir, "*.txt"))
    print(f"Found {len(deck_files)} processed deck list files to analyze")

    if not deck_files:
        print("No deck files found to analyze.")
        return

    # Count cards across all decks
    card_counts = Counter()
    total_decks = len(deck_files)

    # Process each deck file
    for file_path in deck_files:
        file_name = os.path.basename(file_path)
        print(f"Analyzing: {file_name}")

        try:
            # Read the deck list file
            with open(file_path, 'r', encoding='utf-8') as f:
                cards = [line.strip() for line in f if line.strip()]

            #todo this doesn't work quite right at the moment

            # Normalize card names (remove numeric suffixes) and count unique base cards
            base_cards = set()
            for card in cards:
                # Extract the base card name (remove numeric suffix)
                base_card = re.sub(r'(\d+)$', '', card)
                base_cards.add(base_card)

            # Count each unique base card once per deck
            for card in base_cards:
                card_counts[card] += 1

        except Exception as e:
            print(f"  Error analyzing {file_name}: {e}")

    print(f"\nAnalyzed {total_decks} decks with {len(card_counts)} unique cards")

    # Count how many of each card appears in each deck
    card_quantities = {}
    for file_path in deck_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cards = [line.strip() for line in f if line.strip()]

            # Count cards in this deck
            deck_card_counts = Counter()
            for card in cards:
                base_card = re.sub(r'(\d+)$', '', card)
                deck_card_counts[base_card] += 1

            # Update the maximum count for each card
            for card, count in deck_card_counts.items():
                if card not in card_quantities or count > card_quantities[card]:
                    card_quantities[card] = count

        except Exception as e:
            print(f"  Error counting quantities in {os.path.basename(file_path)}: {e}")

    # Calculate usage percentages and assign tags
    tagged_cards = []
    for card, count in card_counts.items():
        usage_percent = (count / total_decks) * 100
        quantity = card_quantities.get(card, 1)

        if usage_percent >= 99:
            tagged_cards.append((card, quantity, usage_percent, "#1_core"))
        elif usage_percent >= 95:
            tagged_cards.append((card, quantity, usage_percent, "#2_essential"))
        elif usage_percent >= 90:
            tagged_cards.append((card, quantity, usage_percent, "#3_common"))

    # Sort cards by usage percentage (highest first)
    tagged_cards.sort(key=lambda x: x[2], reverse=True)

    # Write results to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for card, quantity, _, tag in tagged_cards:
            f.write(f"{quantity} {card} {tag}\n")

    # Print summary
    print(f"\nTagged cards summary:")
    print(f"  #1_core cards (100% usage): {sum(1 for _, _, _, tag in tagged_cards if tag == '#1_core')}")
    print(f"  #2_essential cards (95-99% usage): {sum(1 for _, _, _, tag in tagged_cards if tag == '#2_essential')}")
    print(f"  #3_common cards (90-94% usage): {sum(1 for _, _, _, tag in tagged_cards if tag == '#3_common')}")
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        analyze_card_usage(sys.argv[1], sys.argv[2])
    elif len(sys.argv) > 1:
        analyze_card_usage(sys.argv[1])
    else:
        analyze_card_usage()
