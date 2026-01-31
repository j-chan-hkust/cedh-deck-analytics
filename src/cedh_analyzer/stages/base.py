"""Base class for analysis pipeline stages."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..state import AnalysisState


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""
    
    success: bool
    message: str = ""
    data: dict[str, Any] | None = None


class Stage(ABC):
    """Base class for analysis pipeline stages."""
    
    name: str = "Base Stage"
    description: str = "Base stage description"
    
    def __init__(self, state: AnalysisState):
        """
        Initialize the stage.
        
        Args:
            state: Current analysis state
        """
        self.state = state
    
    @abstractmethod
    async def run(self) -> StageResult:
        """
        Execute the stage.
        
        Returns:
            StageResult indicating success/failure and any output data
        """
        pass
    
    @abstractmethod
    def is_complete(self) -> bool:
        """Check if this stage has already been completed."""
        pass
