import pandas as pd
import numpy as np
import os
import re
import matplotlib.pyplot as plt
from collections import defaultdict
from dir_utils import get_latest_output_dir

def power_law_weight(win_rate, power=2, center=0.25):
    """
    Apply power-law transformation to win rate.
    Preserves sign while emphasizing differences at high win rates.
    Center parameter determines what win rate gives a weight of 0.
    """
    try:
        shifted = win_rate - center
        return np.sign(shifted) * np.abs(shifted) ** power
    except Exception as e:
        print(f"Error calculating power law weight: {e}")
        return 0  # Return a neutral weight on error

def extract_deck_id(url):
    """Extract the deck ID from the Moxfield URL"""
    try:
        # Extract the part after the last slash
        match = re.search(r'/([^/]+)$', url)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"Error extracting deck ID: {e}")
        return None

def find_decklist_file(deck_id, processed_decklists_dir=None):
    """
    Find the decklist file that contains the deck ID in its name.
    
    Args:
        deck_id: The deck ID to search for
        processed_decklists_dir: Optional path to the processed_decklists directory.
                               If None, will use the latest timestamped directory.
    """
    try:
        # If no directory specified, find the latest timestamped directory
        if processed_decklists_dir is None:
            base_dir = get_latest_output_dir()
            if base_dir is None:
                print("Error: No timestamped directory found. Please run previous scripts first.")
                return None
            processed_decklists_dir = os.path.join(base_dir, "processed_decklists")
            print(f"Using processed decklists from: {processed_decklists_dir}")

        # Check if directory exists
        if not os.path.isdir(processed_decklists_dir):
            print(f"Warning: Directory {processed_decklists_dir} not found")
            return None

        # List all files in the directory
        for filename in os.listdir(processed_decklists_dir):
            if deck_id in filename:
                return os.path.join(processed_decklists_dir, filename)

        print(f"Warning: No decklist file found containing ID {deck_id}")
        return None
    except Exception as e:
        print(f"Error finding decklist file for {deck_id}: {e}")
        return None

def read_decklist(filepath):
    """Read the decklist file"""
    try:
        with open(filepath, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Warning: Decklist file not found: {filepath}")
        return []
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return []

def create_spice_tags(card_df, output_file=None):
    """
    Create spice tags for cards in the top 20% of the list based on appearance counts.
    Uses average power instead of power_sum for ranking.
    Ignores cards with numbers appended at the end.
    Append these tags to the existing tagged_cards.txt file.
    If a card already exists in the file, append the spice tag to that entry.
    Also adds #7_potential_traps tag for bottom 20 cards that appear in >20% of decks.
    Adds #8_bad_cards tag for cards in the bottom 20% or bottom 30 cards, whichever is smaller.

    Args:
        card_df: DataFrame containing card data with average_power and appearance_count
        output_file: File where tagged cards will be appended. If None, will use the latest timestamped directory.
    """
    # Set default output file if not provided
    if output_file is None:
        base_dir = get_latest_output_dir()
        if base_dir is None:
            print("Error: No timestamped directory found. Please run 1_edh16_scrape.py first.")
            return pd.DataFrame()
        output_file = os.path.join(base_dir, "spice_tags.txt")
    try:
        # Handle empty dataframe
        if card_df.empty:
            print("No cards to process for spice tags")
            return pd.DataFrame()

        # Filter out cards with numbers at the end (e.g., Mountain1)
        filtered_df = card_df.copy()
        filtered_indices = []

        for card_name in filtered_df.index:
            # Check if the card name ends with a number
            if re.search(r'\d+$', card_name):
                filtered_indices.append(card_name)

        # Remove cards with numbers at the end
        filtered_df = filtered_df.drop(filtered_indices)

        print(f"Filtered out {len(filtered_indices)} cards with numbers at the end")

        # Handle empty dataframe after filtering
        if filtered_df.empty:
            print("No cards left after filtering")
            return pd.DataFrame()

        # Ensure average_power column exists and has valid values
        if 'average_power' not in filtered_df.columns:
            print("Warning: average_power column not found, calculating it")
            if 'power_law_sum' in filtered_df.columns and 'appearance_count' in filtered_df.columns:
                filtered_df['average_power'] = filtered_df['power_law_sum'] / filtered_df['appearance_count'].replace(0, 1)
            else:
                print("Error: Cannot calculate average_power, required columns missing")
                return pd.DataFrame()

        # Replace NaN values with 0
        filtered_df['average_power'] = filtered_df['average_power'].fillna(0)

        # Sort by average_power (descending) to get the complete ordered list
        sorted_df = filtered_df.sort_values('average_power', ascending=False).copy()

        # Calculate the cutoff for top 20%
        top_20_percent_cutoff = max(1, int(len(sorted_df) * 0.2))  # Ensure at least 1 card
        top_cards = sorted_df.iloc[:top_20_percent_cutoff].copy()

        # Calculate the cutoff for bottom 20% or 30 cards, whichever is smaller
        bottom_20_percent_cutoff = max(1, int(len(sorted_df) * 0.2))  # Ensure at least 1 card
        bottom_30_cards_cutoff = min(30, len(sorted_df))
        bottom_cutoff = min(bottom_20_percent_cutoff, bottom_30_cards_cutoff)

        # Get the bottom cards
        bottom_cards = sorted_df.iloc[-bottom_cutoff:].copy()
        bottom_threshold = bottom_cards['average_power'].max()

        print(f"Selected bottom {bottom_cutoff} cards as bad cards (min of 20% and 30 cards)")

        # Calculate the total number of decks for percentage calculation
        total_decks = filtered_df['appearance_count'].sum() / len(filtered_df)  # Average appearances per card
        deck_threshold_percentage = 0.2  # 20% of decks
        deck_threshold = deck_threshold_percentage * total_decks

        # Debug information
        print(f"Average decks per card: {total_decks:.2f}")
        print(f"Deck threshold (20%): {deck_threshold:.2f}")
        print(f"Bottom score threshold: {bottom_threshold}")

        # Apply tags based on appearance counts
        def assign_spice_tag(appearances):
            if pd.isna(appearances):
                return "#5_medium_spice"  # Default tag for missing data
            if appearances < 3:
                return "#4_high_spice"
            elif appearances <= 10:
                return "#5_medium_spice"
            else:
                return "#6_low_spice"

        # Ensure appearance_count column exists
        if 'appearance_count' not in top_cards.columns:
            print("Warning: appearance_count column not found, using default values")
            top_cards['appearance_count'] = 5  # Default middle value

        top_cards['spice_tag'] = top_cards['appearance_count'].apply(assign_spice_tag)

        # Create a dictionary of cards with their spice tags
        spice_tags = {card: tag for card, tag in zip(top_cards.index, top_cards['spice_tag'])}

        # Add potential_traps and bad_cards tags
        additional_tags = {}

        # Find cards that appear in >20% of decks
        high_appearance_cards = filtered_df[filtered_df['appearance_count'] > deck_threshold].copy()
        print(f"Found {len(high_appearance_cards)} cards appearing in >20% of decks")

        # Sort these by average_power (ascending) to get the worst performers
        high_appearance_cards = high_appearance_cards.sort_values('average_power', ascending=True)

        # Take the bottom 20 cards (or all if fewer than 20)
        potential_trap_count = min(20, len(high_appearance_cards))
        potential_traps = high_appearance_cards.iloc[:potential_trap_count]

        print(f"Selected {potential_trap_count} cards as potential traps")

        # Debug: Print the potential traps
        print("\nPotential trap cards:")
        for card, row in potential_traps.iterrows():
            print(f"  {card}: appearances={row['appearance_count']}, avg_power={row['average_power']:.4f}")
            additional_tags[card] = "#7_potential_traps"

        # Tag cards in the bottom cards as bad cards
        print("\nBad cards:")
        for card, row in bottom_cards.iterrows():
            # Skip cards already tagged as potential traps
            if card in additional_tags:
                continue
            print(f"  {card}: appearances={row['appearance_count']}, avg_power={row['average_power']:.4f}")
            additional_tags[card] = "#8_bad_cards"

        # Check if the output file exists
        if os.path.exists(output_file):
            try:
                # Read the existing file
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()

                # Process existing lines
                updated_lines = []
                cards_found = set()

                for line in existing_lines:
                    line = line.strip()
                    if not line:
                        updated_lines.append(line)
                        continue

                    # Extract card name from the format "1 Card Name #tag"
                    try:
                        parts = line.split()
                        if not parts:
                            updated_lines.append(line)
                            continue

                        # Expected format: "1 Card Name #tag"
                        if parts[0].isdigit():
                            # Find all tags (starting with #)
                            tag_indices = [i for i, part in enumerate(parts) if part.startswith('#')]

                            if tag_indices:
                                # Card name is between the count and the first tag
                                first_tag_index = tag_indices[0]
                                card_name = ' '.join(parts[1:first_tag_index])
                            else:
                                # No tags yet, card name is everything after the count
                                card_name = ' '.join(parts[1:])
                        else:
                            # Unexpected format (no count), try to extract card name
                            tag_indices = [i for i, part in enumerate(parts) if part.startswith('#')]
                            if tag_indices:
                                first_tag_index = tag_indices[0]
                                card_name = ' '.join(parts[:first_tag_index])
                            else:
                                card_name = ' '.join(parts)

                        # Check if this card has a spice tag
                        new_tags = []
                        if card_name in spice_tags:
                            new_tags.append(spice_tags[card_name])

                        # Check if this card has additional tags
                        if card_name in additional_tags:
                            new_tags.append(additional_tags[card_name])

                        if new_tags:
                            # Append the tags to the existing line
                            updated_line = f"{line} {' '.join(new_tags)}"
                            updated_lines.append(updated_line)
                            cards_found.add(card_name)
                        else:
                            # Keep the line as is
                            updated_lines.append(line)
                    except Exception as e:
                        print(f"Error processing line '{line}': {e}")
                        updated_lines.append(line)  # Keep the original line

                # Add new cards with tags that weren't in the file
                all_tagged_cards = {**spice_tags, **additional_tags}
                for card in set(spice_tags.keys()) | set(additional_tags.keys()):
                    if card not in cards_found:
                        # Combine all tags for this card
                        combined_tags = []
                        if card in spice_tags:
                            combined_tags.append(spice_tags[card])
                        if card in additional_tags:
                            combined_tags.append(additional_tags[card])

                        # Add new cards with a default count of 1
                        updated_lines.append(f"1 {card} {' '.join(combined_tags)}")

                # Write back to the file
                with open(output_file, 'w', encoding='utf-8') as f:
                    for line in updated_lines:
                        f.write(f"{line}\n")
            except Exception as e:
                print(f"Error updating existing file {output_file}: {e}")
                # Fallback: Create a new file with just the tags
                try:
                    with open(output_file + '.new', 'w', encoding='utf-8') as f:
                        for card in set(spice_tags.keys()) | set(additional_tags.keys()):
                            combined_tags = []
                            if card in spice_tags:
                                combined_tags.append(spice_tags[card])
                            if card in additional_tags:
                                combined_tags.append(additional_tags[card])
                            f.write(f"1 {card} {' '.join(combined_tags)}\n")
                    print(f"Created fallback file {output_file}.new due to error")
                except Exception as e2:
                    print(f"Error creating fallback file: {e2}")
        else:
            # If file doesn't exist, create it with just the tagged cards
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    for card in set(spice_tags.keys()) | set(additional_tags.keys()):
                        combined_tags = []
                        if card in spice_tags:
                            combined_tags.append(spice_tags[card])
                        if card in additional_tags:
                            combined_tags.append(additional_tags[card])
                        # Add new cards with a default count of 1
                        f.write(f"1 {card} {' '.join(combined_tags)}\n")
            except Exception as e:
                print(f"Error creating new file {output_file}: {e}")

        # Print summary
        print(f"\nSpice tag summary for top 20% cards ({len(top_cards)} cards):")
        print(f"  #4_high_spice (< 3 appearances): {sum(top_cards['spice_tag'] == '#4_high_spice')}")
        print(f"  #5_medium_spice (3-10 appearances): {sum(top_cards['spice_tag'] == '#5_medium_spice')}")
        print(f"  #6_low_spice (> 10 appearances): {sum(top_cards['spice_tag'] == '#6_low_spice')}")

        # Count potential traps and bad cards
        potential_traps_count = sum(1 for tags in additional_tags.values() if "#7_potential_traps" in tags)
        bad_cards_count = sum(1 for tags in additional_tags.values() if "#8_bad_cards" in tags)
        print(f"  #7_potential_traps (bottom 20 cards with >20% appearance): {potential_traps_count}")
        print(f"  #8_bad_cards (bottom {bottom_cutoff} cards): {bad_cards_count}")

        print(f"\nTags appended to {output_file}")

        return top_cards
    except Exception as e:
        print(f"Error in create_spice_tags: {e}")
        import traceback
        print(traceback.format_exc())
        return pd.DataFrame()  # Return empty DataFrame on error

def analyze_deck_win_rates(csv_file=None, output_file=None):
    """
    Analyze win rates for cards across all decks.
    
    Args:
        csv_file: Path to the CSV file with tournament results. If None, will look in the latest timestamped directory.
        output_file: Path to save the analysis results. If None, will save to winrate_analysis.txt in the timestamped directory.
    """
    # Find the latest output directory if not specified
    if csv_file is None or output_file is None:
        base_dir = get_latest_output_dir()
        if base_dir is None:
            print("Error: No timestamped directory found. Please run 1_edh16_scrape.py first.")
            return pd.DataFrame()
        
        if csv_file is None:
            csv_file = os.path.join(base_dir, "edh16_scrape.csv")
        
        if output_file is None:
            output_file = os.path.join(base_dir, "winrate_analysis.txt")
    
    try:
        # Load the CSV file
        df = pd.read_csv(csv_file)
        print(f"Successfully loaded data with {len(df)} records from {csv_file}")

        # Print column names to debug
        print("Available columns:", df.columns.tolist())

        # Identify relevant columns
        if 'Wins' in df.columns and 'Losses' in df.columns:
            win_col = 'Wins'
            loss_col = 'Losses'
            draw_col = 'Draws' if 'Draws' in df.columns else None
            url_col = 'Weblink'
            # Try to find a deck name column - check multiple possible names
            possible_deck_cols = ['Deck', 'Commander', 'Name', 'Title', 'DeckName']
            deck_col = next((col for col in possible_deck_cols if col in df.columns), None)
        else:
            win_col = 'wins'
            loss_col = 'losses'
            draw_col = 'draws' if 'draws' in df.columns else None
            url_col = 'url'
            # Try to find a deck name column - check multiple possible names
            possible_deck_cols = ['deck_name', 'commander', 'name', 'title', 'deckname']
            deck_col = next((col for col in possible_deck_cols if col in df.columns), None)

        if not url_col or url_col not in df.columns:
            print(f"Error: Weblink column not found in CSV. Available columns: {df.columns.tolist()}")
            return pd.DataFrame()

        # Calculate adjusted win rate with draws worth 0.25 of a win
        df['total_games'] = df[win_col] + df[loss_col]
        if draw_col and draw_col in df.columns:
            df['total_games'] += df[draw_col]
            # Adjusted win rate: wins + 0.25*draws / total games
            df['win_rate'] = (df[win_col] + 0.25 * df[draw_col]) / df['total_games']
        else:
            df['win_rate'] = df[win_col] / df['total_games']

        # Handle division by zero
        df['win_rate'] = df['win_rate'].fillna(0.25)  # Default to neutral win rate

        # Calculate power law weight with center at 0.25
        center = 0.25  # Win rate that produces a weight of 0
        power = 2      # Power parameter for non-linearity
        df['power_weight'] = df['win_rate'].apply(lambda x: power_law_weight(x, power=power, center=center))

        # Display the win rates and weights for verification
        print("\nSample of win rates and power weights (centered at 0.25):")
        if deck_col:
            print(df[[deck_col, 'win_rate', 'power_weight']].head(10))
        else:
            print(df[['win_rate', 'power_weight']].head(10))
            # Add a generic deck name column for display purposes
            df['DeckIndex'] = [f"Deck_{i}" for i in range(len(df))]
            deck_col = 'DeckIndex'

        # Initialize card dictionary using defaultdict for more robust handling
        card_dict = defaultdict(lambda: {'appearance_count': 0, 'power_law_sum': 0})

        # Process each deck
        processed_decks = 0
        for idx, row in df.iterrows():
            try:
                deck_id = extract_deck_id(row[url_col])
                if not deck_id:
                    print(f"Warning: Could not extract deck ID from Weblink: {row[url_col]}")
                    continue

                deck_weight = row['power_weight']
                deck_name = row[deck_col] if deck_col else f"Deck_{idx}"

                # Find the decklist file
                decklist_path = find_decklist_file(deck_id)
                if not decklist_path:
                    continue

                print(f"Processing {deck_name} (ID: {deck_id}) with power weight: {deck_weight:.4f}")

                # Read the decklist
                cards = read_decklist(decklist_path)
                if not cards:
                    print(f"Warning: No cards found in decklist for {deck_name}")
                    continue

                # Update card dictionary
                for card in cards:
                    card_dict[card]['appearance_count'] += 1
                    card_dict[card]['power_law_sum'] += deck_weight

                processed_decks += 1
            except Exception as e:
                print(f"Error processing deck at index {idx}: {e}")
                continue

        print(f"Successfully processed {processed_decks} decks")

        # Convert to DataFrame for easier analysis
        card_df = pd.DataFrame.from_dict(card_dict, orient='index')

        # Handle empty dataframe case
        if card_df.empty:
            print("No cards were processed. Check file paths and deck IDs.")
            return pd.DataFrame()

        # Calculate average power per appearance
        card_df['average_power'] = card_df['power_law_sum'] / card_df['appearance_count']

        # Handle potential NaN values
        card_df = card_df.fillna(0)

        # Add card names as a column for easier reference
        card_df['card_name'] = card_df.index

        # Sort by power law sum (descending)
        sum_df = card_df.sort_values('power_law_sum', ascending=False)

        # Sort by average power (descending)
        avg_df = card_df.sort_values('average_power', ascending=False)


        # Filter to cards that appear in at least 3 decks for more reliable average power
        min_appearances = 3
        reliable_avg_df = card_df[card_df['appearance_count'] >= min_appearances].sort_values('average_power', ascending=False)

        # Save results to files in the timestamped directory
        try:
            sum_df.to_csv(os.path.join(os.path.dirname(output_file), 'card_power_by_sum.csv'))
            avg_df.to_csv(os.path.join(os.path.dirname(output_file), 'card_power_by_average.csv'))
            reliable_avg_df.to_csv(os.path.join(os.path.dirname(output_file), 'card_power_by_reliable_average.csv'))
            print(f"Analysis saved to {os.path.dirname(output_file)}/")
        except Exception as e:
            print(f"Error saving CSV files: {e}")

        # Visualize the power law function with center at 0.25
        try:
            win_rates = np.linspace(0, 1, 100)
            weights = [power_law_weight(wr, power=power, center=center) for wr in win_rates]
            
            plt.figure(figsize=(10, 6))
            plt.plot(win_rates, weights)
            plt.axhline(y=0, color='gray', linestyle='--')
            plt.axvline(x=center, color='gray', linestyle='--')
            plt.xlabel('Win Rate')
            plt.ylabel('Weight')
            plt.title(f'Power Law Weighting (Power={power}, Center={center})')
            plt.grid(True)
            
            # Save the visualization in the timestamped directory
            viz_path = os.path.join(os.path.dirname(output_file), 'power_law_weight_function.png')
            plt.savefig(viz_path)
            print(f"Visualization saved to {viz_path}")
            plt.close()
        except Exception as e:
            print(f"Error creating visualization: {e}")

        return card_df

    except Exception as e:
        import traceback
        print(f"Error processing data: {e}")
        print(traceback.format_exc())
        return pd.DataFrame()

def main():
    # Find the latest output directory
    base_dir = get_latest_output_dir()
    if base_dir is None:
        print("Error: No timestamped directory found. Please run 1_edh16_scrape.py first.")
        return
    
    # Set up file paths
    csv_file = os.path.join(base_dir, "edh16_scrape.csv")
    winrate_output = os.path.join(base_dir, "winrate_analysis.txt")
    tagged_cards_file = os.path.join(base_dir, "tagged_cards.txt")
    
    # Run the analysis
    card_df = analyze_deck_win_rates(csv_file, winrate_output)
    
    # Create spice tags if we have card data
    if not card_df.empty:
        # Check if tagged_cards.txt exists, if not, create it
        if not os.path.exists(tagged_cards_file):
            print(f"Creating new {tagged_cards_file} file")
            with open(tagged_cards_file, 'w', encoding='utf-8') as f:
                f.write("# This file contains card tags. Format: <count> <card name> #tag1 #tag2\n")
        
        # Append spice tags to the existing tagged_cards.txt
        print(f"\nAppending spice tags to {tagged_cards_file}")
        create_spice_tags(card_df, tagged_cards_file)
    else:
        print("No card data available to create spice tags")

if __name__ == "__main__":
    main()
