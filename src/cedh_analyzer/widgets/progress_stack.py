"""Stacked progress bar widget for pipeline stages."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, ProgressBar, Label
from textual.reactive import reactive


class StageProgress(Static):
    """A single stage progress indicator."""
    
    progress = reactive(0.0)
    status_text = reactive("")
    
    def __init__(
        self,
        stage_name: str,
        stage_num: int,
        total_stages: int,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.stage_name = stage_name
        self.stage_num = stage_num
        self.total_stages = total_stages
        self._complete = False
        self._active = False
    
    def compose(self) -> ComposeResult:
        yield Label(
            f"[{self.stage_num}/{self.total_stages}] {self.stage_name}",
            id=f"stage-label-{self.stage_num}",
        )
        yield ProgressBar(total=100, show_eta=False, id=f"stage-bar-{self.stage_num}")
        yield Label("Waiting...", id=f"stage-status-{self.stage_num}", classes="status-text")
    
    def watch_progress(self, progress: float) -> None:
        """Update the progress bar when progress changes."""
        bar = self.query_one(f"#stage-bar-{self.stage_num}", ProgressBar)
        bar.progress = progress * 100
    
    def watch_status_text(self, text: str) -> None:
        """Update the status text when it changes."""
        status = self.query_one(f"#stage-status-{self.stage_num}", Label)
        status.update(text)
    
    def set_active(self) -> None:
        """Mark this stage as currently active."""
        self._active = True
        self._complete = False
        self.add_class("active")
        self.remove_class("complete")
        self.remove_class("pending")
        self.status_text = "Starting..."
    
    def set_complete(self) -> None:
        """Mark this stage as complete."""
        self._complete = True
        self._active = False
        self.progress = 1.0
        self.add_class("complete")
        self.remove_class("active")
        self.remove_class("pending")
        self.status_text = "✓ Complete"
    
    def set_pending(self) -> None:
        """Mark this stage as pending."""
        self._active = False
        self._complete = False
        self.progress = 0.0
        self.add_class("pending")
        self.remove_class("active")
        self.remove_class("complete")
        self.status_text = "Waiting..."
    
    def set_error(self, message: str) -> None:
        """Mark this stage as errored."""
        self._active = False
        self.add_class("error")
        self.remove_class("active")
        self.status_text = f"✗ {message}"


class ProgressStack(Vertical):
    """A stack of progress bars for all pipeline stages."""
    
    STAGE_NAMES = [
        ("EDH16 Scrape", "Fetching tournament data"),
        ("Moxfield Scrape", "Downloading decklists"),
        ("Preprocess", "Normalizing card data"),
        ("Basic Analytics", "Analyzing card usage"),
        ("Win Rate Analytics", "Calculating performance metrics"),
    ]
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.stages: list[StageProgress] = []
    
    def compose(self) -> ComposeResult:
        yield Label("Analysis Progress", classes="section-header")
        for idx, (name, _) in enumerate(self.STAGE_NAMES):
            stage = StageProgress(
                stage_name=name,
                stage_num=idx + 1,
                total_stages=len(self.STAGE_NAMES),
                id=f"stage-progress-{idx + 1}",
                classes="stage-progress pending",
            )
            self.stages.append(stage)
            yield stage
    
    def set_stage_active(self, stage_num: int) -> None:
        """Mark a stage as active (1-indexed)."""
        for idx, stage in enumerate(self.stages):
            if idx + 1 < stage_num:
                stage.set_complete()
            elif idx + 1 == stage_num:
                stage.set_active()
            else:
                stage.set_pending()
    
    def update_stage_progress(self, stage_num: int, progress: float, message: str = "") -> None:
        """Update progress for a specific stage."""
        if 1 <= stage_num <= len(self.stages):
            stage = self.stages[stage_num - 1]
            stage.progress = progress
            if message:
                stage.status_text = message
    
    def set_stage_complete(self, stage_num: int) -> None:
        """Mark a stage as complete."""
        if 1 <= stage_num <= len(self.stages):
            self.stages[stage_num - 1].set_complete()
    
    def set_stage_error(self, stage_num: int, message: str) -> None:
        """Mark a stage as errored."""
        if 1 <= stage_num <= len(self.stages):
            self.stages[stage_num - 1].set_error(message)
    
    def set_all_complete(self) -> None:
        """Mark all stages as complete."""
        for stage in self.stages:
            stage.set_complete()
    
    def reset(self) -> None:
        """Reset all stages to pending state."""
        for stage in self.stages:
            stage.set_pending()
