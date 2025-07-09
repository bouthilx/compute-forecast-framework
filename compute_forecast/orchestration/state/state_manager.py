"""
Simple State Manager for Agent Beta functionality.
Handles session creation, checkpointing, and recovery.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, cast
from dataclasses import dataclass, asdict
from pathlib import Path

from ...pipeline.metadata_collection.models import CollectionConfig


@dataclass
class CheckpointData:
    checkpoint_id: str
    session_id: str
    checkpoint_type: str
    timestamp: datetime
    venues_completed: List[tuple]
    venues_in_progress: List[tuple]
    venues_not_started: List[tuple]
    papers_collected: int
    papers_by_venue: Dict[str, Dict[int, int]]
    last_successful_operation: str
    api_health_status: Dict[str, Any]
    rate_limit_status: Dict[str, Any]
    checksum: str


class SimpleStateManager:
    """Simple implementation of state management for session handling"""

    def __init__(self, storage_dir: str = "session_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, config: CollectionConfig) -> str:
        """Create new collection session"""
        session_id = f"session_{uuid.uuid4().hex[:8]}_{int(time.time())}"

        session_data = {
            "session_id": session_id,
            "config": asdict(config),
            "start_time": datetime.now().isoformat(),
            "status": "created",
            "checkpoints": [],
            "papers_collected": 0,
        }

        # Store in memory and disk
        self.active_sessions[session_id] = session_data
        self._save_session_to_disk(session_id, session_data)

        return session_id

    def save_checkpoint(self, session_id: str, checkpoint_data: CheckpointData) -> str:
        """Save checkpoint for session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        checkpoint_id = f"checkpoint_{uuid.uuid4().hex[:8]}"
        checkpoint_data.checkpoint_id = checkpoint_id

        # Add to session
        session_data = self.active_sessions[session_id]
        session_data["checkpoints"].append(asdict(checkpoint_data))
        session_data["last_checkpoint"] = datetime.now().isoformat()

        # Save to disk
        self._save_session_to_disk(session_id, session_data)

        return checkpoint_id

    def recover_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recover session data from storage"""
        try:
            # Try memory first
            if session_id in self.active_sessions:
                return self.active_sessions[session_id]

            # Try disk
            session_file = self.storage_dir / f"{session_id}.json"
            if session_file.exists():
                with open(session_file, "r") as f:
                    session_data = cast(Dict[str, Any], json.load(f))
                    self.active_sessions[session_id] = session_data
                    return session_data

            return None

        except Exception as e:
            print(f"Failed to recover session {session_id}: {e}")
            return None

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session status"""
        session_data = self.active_sessions.get(session_id)
        if not session_data:
            session_data = self.recover_session(session_id)

        if session_data:
            return {
                "session_id": session_id,
                "status": session_data.get("status", "unknown"),
                "start_time": session_data.get("start_time"),
                "papers_collected": session_data.get("papers_collected", 0),
                "checkpoint_count": len(session_data.get("checkpoints", [])),
            }

        return None

    def list_active_sessions(self) -> List[str]:
        """List all active session IDs"""
        return list(self.active_sessions.keys())

    def _save_session_to_disk(self, session_id: str, session_data: Dict[str, Any]):
        """Save session data to disk"""
        try:
            session_file = self.storage_dir / f"{session_id}.json"
            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save session {session_id} to disk: {e}")

    def update_session_progress(
        self, session_id: str, papers_collected: int, status: Optional[str] = None
    ):
        """Update session progress"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["papers_collected"] = papers_collected
            if status:
                self.active_sessions[session_id]["status"] = status
            self.active_sessions[session_id]["last_updated"] = (
                datetime.now().isoformat()
            )

            # Save to disk
            self._save_session_to_disk(session_id, self.active_sessions[session_id])
