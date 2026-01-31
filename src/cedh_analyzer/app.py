"""Main Textual application for cEDH Analyzer."""

from pathlib import Path

import pyperclip
import pyfiglet
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Label, Static, TextArea

from .config import DEFAULT_COMMANDER_URL
from .state import (
    AnalysisState,
    clear_state,
    initialize_new_run,
    load_state,
)
from .stages import (
    BasicAnalyticsStage,
    EDH16ScrapeStage,
    MoxfieldScrapeStage,
    PreprocessStage,
    WinrateAnalyticsStage,
)


class ResumeModal(ModalScreen[bool]):
    """Modal dialog for resuming or starting fresh."""
    
    BINDINGS = [
        Binding("escape", "start_fresh", "Start Fresh", show=True),
        Binding("enter", "continue_analysis", "Continue", show=True),
    ]
    
    def __init__(self, state: AnalysisState) -> None:
        super().__init__()
        self.existing_state = state
    
    def _format_commander_name(self, name: str | None) -> str:
        """Decode URL-encoded commander name."""
        if not name:
            return "Unknown"
        from urllib.parse import unquote
        return unquote(name)
    
    def compose(self) -> ComposeResult:
        commander = self._format_commander_name(self.existing_state.commander_name)
        progress = self.existing_state.current_stage
        decks_done = self.existing_state.decks_scraped
        decks_total = self.existing_state.deck_count
        
        with Container(id="resume-modal"):
            yield Label("⏸ Existing Analysis Found", id="modal-title")
            yield Static("")
            yield Label(f"Commander: {commander}", classes="modal-info")
            yield Label(f"Progress: Stage {progress}/5", classes="modal-info")
            yield Label(f"Decks processed: {decks_done}/{decks_total}", classes="modal-info")
            yield Static("")
            yield Label("Press Enter to continue", id="resume-continue-hint")
            yield Label("Press Esc to start a new analysis", id="resume-fresh-hint")
    
    def action_start_fresh(self) -> None:
        self.dismiss(False)
    
    def action_continue_analysis(self) -> None:
        self.dismiss(True)


class CompletionModal(ModalScreen[None]):
    """Modal shown when analysis is complete."""
    
    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
        Binding("enter", "dismiss_modal", "Close"),
    ]
    
    def __init__(self, commander_name: str, stats: dict) -> None:
        super().__init__()
        self.commander_name = commander_name
        self.stats = stats
    
    def compose(self) -> ComposeResult:
        with Container(id="completion-modal"):
            yield Label("✓ Analysis Complete!", id="completion-title")
            yield Static("")
            yield Label(f"Commander: {self.commander_name}", classes="completion-info")
            yield Label(
                f"Decks analyzed: {self.stats.get('decks', 0)}",
                classes="completion-info",
            )
            yield Label(
                f"Unique cards: {self.stats.get('cards', 0)}",
                classes="completion-info",
            )
            yield Static("")
            yield Label(
                "📋 Results copied to clipboard!",
                id="clipboard-notice",
            )
            yield Label(
                "Paste directly into Moxfield and group by tag.",
                classes="completion-hint",
            )
            yield Static("")
            yield Label(
                "Press Enter to continue",
                classes="modal-hint",
            )
    
    def action_dismiss_modal(self) -> None:
        self.dismiss(None)


class CEDHAnalyzerApp(App):
    """Main cEDH Analyzer TUI application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #banner {
        height: auto;
        color: $secondary;
        text-align: center;
        padding: 1 0;
    }
    
    #subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }
    
    #main-container {
        padding: 1 4;
    }
    
    #input-section {
        height: auto;
        margin-bottom: 2;
    }
    
    #input-section Label {
        margin-bottom: 1;
    }
    
    #url-input {
        width: 100%;
        height: 4;
        margin-bottom: 1;
    }
    
    #url-input:focus {
        border: tall $secondary;
    }
    
    #input-hint {
        color: $text-muted;
        text-style: italic;
        text-align: center;
    }
    
    /* Modal Styles */
    ResumeModal, CompletionModal {
        align: center middle;
    }
    
    #resume-modal, #completion-modal {
        width: 80%;
        max-width: 100;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: heavy $primary;
    }
    
    #modal-title, #completion-title {
        text-style: bold;
        text-align: center;
        color: $secondary;
        margin-bottom: 1;
    }
    
    #completion-title {
        color: $success;
    }
    
    .modal-info, .completion-info {
        text-align: center;
        padding: 0 2;
    }
    
    #resume-continue-hint {
        text-align: center;
        color: $success;
        text-style: bold;
        margin-top: 1;
    }
    
    #resume-fresh-hint {
        text-align: center;
        color: $text-muted;
    }
    
    .modal-hint {
        text-align: center;
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }
    
    #clipboard-notice {
        text-align: center;
        color: $secondary;
        text-style: bold;
    }
    
    .completion-hint {
        text-align: center;
        color: $text-muted;
        text-style: italic;
    }
    
    #result-preview {
        height: 8;
        margin-top: 1;
        border: tall $primary;
        padding: 1;
        display: none;
    }
    
    #result-preview.visible {
        display: block;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+enter", "submit_url", "Submit", show=True),
    ]
    
    def __init__(self) -> None:
        super().__init__()
        self.state: AnalysisState | None = None
        self._analysis_running = False
    
    def compose(self) -> ComposeResult:
        # Generate ASCII banner
        banner_text = pyfiglet.figlet_format("cEDH Analyzer", font="slant")
        
        with Container(id="main-container"):
            yield Static(banner_text, id="banner")
            yield Label(
                "Competitive EDH Decklist Analysis Tool",
                id="subtitle",
            )
            
            with Vertical(id="input-section"):
                yield Label("Enter EDHTop16 Commander URL:")
                yield TextArea(
                    "",
                    id="url-input",
                    soft_wrap=True,
                    placeholder=DEFAULT_COMMANDER_URL,
                )
                yield Label("Press Ctrl+Enter to start analysis (empty = use placeholder)", id="input-hint")
            
            yield Static("", id="result-preview")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Check for existing state on mount."""
        self.theme = "nord"
        existing_state = load_state()
        
        if existing_state.has_existing_run:
            # Show resume modal - defer to allow mount to complete
            self.call_later(self._show_resume_modal, existing_state)
        else:
            # Focus the input for keyboard-driven interaction
            url_input = self.query_one("#url-input", TextArea)
            url_input.focus()
    
    def _show_resume_modal(self, existing_state: AnalysisState) -> None:
        """Show the resume modal and handle the result."""
        def handle_result(should_continue: bool) -> None:
            url_input = self.query_one("#url-input", TextArea)
            
            if should_continue:
                self.state = existing_state
                # Update URL input with existing URL
                url_input.load_text(existing_state.commander_url)
            else:
                # Start fresh
                clear_state()
                self.state = None
            
            # Focus the input for keyboard-driven interaction
            url_input.focus()
        
        self.push_screen(ResumeModal(existing_state), handle_result)
    
    def action_submit_url(self) -> None:
        """Start or resume the analysis pipeline."""
        if self._analysis_running:
            return
        
        url_input = self.query_one("#url-input", TextArea)
        commander_url = url_input.text.strip()
        
        # Use default URL if empty
        if not commander_url:
            commander_url = DEFAULT_COMMANDER_URL
            url_input.load_text(commander_url)
        
        if not commander_url.startswith("http"):
            self.notify("Invalid URL format", severity="error")
            return
        
        self._analysis_running = True
        url_input.disabled = True
        hint = self.query_one("#input-hint", Label)
        hint.update("Running analysis...")
        
        # Initialize or use existing state
        if self.state is None or self.state.commander_url != commander_url:
            # Extract commander name from URL (basic extraction)
            commander_name = commander_url.split("/commander/")[-1].split("?")[0]
            commander_name = commander_name.replace("%20", " ").replace("%2C", ",")
            self.state = initialize_new_run(commander_url, commander_name)
        
        # Run the pipeline
        self.run_pipeline()
    
    @work(exclusive=True, thread=True)
    async def run_pipeline(self) -> None:
        """Run the analysis pipeline."""
        if not self.state:
            return
        
        stages = [
            (1, EDH16ScrapeStage),
            (2, MoxfieldScrapeStage),
            (3, PreprocessStage),
            (4, BasicAnalyticsStage),
            (5, WinrateAnalyticsStage),
        ]
        
        for stage_num, stage_class in stages:
            if self.state.current_stage > stage_num:
                # Already complete
                continue
            
            stage = stage_class(self.state)
            result = await stage.run()
            
            if not result.success:
                self.call_from_thread(
                    self.notify,
                    f"Stage {stage_num} failed: {result.message}",
                    severity="error",
                )
                self.call_from_thread(self._reset_input)
                return
        
        # All stages complete - finalize
        self.call_from_thread(self._finalize_analysis)
    
    def _reset_input(self) -> None:
        """Reset the input to enabled state."""
        self._analysis_running = False
        url_input = self.query_one("#url-input", TextArea)
        url_input.disabled = False
        url_input.focus()
        hint = self.query_one("#input-hint", Label)
        hint.update("Press Ctrl+Enter to start analysis")
    
    def _finalize_analysis(self) -> None:
        """Finalize the analysis - copy to clipboard and cleanup."""
        if not self.state:
            return
        
        output_dir = Path(self.state.output_dir)
        tagged_file = output_dir / "tagged_cards.txt"
        
        # Copy results to clipboard
        if tagged_file.exists():
            with open(tagged_file, "r", encoding="utf-8") as f:
                results = f.read()
            
            try:
                pyperclip.copy(results)
            except Exception:
                self.notify("Could not copy to clipboard", severity="warning")
        
        # Show completion modal with callback for cleanup after dismissal
        stats = {
            "decks": self.state.decks_scraped,
            "cards": self.state.cards_analyzed,
        }
        
        self.push_screen(
            CompletionModal(self.state.commander_name, stats),
            callback=lambda _: self._cleanup(),
        )
    
    def _cleanup(self) -> None:
        """Clean up state files after successful completion."""
        # Clear state (keeps the output files but removes tracking)
        clear_state()
        self.state = None
        self._reset_input()
        
        self.notify("Analysis complete! Results copied to clipboard.", severity="information")


def main() -> None:
    """Entry point for the application."""
    app = CEDHAnalyzerApp()
    app.run()


if __name__ == "__main__":
    main()
