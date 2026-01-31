"""Stage 5: Win rate based analytics and spice tagging."""

import csv
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .base import Stage, StageResult
from ..state import save_state
from ..config import TAGS, HIGH_SPICE_COUNT, MEDIUM_SPICE_COUNT
from .edh16_scrape import extract_deck_id


def power_law_weight(win_rate: float, power: float = 2, center: float = 0.25) -> float:
    """
    Apply power-law transformation to win rate.
    
    Preserves sign while emphasizing differences at high win rates.
    Center parameter determines what win rate gives a weight of 0.
    """
    shifted = win_rate - center
    return float(np.sign(shifted) * np.abs(shifted) ** power)


class WinrateAnalyticsStage(Stage):
    """Analyze cards based on win rates and add spice tags."""
    
    name = "Win Rate Analytics"
    description = "Analyzing card performance by win rate"
    
    def is_complete(self) -> bool:
        return self.state.stage_winrate_analytics_complete
    
    async def run(self) -> StageResult:
        """Execute the win rate analytics stage."""
        if self.is_complete():
            return StageResult(success=True, message="Already complete")
        
        output_dir = Path(self.state.output_dir)
        csv_file = output_dir / "edh16_scrape.csv"
        processed_dir = output_dir / "processed_decklists"
        tagged_file = output_dir / "tagged_cards.txt"
        
        if not csv_file.exists() or not processed_dir.exists():
            return StageResult(
                success=False,
                message="Required data files not found. Run previous stages first.",
            )
        
        self.report_progress(0.0, "Loading tournament data...")
        
        try:
            # Load tournament data
            df = pd.read_csv(csv_file)
            
            # Calculate win rates
            df["total_games"] = df["wins"].fillna(0) + df["losses"].fillna(0)
            if "draws" in df.columns:
                df["total_games"] += df["draws"].fillna(0)
                df["win_rate"] = (df["wins"].fillna(0) + 0.25 * df["draws"].fillna(0)) / df["total_games"].replace(0, 1)
            else:
                df["win_rate"] = df["wins"].fillna(0) / df["total_games"].replace(0, 1)
            
            df["win_rate"] = df["win_rate"].fillna(0.25)
            df["power_weight"] = df["win_rate"].apply(power_law_weight)
            
            self.report_progress(0.2, "Analyzing card performance...")
            
            # Build card statistics
            card_dict: dict[str, dict] = defaultdict(
                lambda: {"appearance_count": 0, "power_law_sum": 0}
            )
            
            processed_decks = 0
            for idx, row in df.iterrows():
                deck_id = extract_deck_id(row["url"])
                if not deck_id:
                    continue
                
                # Find decklist file
                decklist_file = self._find_decklist(processed_dir, deck_id)
                if not decklist_file:
                    continue
                
                cards = self._read_decklist(decklist_file)
                if not cards:
                    continue
                
                deck_weight = row["power_weight"]
                for card in cards:
                    card_dict[card]["appearance_count"] += 1
                    card_dict[card]["power_law_sum"] += deck_weight
                
                processed_decks += 1
                progress = 0.2 + (idx / len(df)) * 0.5
                self.report_progress(progress, f"Processing deck {idx + 1}/{len(df)}")
            
            self.report_progress(0.75, "Calculating spice tags...")
            
            # Create DataFrame for analysis
            card_df = pd.DataFrame.from_dict(card_dict, orient="index")
            if card_df.empty:
                return StageResult(
                    success=False,
                    message="No card data available after processing",
                )
            
            card_df["average_power"] = (
                card_df["power_law_sum"] / card_df["appearance_count"].replace(0, 1)
            )
            
            # Filter out numbered cards
            filtered_df = card_df[
                ~card_df.index.str.contains(r"\d+$", regex=True)
            ].copy()
            
            if filtered_df.empty:
                return StageResult(
                    success=False,
                    message="No valid cards after filtering",
                )
            
            # Sort by average power
            sorted_df = filtered_df.sort_values("average_power", ascending=False)
            
            # Top 20% for spice tags
            top_cutoff = max(1, int(len(sorted_df) * 0.2))
            top_cards = sorted_df.iloc[:top_cutoff].copy()
            
            # Bottom 20% or 30 cards for bad cards
            bottom_cutoff = min(max(1, int(len(sorted_df) * 0.2)), 30)
            bottom_cards = sorted_df.iloc[-bottom_cutoff:]
            
            # Calculate deck threshold for potential traps
            avg_decks = filtered_df["appearance_count"].mean()
            deck_threshold = 0.2 * avg_decks
            
            # Identify potential traps (high appearance, low performance)
            high_appearance = filtered_df[
                filtered_df["appearance_count"] > deck_threshold
            ].sort_values("average_power", ascending=True)
            potential_traps = high_appearance.iloc[:min(20, len(high_appearance))]
            
            # Assign spice tags
            spice_tags: dict[str, str] = {}
            for card, row in top_cards.iterrows():
                appearances = row["appearance_count"]
                if appearances < HIGH_SPICE_COUNT:
                    spice_tags[card] = TAGS["high_spice"]
                elif appearances <= MEDIUM_SPICE_COUNT:
                    spice_tags[card] = TAGS["medium_spice"]
                else:
                    spice_tags[card] = TAGS["low_spice"]
            
            # Assign trap and bad card tags
            additional_tags: dict[str, str] = {}
            for card in potential_traps.index:
                additional_tags[card] = TAGS["potential_traps"]
            
            for card in bottom_cards.index:
                if card not in additional_tags:
                    additional_tags[card] = TAGS["bad_cards"]
            
            self.report_progress(0.9, "Updating tagged cards file...")
            
            # Update tagged_cards.txt
            self._update_tagged_cards(tagged_file, spice_tags, additional_tags)
            
            # Save analytics CSVs
            sorted_df.to_csv(output_dir / "card_power_by_average.csv")
            
            self.state.stage_winrate_analytics_complete = True
            save_state(self.state)
            
            self.report_progress(1.0, "Analysis complete")
            
            spice_count = len(spice_tags)
            trap_count = sum(1 for t in additional_tags.values() if t == TAGS["potential_traps"])
            bad_count = sum(1 for t in additional_tags.values() if t == TAGS["bad_cards"])
            
            return StageResult(
                success=True,
                message=f"Tagged {spice_count} spice cards, {trap_count} potential traps, {bad_count} underperformers",
                data={
                    "spice_cards": spice_count,
                    "potential_traps": trap_count,
                    "bad_cards": bad_count,
                    "processed_decks": processed_decks,
                },
            )
        
        except Exception as e:
            return StageResult(success=False, message=f"Error: {str(e)}")
    
    def _find_decklist(self, processed_dir: Path, deck_id: str) -> Path | None:
        """Find decklist file by deck ID."""
        for file in processed_dir.glob("*.txt"):
            if deck_id in file.name:
                return file
        return None
    
    def _read_decklist(self, filepath: Path) -> list[str]:
        """Read decklist from file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception:
            return []
    
    def _update_tagged_cards(
        self,
        tagged_file: Path,
        spice_tags: dict[str, str],
        additional_tags: dict[str, str],
    ) -> None:
        """Update the tagged_cards.txt file with new tags."""
        if not tagged_file.exists():
            # Create new file with just spice/additional tags
            with open(tagged_file, "w", encoding="utf-8") as f:
                all_cards = set(spice_tags.keys()) | set(additional_tags.keys())
                for card in all_cards:
                    tags = []
                    if card in spice_tags:
                        tags.append(spice_tags[card])
                    if card in additional_tags:
                        tags.append(additional_tags[card])
                    f.write(f"1 {card} {' '.join(tags)}\n")
            return
        
        # Update existing file
        with open(tagged_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        updated_lines = []
        cards_found = set()
        
        for line in lines:
            line = line.strip()
            if not line:
                updated_lines.append(line)
                continue
            
            parts = line.split()
            if not parts or not parts[0].isdigit():
                updated_lines.append(line)
                continue
            
            # Find card name (between count and first tag)
            tag_indices = [i for i, p in enumerate(parts) if p.startswith("#")]
            if tag_indices:
                card_name = " ".join(parts[1:tag_indices[0]])
            else:
                card_name = " ".join(parts[1:])
            
            # Add new tags
            new_tags = []
            if card_name in spice_tags:
                new_tags.append(spice_tags[card_name])
            if card_name in additional_tags:
                new_tags.append(additional_tags[card_name])
            
            if new_tags:
                updated_lines.append(f"{line} {' '.join(new_tags)}")
                cards_found.add(card_name)
            else:
                updated_lines.append(line)
        
        # Add new cards not in original file
        for card in set(spice_tags.keys()) | set(additional_tags.keys()):
            if card not in cards_found:
                tags = []
                if card in spice_tags:
                    tags.append(spice_tags[card])
                if card in additional_tags:
                    tags.append(additional_tags[card])
                updated_lines.append(f"1 {card} {' '.join(tags)}")
        
        with open(tagged_file, "w", encoding="utf-8") as f:
            for line in updated_lines:
                f.write(f"{line}\n")
