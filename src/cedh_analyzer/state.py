"""State management for analysis progress and resumption."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from datetime import datetime

from .config import DATA_DIR, STATE_FILE


@dataclass
class AnalysisState:
    """Represents the current state of an analysis run."""
    
    commander_url: str = ""
    commander_name: str = ""
    started_at: str = ""
    
    # Stage completion flags
    stage_edh16_complete: bool = False
    stage_moxfield_complete: bool = False
    stage_preprocess_complete: bool = False
    stage_basic_analytics_complete: bool = False
    stage_winrate_analytics_complete: bool = False
    
    # Stage-specific data
    deck_count: int = 0
    decks_scraped: int = 0
    cards_analyzed: int = 0
    
    # Output paths
    output_dir: str = ""
    
    @property
    def current_stage(self) -> int:
        """Return the current stage number (1-5), or 0 if not started."""
        if not self.commander_url:
            return 0
        if not self.stage_edh16_complete:
            return 1
        if not self.stage_moxfield_complete:
            return 2
        if not self.stage_preprocess_complete:
            return 3
        if not self.stage_basic_analytics_complete:
            return 4
        if not self.stage_winrate_analytics_complete:
            return 5
        return 6  # Complete
    
    @property
    def is_complete(self) -> bool:
        """Check if all stages are complete."""
        return self.current_stage == 6
    
    @property
    def has_existing_run(self) -> bool:
        """Check if there's an incomplete existing run."""
        return self.commander_url and not self.is_complete


def load_state() -> AnalysisState:
    """Load state from disk, or return fresh state if none exists."""
    if not STATE_FILE.exists():
        return AnalysisState()
    
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        return AnalysisState(**data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return AnalysisState()


def save_state(state: AnalysisState) -> None:
    """Save state to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(asdict(state), f, indent=2)


def clear_state() -> None:
    """Clear all state and data files."""
    import shutil
    
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)


def initialize_new_run(commander_url: str, commander_name: str) -> AnalysisState:
    """Initialize a fresh analysis run."""
    clear_state()
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = str(DATA_DIR / f"run_{timestamp}")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    state = AnalysisState(
        commander_url=commander_url,
        commander_name=commander_name,
        started_at=datetime.now().isoformat(),
        output_dir=output_dir,
    )
    save_state(state)
    return state
