"""Main Textual application for cEDH Analyzer."""

import asyncio
import shutil
from pathlib import Path

import pyperclip
import pyfiglet
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Input, Label, Static

from .config import APP_NAME, DEFAULT_COMMANDER_URL, DATA_DIR
from .state import (
    AnalysisState,
    clear_state,
    initialize_new_run,
    load_state,
    save_state,
)
from .stages import (
    BasicAnalyticsStage,
    EDH16ScrapeStage,
    MoxfieldScrapeStage,
    PreprocessStage,
    WinrateAnalyticsStage,
)
from .widgets import ProgressStack


class ResumeModal(ModalScreen[bool]):
    """Modal dialog for resuming or starting fresh."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, state: AnalysisState) -> None:
        super().__init__()
        self.existing_state = state
    
    def compose(self) -> ComposeResult:
        with Container(id="resume-modal"):
            yield Label("Existing Analysis Found", id="modal-title")
            yield Label(
                f"Commander: {self.existing_state.commander_name or 'Unknown'}",
                classes="modal-info",
            )
            yield Label(
                f"Progress: Stage {self.existing_state.current_stage}/5",
                classes="modal-info",
            )
            yield Label(
                f"Decks processed: {self.existing_state.decks_scraped}/{self.existing_state.deck_count}",
                classes="modal-info",
            )
            yield Static("")
            yield Label("What would you like to do?", classes="modal-prompt")
            with Horizontal(id="modal-buttons"):
                yield Button("Continue", id="btn-continue", variant="primary")
                yield Button("Start Fresh", id="btn-fresh", variant="warning")
    
    def action_cancel(self) -> None:
        self.dismiss(True)  # Default to continue
    
    @on(Button.Pressed, "#btn-continue")
    def continue_analysis(self) -> None:
        self.dismiss(True)
    
    @on(Button.Pressed, "#btn-fresh")
    def start_fresh(self) -> None:
        self.dismiss(False)


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
            with Center():
                yield Button("Done", id="btn-done", variant="success")
    
    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
    
    @on(Button.Pressed, "#btn-done")
    def done(self) -> None:
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
        margin-bottom: 1;
    }
    
    #start-button {
        width: auto;
        min-width: 20;
    }
    
    #progress-section {
        height: auto;
        padding: 1 2;
        border: tall $primary;
        margin-top: 1;
    }
    
    .section-header {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }
    
    .stage-progress {
        height: auto;
        margin-bottom: 1;
        padding: 0 1;
    }
    
    .stage-progress.active {
        background: $primary 20%;
    }
    
    .stage-progress.complete {
        background: $success 15%;
    }
    
    .stage-progress.error {
        background: $error 20%;
    }
    
    .status-text {
        color: $text-muted;
        text-style: italic;
        margin-left: 2;
    }
    
    .stage-progress.complete .status-text {
        color: $success;
        text-style: bold;
    }
    
    .stage-progress.error .status-text {
        color: $error;
    }
    
    ProgressBar {
        padding: 0 2;
    }
    
    /* Modal Styles */
    #resume-modal, #completion-modal {
        width: 60;
        height: auto;
        padding: 2 3;
        background: $surface;
        border: tall $primary;
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
        margin: 0 1;
    }
    
    .modal-prompt {
        text-align: center;
        margin-top: 1;
    }
    
    #modal-buttons {
        margin-top: 1;
        height: auto;
        align: center middle;
    }
    
    #modal-buttons Button {
        margin: 0 1;
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
    
    #btn-done {
        margin-top: 1;
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
                yield Input(
                    placeholder="https://edhtop16.com/commander/...",
                    value=DEFAULT_COMMANDER_URL,
                    id="url-input",
                )
                with Center():
                    yield Button("Start Analysis", id="start-button", variant="primary")
            
            with Vertical(id="progress-section"):
                yield ProgressStack(id="progress-stack")
            
            yield Static("", id="result-preview")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Check for existing state on mount."""
        existing_state = load_state()
        
        if existing_state.has_existing_run:
            # Show resume modal
            should_continue = await self.push_screen_wait(ResumeModal(existing_state))
            
            if should_continue:
                self.state = existing_state
                # Update URL input with existing URL
                url_input = self.query_one("#url-input", Input)
                url_input.value = existing_state.commander_url
                
                # Update progress display
                progress_stack = self.query_one("#progress-stack", ProgressStack)
                if existing_state.current_stage > 1:
                    for i in range(1, existing_state.current_stage):
                        progress_stack.set_stage_complete(i)
            else:
                # Start fresh
                clear_state()
                self.state = None
    
    @on(Button.Pressed, "#start-button")
    async def start_analysis(self) -> None:
        """Start or resume the analysis pipeline."""
        if self._analysis_running:
            return
        
        url_input = self.query_one("#url-input", Input)
        commander_url = url_input.value.strip()
        
        if not commander_url:
            self.notify("Please enter a commander URL", severity="error")
            return
        
        if not commander_url.startswith("http"):
            self.notify("Invalid URL format", severity="error")
            return
        
        self._analysis_running = True
        button = self.query_one("#start-button", Button)
        button.disabled = True
        button.label = "Running..."
        
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
        
        progress_stack = self.query_one("#progress-stack", ProgressStack)
        
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
                self.call_from_thread(progress_stack.set_stage_complete, stage_num)
                continue
            
            self.call_from_thread(progress_stack.set_stage_active, stage_num)
            
            def progress_callback(progress: float, message: str) -> None:
                self.call_from_thread(
                    progress_stack.update_stage_progress,
                    stage_num,
                    progress,
                    message,
                )
            
            stage = stage_class(self.state, progress_callback)
            result = await stage.run()
            
            if result.success:
                self.call_from_thread(progress_stack.set_stage_complete, stage_num)
            else:
                self.call_from_thread(
                    progress_stack.set_stage_error,
                    stage_num,
                    result.message,
                )
                self.call_from_thread(
                    self.notify,
                    f"Stage {stage_num} failed: {result.message}",
                    severity="error",
                )
                self.call_from_thread(self._reset_button)
                return
        
        # All stages complete - finalize
        self.call_from_thread(self._finalize_analysis)
    
    def _reset_button(self) -> None:
        """Reset the start button to enabled state."""
        self._analysis_running = False
        button = self.query_one("#start-button", Button)
        button.disabled = False
        button.label = "Start Analysis"
    
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
        
        # Show completion modal
        stats = {
            "decks": self.state.decks_scraped,
            "cards": self.state.cards_analyzed,
        }
        
        async def show_completion() -> None:
            await self.push_screen_wait(
                CompletionModal(self.state.commander_name, stats)
            )
            # Cleanup after modal is dismissed
            self._cleanup()
        
        self.call_later(show_completion)
    
    def _cleanup(self) -> None:
        """Clean up state files after successful completion."""
        # Clear state (keeps the output files but removes tracking)
        clear_state()
        self.state = None
        self._reset_button()
        
        # Reset progress display
        progress_stack = self.query_one("#progress-stack", ProgressStack)
        progress_stack.reset()
        
        self.notify("Analysis complete! Results copied to clipboard.", severity="information")


def main() -> None:
    """Entry point for the application."""
    app = CEDHAnalyzerApp()
    app.run()


if __name__ == "__main__":
    main()
