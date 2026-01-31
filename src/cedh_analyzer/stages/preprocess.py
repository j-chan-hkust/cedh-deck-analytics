"""Stage 3: Preprocess decklists for analysis."""

import re
from pathlib import Path

from .base import Stage, StageResult
from ..state import save_state


class PreprocessStage(Stage):
    """Preprocess raw decklists into normalized card lists."""
    
    name = "Preprocess"
    description = "Normalizing decklist data"
    
    def is_complete(self) -> bool:
        return self.state.stage_preprocess_complete
    
    async def run(self) -> StageResult:
        """Execute the preprocessing stage."""
        if self.is_complete():
            return StageResult(success=True, message="Already complete")
        
        output_dir = Path(self.state.output_dir)
        deck_lists_dir = output_dir / "deck_lists"
        processed_dir = output_dir / "processed_decklists"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        if not deck_lists_dir.exists():
            return StageResult(
                success=False,
                message="Deck lists directory not found. Run stage 2 first.",
            )
        
        deck_files = list(deck_lists_dir.glob("*.txt"))
        if not deck_files:
            return StageResult(success=False, message="No deck files to process")
        
        self.report_progress(0.0, f"Processing {len(deck_files)} decklists...")
        
        processed_count = 0
        total_cards = 0
        
        for idx, file_path in enumerate(deck_files):
            progress = (idx + 1) / len(deck_files)
            self.report_progress(progress * 0.9, f"Processing {file_path.name}...")
            
            try:
                cards = self._process_decklist(file_path)
                
                output_path = processed_dir / file_path.name
                with open(output_path, "w", encoding="utf-8") as f:
                    for card in cards:
                        f.write(f"{card}\n")
                
                processed_count += 1
                total_cards += len(cards)
            
            except Exception as e:
                # Log but continue processing other files
                pass
        
        self.state.stage_preprocess_complete = True
        save_state(self.state)
        
        self.report_progress(1.0, f"Processed {processed_count} decklists")
        
        return StageResult(
            success=True,
            message=f"Processed {processed_count} decklists with {total_cards} total cards",
            data={"processed": processed_count, "total_cards": total_cards},
        )
    
    def _process_decklist(self, file_path: Path) -> list[str]:
        """
        Process a single decklist file.
        
        Extracts card names, handles multiple copies by appending numbers,
        and stops at sideboard/stickers sections.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            deck_text = f.read()
        
        processed_cards = []
        card_counts: dict[str, int] = {}
        
        for line in deck_text.splitlines():
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            
            # Stop at sideboard or stickers
            upper_line = line.upper()
            if any(
                upper_line.startswith(s) or upper_line == s
                for s in ["SIDEBOARD:", "SIDEBOARD", "STICKERS:", "STICKERS"]
            ):
                break
            
            # Skip section headers
            if any(
                keyword in upper_line
                for keyword in ["COMMANDER", "COMPANION", "MAINDECK"]
            ):
                continue
            
            # Parse card entry: "count card_name (set_code) other_info"
            match = re.match(r"(\d+)\s+([^(]+)(?:\s+\([^)]+\).*)?$", line)
            
            if match:
                count = int(match.group(1))
                card_name = match.group(2).strip()
                
                # Add card with numbered suffix for multiples
                for _ in range(count):
                    if count > 1:
                        current = card_counts.get(card_name, 0) + 1
                        card_counts[card_name] = current
                        numbered_name = f"{card_name}{current}"
                    else:
                        numbered_name = card_name
                    
                    processed_cards.append(numbered_name)
        
        return processed_cards
