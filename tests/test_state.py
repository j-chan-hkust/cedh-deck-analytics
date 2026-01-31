"""Tests for state management."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cedh_analyzer.state import (
    AnalysisState,
    clear_state,
    initialize_new_run,
    load_state,
    save_state,
)


class TestAnalysisState:
    """Tests for AnalysisState dataclass."""
    
    def test_current_stage_not_started(self):
        """Test current_stage returns 0 when not started."""
        state = AnalysisState()
        assert state.current_stage == 0
    
    def test_current_stage_progression(self):
        """Test current_stage returns correct stage as stages complete."""
        state = AnalysisState(commander_url="http://test.com")
        assert state.current_stage == 1
        
        state.stage_edh16_complete = True
        assert state.current_stage == 2
        
        state.stage_moxfield_complete = True
        assert state.current_stage == 3
        
        state.stage_preprocess_complete = True
        assert state.current_stage == 4
        
        state.stage_basic_analytics_complete = True
        assert state.current_stage == 5
        
        state.stage_winrate_analytics_complete = True
        assert state.current_stage == 6
    
    def test_is_complete(self):
        """Test is_complete property."""
        state = AnalysisState(commander_url="http://test.com")
        assert not state.is_complete
        
        state.stage_edh16_complete = True
        state.stage_moxfield_complete = True
        state.stage_preprocess_complete = True
        state.stage_basic_analytics_complete = True
        state.stage_winrate_analytics_complete = True
        
        assert state.is_complete
    
    def test_has_existing_run(self):
        """Test has_existing_run property."""
        state = AnalysisState()
        assert not state.has_existing_run
        
        state.commander_url = "http://test.com"
        assert state.has_existing_run
        
        # Complete all stages
        state.stage_edh16_complete = True
        state.stage_moxfield_complete = True
        state.stage_preprocess_complete = True
        state.stage_basic_analytics_complete = True
        state.stage_winrate_analytics_complete = True
        
        assert not state.has_existing_run  # Complete run is not "existing"


class TestStatePersistence:
    """Tests for state save/load functionality."""
    
    def test_save_and_load_state(self, tmp_path: Path):
        """Test saving and loading state."""
        state_file = tmp_path / "state.json"
        
        with patch("cedh_analyzer.state.STATE_FILE", state_file):
            with patch("cedh_analyzer.state.DATA_DIR", tmp_path):
                original = AnalysisState(
                    commander_url="http://test.com",
                    commander_name="Test Commander",
                    deck_count=42,
                    stage_edh16_complete=True,
                )
                
                save_state(original)
                loaded = load_state()
                
                assert loaded.commander_url == original.commander_url
                assert loaded.commander_name == original.commander_name
                assert loaded.deck_count == original.deck_count
                assert loaded.stage_edh16_complete == original.stage_edh16_complete
    
    def test_load_state_missing_file(self, tmp_path: Path):
        """Test loading state when file doesn't exist."""
        state_file = tmp_path / "nonexistent.json"
        
        with patch("cedh_analyzer.state.STATE_FILE", state_file):
            state = load_state()
            assert state.commander_url == ""
            assert state.current_stage == 0
    
    def test_load_state_corrupted_file(self, tmp_path: Path):
        """Test loading state from corrupted file."""
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json {{{")
        
        with patch("cedh_analyzer.state.STATE_FILE", state_file):
            state = load_state()
            assert state.commander_url == ""


class TestInitializeNewRun:
    """Tests for initialize_new_run function."""
    
    def test_initialize_new_run(self, tmp_path: Path):
        """Test initializing a new analysis run."""
        data_dir = tmp_path / ".cedh_data"
        state_file = data_dir / "state.json"
        
        with patch("cedh_analyzer.state.DATA_DIR", data_dir):
            with patch("cedh_analyzer.state.STATE_FILE", state_file):
                state = initialize_new_run(
                    "http://test.com/commander/Test",
                    "Test Commander",
                )
                
                assert state.commander_url == "http://test.com/commander/Test"
                assert state.commander_name == "Test Commander"
                assert state.started_at != ""
                assert state.output_dir != ""
                assert Path(state.output_dir).exists()
