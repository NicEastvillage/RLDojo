from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dojo_state import DojoState


class BaseGameMode(ABC):
    """Abstract base class for all game modes in Dojo"""
    
    def __init__(self, game_state: 'DojoState', game_interface):
        self.game_state = game_state
        self.game_interface = game_interface
    
    @abstractmethod
    def update(self, packet) -> None:
        """Update the game mode with the current packet"""
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the game mode"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources when switching away from this mode"""
        pass
