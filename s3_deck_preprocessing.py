import os
import re
import sys
import glob
from utils import get_latest_output_dir

def preprocess_decklists(input_dir=None, output_dir=None):
    """
    Preprocess deck list text files to extract just the card names.
    For cards with multiple copies, create entries like card_name1, card_name2, etc.
    Stop processing when reaching the sideboard or stickers section.

    If no directories are specified, uses the most recent timestamped directory.

    Args:
        input_dir: Directory containing the raw deck list text files
        output_dir: Directory where processed files will be saved
    """
    # Find the latest output directory if not specified
    if input_dir is None:
        base_dir = get_latest_output_dir()
        if base_dir is None:
            print("Error: No timestamped directory found. Please run 1_edh16_scrape.py first.")
            return
        input_dir = os.path.join(base_dir, "deck_lists")

    if output_dir is None:
        base_dir = base_dir if 'base_dir' in locals() else os.path.dirname(os.path.dirname(os.path.abspath(input_dir)))
        output_dir = os.path.join(base_dir, "processed_decklists")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Processing files from: {input_dir}")
    print(f"Saving processed files to: {output_dir}")

    # Get all text files in the input directory
    deck_files = glob.glob(os.path.join(input_dir, "*.txt"))
    print(f"Found {len(deck_files)} deck list files to process")

    # Process each deck file
    for file_path in deck_files:
        file_name = os.path.basename(file_path)
        output_path = os.path.join(output_dir, file_name)

        print(f"Processing: {file_name}")

        try:
            # Read the deck list file
            with open(file_path, 'r', encoding='utf-8') as f:
                deck_text = f.read()

            # Extract card entries
            processed_cards = []
            card_counts = {}  # Track how many of each card we've seen

            # Split the text into lines and process each line
            for line in deck_text.splitlines():
                line = line.strip()

                # Skip empty lines or comment lines
                if not line or line.startswith('//') or line.startswith('#'):
                    continue

                # Stop processing if we reach the sideboard or stickers section
                if (line.upper().startswith("SIDEBOARD:") or line.upper() == "SIDEBOARD" or
                    line.upper().startswith("STICKERS:") or line.upper() == "STICKERS"):
                    print(f"  Reached {line} section, stopping processing")
                    break

                # Try to match the card entry pattern: count + card name + (set) + other info
                # Pattern: number at start, followed by card name, then (set code)
                match = re.match(r'(\d+)\s+([^(]+)(?:\s+\([^)]+\).*)?$', line)

                if match:
                    count = int(match.group(1))
                    card_name = match.group(2).strip()

                    # Add the card with numbered suffix for each copy
                    for i in range(count):
                        # Get the current count for this card
                        if count>1:
                            current_count = card_counts.get(card_name, 0) + 1
                            card_counts[card_name] = current_count

                            # Create the numbered card name
                            numbered_card_name = f"{card_name}{current_count}"
                        else:
                            numbered_card_name = card_name

                        processed_cards.append(numbered_card_name)
                else:
                    # Check if this might be a section header that's not sideboard or stickers
                    if not any(keyword in line.upper() for keyword in ["COMMANDER", "COMPANION", "MAINDECK"]):
                        print(f"  Warning: Could not parse line: {line}")

            # Write the processed cards to the output file
            with open(output_path, 'w', encoding='utf-8') as f:
                for card in processed_cards:
                    f.write(f"{card}\n")

            print(f"  Processed {len(processed_cards)} cards and saved to {output_path}")

        except Exception as e:
            print(f"  Error processing {file_name}: {e}")

    print(f"\nPreprocessing completed! Processed files saved to {output_dir} directory")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        preprocess_decklists(sys.argv[1], sys.argv[2])
    elif len(sys.argv) > 1:
        preprocess_decklists(sys.argv[1])
    else:
        preprocess_decklists()
