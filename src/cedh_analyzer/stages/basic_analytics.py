"""Stage 4: Basic card usage analytics."""

import re
from collections import Counter
from pathlib import Path

from .base import Stage, StageResult
from ..state import save_state
from ..config import TAGS, CORE_THRESHOLD, ESSENTIAL_THRESHOLD, COMMON_THRESHOLD


class BasicAnalyticsStage(Stage):
    """Analyze card usage rates across all decklists."""
    
    name = "Basic Analytics"
    description = "Analyzing card usage patterns"
    
    def is_complete(self) -> bool:
        return self.state.stage_basic_analytics_complete
    
    async def run(self) -> StageResult:
        """Execute the basic analytics stage."""
        if self.is_complete():
            return StageResult(success=True, message="Already complete")
        
        output_dir = Path(self.state.output_dir)
        processed_dir = output_dir / "processed_decklists"
        
        if not processed_dir.exists():
            return StageResult(
                success=False,
                message="Processed decklists not found. Run stage 3 first.",
            )
        
        deck_files = list(processed_dir.glob("*.txt"))
        if not deck_files:
            return StageResult(success=False, message="No processed decks to analyze")
        
        self.report_progress(0.0, f"Analyzing {len(deck_files)} decklists...")
        
        # Count card occurrences
        card_counts = Counter()
        card_quantities: dict[str, int] = {}
        total_decks = len(deck_files)
        
        for idx, file_path in enumerate(deck_files):
            progress = (idx + 1) / total_decks * 0.7
            self.report_progress(progress, f"Analyzing {file_path.name}...")
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    cards = [line.strip() for line in f if line.strip()]
                
                # Count unique base cards (without numeric suffixes)
                base_cards = set()
                deck_card_counts = Counter()
                
                for card in cards:
                    base_card = re.sub(r"\d+$", "", card)
                    base_cards.add(base_card)
                    deck_card_counts[base_card] += 1
                
                for card in base_cards:
                    card_counts[card] += 1
                
                # Track max quantity per card
                for card, count in deck_card_counts.items():
                    if card not in card_quantities or count > card_quantities[card]:
                        card_quantities[card] = count
            
            except Exception:
                pass
        
        self.report_progress(0.8, "Calculating usage percentages...")
        
        # Calculate usage percentages and assign tags
        tagged_cards = []
        
        for card, count in card_counts.items():
            usage_percent = (count / total_decks) * 100
            quantity = card_quantities.get(card, 1)
            
            if usage_percent >= CORE_THRESHOLD:
                tag = TAGS["core"]
            elif usage_percent >= ESSENTIAL_THRESHOLD:
                tag = TAGS["essential"]
            elif usage_percent >= COMMON_THRESHOLD:
                tag = TAGS["common"]
            else:
                continue  # Skip cards below common threshold
            
            tagged_cards.append((card, quantity, usage_percent, tag))
        
        # Sort by usage percentage
        tagged_cards.sort(key=lambda x: x[2], reverse=True)
        
        # Write results
        output_file = output_dir / "tagged_cards.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for card, quantity, _, tag in tagged_cards:
                f.write(f"{quantity} {card} {tag}\n")
        
        # Count by category
        core_count = sum(1 for _, _, _, tag in tagged_cards if tag == TAGS["core"])
        essential_count = sum(1 for _, _, _, tag in tagged_cards if tag == TAGS["essential"])
        common_count = sum(1 for _, _, _, tag in tagged_cards if tag == TAGS["common"])
        
        self.state.cards_analyzed = len(card_counts)
        self.state.stage_basic_analytics_complete = True
        save_state(self.state)
        
        self.report_progress(1.0, f"Found {len(tagged_cards)} core/essential/common cards")
        
        return StageResult(
            success=True,
            message=f"Analyzed {len(card_counts)} unique cards: {core_count} core, {essential_count} essential, {common_count} common",
            data={
                "unique_cards": len(card_counts),
                "core": core_count,
                "essential": essential_count,
                "common": common_count,
            },
        )
