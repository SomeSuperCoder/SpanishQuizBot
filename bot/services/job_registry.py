"""
Job registry for tracking active asyncio tasks.

This module provides an in-memory registry for managing background tasks,
specifically for scheduled publication cascades. Tasks are registered with
unique IDs and can be cancelled by users.

Note: This is an in-memory registry. Tasks are lost on bot restart.
This is expected behavior - no persistence is needed.
"""

import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class JobRegistry:
    """
    Registry for tracking active asyncio tasks.
    
    Provides methods to register, cancel, and query active tasks.
    Thread-safe by design (asyncio is single-threaded, but uses locks for safety).
    """
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, task_id: str, task: asyncio.Task) -> None:
        """
        Register a task in the registry.
        
        Args:
            task_id: Unique identifier for the task
            task: The asyncio.Task object to track
        """
        async with self._lock:
            if task_id in self._tasks:
                logger.warning(f"Task {task_id} already registered, replacing")
            self._tasks[task_id] = task
            logger.debug(f"Registered task: {task_id}")
    
    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a registered task.
        
        Args:
            task_id: The task ID to cancel
            
        Returns:
            True if task was found and cancelled, False otherwise
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                logger.debug(f"Task {task_id} not found in registry")
                return False
            
            if task.done():
                logger.debug(f"Task {task_id} already completed, cleaning up")
                del self._tasks[task_id]
                return False
            
            task.cancel()
            logger.info(f"Cancelled task: {task_id}")
            return True
    
    async def unregister(self, task_id: str) -> None:
        """
        Remove a task from the registry (called on completion or cancellation).
        
        Args:
            task_id: The task ID to remove
        """
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.debug(f"Unregistered task: {task_id}")
    
    async def get_active(self) -> Dict[str, asyncio.Task]:
        """
        Get all active tasks.
        
        Returns:
            Dictionary of task_id -> Task for all non-completed tasks
        """
        async with self._lock:
            # Clean up completed tasks
            completed = [tid for tid, task in self._tasks.items() if task.done()]
            for tid in completed:
                del self._tasks[tid]
            
            return self._tasks.copy()
    
    async def get_task_for_chat(self, chat_id: int) -> Optional[str]:
        """
        Find a task ID for a specific chat.
        
        Args:
            chat_id: The chat ID to search for
            
        Returns:
            Task ID if found, None otherwise
        """
        async with self._lock:
            for task_id in self._tasks.keys():
                if f"_{chat_id}_" in task_id:
                    return task_id
            return None


# Module-level singleton instance
job_registry = JobRegistry()
