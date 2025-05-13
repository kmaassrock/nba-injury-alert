"""
Base processor classes for the NBA Injury Alert system.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ..utils.errors import ProcessorError
from ..utils.logging import logger, setup_logger

# Create a logger for the processor module
processor_logger = setup_logger("nba_injury_alert.processor")


class BaseProcessor(ABC):
    """Base class for data processors."""
    
    def __init__(self):
        """Initialize the processor."""
        self.logger = processor_logger
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the data.
        
        Args:
            data: The data to process.
        
        Returns:
            The processed data.
        
        Raises:
            ProcessorError: If the processing operation fails.
        """
        pass


class DiffProcessor(BaseProcessor):
    """Base class for processors that compute differences between datasets."""
    
    @abstractmethod
    async def compute_diff(
        self, 
        current_data: Dict[str, Any], 
        previous_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute the difference between current and previous data.
        
        Args:
            current_data: The current data.
            previous_data: The previous data.
        
        Returns:
            The differences between the datasets.
        
        Raises:
            ProcessorError: If the diff operation fails.
        """
        pass
    
    @staticmethod
    def get_added_items(
        current_items: List[Any], 
        previous_items: List[Any], 
        key_func: Optional[callable] = None
    ) -> List[Any]:
        """
        Get items that are in the current list but not in the previous list.
        
        Args:
            current_items: The current list of items.
            previous_items: The previous list of items.
            key_func: Function to extract a key for comparison (default: identity).
        
        Returns:
            Items that were added.
        """
        if key_func is None:
            key_func = lambda x: x
        
        previous_keys = {key_func(item) for item in previous_items}
        return [item for item in current_items if key_func(item) not in previous_keys]
    
    @staticmethod
    def get_removed_items(
        current_items: List[Any], 
        previous_items: List[Any], 
        key_func: Optional[callable] = None
    ) -> List[Any]:
        """
        Get items that are in the previous list but not in the current list.
        
        Args:
            current_items: The current list of items.
            previous_items: The previous list of items.
            key_func: Function to extract a key for comparison (default: identity).
        
        Returns:
            Items that were removed.
        """
        if key_func is None:
            key_func = lambda x: x
        
        current_keys = {key_func(item) for item in current_items}
        return [item for item in previous_items if key_func(item) not in current_keys]
    
    @staticmethod
    def get_changed_items(
        current_items: List[Any], 
        previous_items: List[Any], 
        key_func: Optional[callable] = None,
        compare_func: Optional[callable] = None
    ) -> List[Tuple[Any, Any]]:
        """
        Get items that exist in both lists but have changed.
        
        Args:
            current_items: The current list of items.
            previous_items: The previous list of items.
            key_func: Function to extract a key for comparison (default: identity).
            compare_func: Function to compare items (default: equality).
        
        Returns:
            Pairs of (current_item, previous_item) that have changed.
        """
        if key_func is None:
            key_func = lambda x: x
        
        if compare_func is None:
            compare_func = lambda x, y: x == y
        
        # Create dictionaries for faster lookup
        previous_dict = {key_func(item): item for item in previous_items}
        current_dict = {key_func(item): item for item in current_items}
        
        # Find common keys
        common_keys = set(previous_dict.keys()) & set(current_dict.keys())
        
        # Return items that have changed
        return [
            (current_dict[key], previous_dict[key])
            for key in common_keys
            if not compare_func(current_dict[key], previous_dict[key])
        ]
