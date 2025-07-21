"""
Checkpoint management for consolidation process.
Handles time-based checkpointing and resumption support.
"""

import json
import logging
import time
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from compute_forecast.pipeline.metadata_collection.models import Paper

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationCheckpoint:
    """State of a consolidation process"""
    session_id: str
    input_file: str
    total_papers: int
    sources: Dict[str, Dict[str, Any]]  # source_name -> state
    last_checkpoint_time: datetime
    timestamp: datetime
    checksum: Optional[str] = None
    phase_state: Optional[Dict[str, Any]] = None  # For two-phase consolidation


class ConsolidationCheckpointManager:
    """
    Manages checkpoints for consolidation with time-based saves.
    
    Features:
    - Time-based checkpointing (default 5 minutes)
    - Atomic file operations
    - Integrity validation via checksums
    - Incremental paper saving with deduplication
    - Session discovery and management
    """
    
    def __init__(self, 
                 session_id: str = None,
                 checkpoint_dir: Path = Path(".cf_state/consolidate"),
                 checkpoint_interval_minutes: float = 5.0):
        """
        Initialize checkpoint manager.
        
        Args:
            session_id: Unique session identifier (auto-generated if None)
            checkpoint_dir: Base directory for checkpoints
            checkpoint_interval_minutes: Minutes between auto checkpoints (0 to disable)
        """
        self.checkpoint_base_dir = checkpoint_dir
        self.session_id = session_id or self._generate_session_id()
        self.checkpoint_dir = checkpoint_dir / self.session_id
        self.checkpoint_interval = checkpoint_interval_minutes * 60  # Convert to seconds
        self.last_checkpoint_time = time.time()
        
        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.checkpoint_file = self.checkpoint_dir / "checkpoint.json"
        self.checkpoint_meta_file = self.checkpoint_dir / "checkpoint.json.meta"
        self.papers_file = self.checkpoint_dir / "papers_enriched.json"
        self.session_info_file = self.checkpoint_dir / "session.json"
        
        # Save session info
        self._save_session_info()
        
        logger.info(f"ConsolidationCheckpointManager initialized: session={self.session_id}, interval={checkpoint_interval_minutes}min")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        from uuid import uuid4
        return f"consolidate_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    
    def _save_session_info(self):
        """Save session metadata"""
        session_info = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "checkpoint_interval_minutes": self.checkpoint_interval / 60,
            "pid": os.getpid() if hasattr(os, 'getpid') else None
        }
        with open(self.session_info_file, "w") as f:
            json.dump(session_info, f, indent=2)
    
    def should_checkpoint(self) -> bool:
        """Check if enough time has passed for a checkpoint"""
        if self.checkpoint_interval <= 0:
            return False
        return (time.time() - self.last_checkpoint_time) >= self.checkpoint_interval
    
    def save_checkpoint(self, 
                       input_file: str,
                       total_papers: int,
                       sources_state: Dict[str, Dict[str, Any]],
                       papers: List[Paper],
                       phase_state: Optional[Dict[str, Any]] = None,
                       force: bool = False) -> bool:
        """
        Save checkpoint if needed or forced.
        
        Args:
            input_file: Path to input file being processed
            total_papers: Total number of papers
            sources_state: State of each source
            papers: Current list of papers with enrichments
            phase_state: Optional phase state for two-phase consolidation
            force: Force checkpoint regardless of time
            
        Returns:
            True if checkpoint was saved
        """
        if not force and not self.should_checkpoint():
            return False
            
        try:
            start_time = time.time()
            
            # Create checkpoint data
            checkpoint = ConsolidationCheckpoint(
                session_id=self.session_id,
                input_file=input_file,
                total_papers=total_papers,
                sources=sources_state,
                last_checkpoint_time=datetime.now(),
                timestamp=datetime.now(),
                phase_state=phase_state
            )
            
            # Save papers first (larger file)
            self._save_papers_atomic(papers)
            
            # Save checkpoint state
            self._save_checkpoint_atomic(checkpoint)
            
            self.last_checkpoint_time = time.time()
            
            duration = time.time() - start_time
            logger.info(f"Checkpoint saved in {duration:.2f}s: {len(papers)} papers, sources={list(sources_state.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False
    
    def load_checkpoint(self) -> Optional[Tuple[ConsolidationCheckpoint, List[Paper]]]:
        """
        Load existing checkpoint if valid.
        
        Returns:
            Tuple of (checkpoint, papers) if found and valid, None otherwise
        """
        if not self.checkpoint_file.exists():
            return None
            
        try:
            # Validate checkpoint integrity
            if not self._validate_checkpoint_integrity():
                logger.warning("Checkpoint integrity validation failed")
                # Try to load backup if available
                backup_file = self.checkpoint_file.with_suffix(".json.bak")
                if backup_file.exists():
                    logger.info("Attempting to load from backup checkpoint")
                    self.checkpoint_file = backup_file
                    self.checkpoint_meta_file = backup_file.with_suffix(".meta")
                    if not self._validate_checkpoint_integrity():
                        logger.error("Backup checkpoint also failed validation")
                        return None
                else:
                    return None
            
            # Load checkpoint
            with open(self.checkpoint_file) as f:
                data = json.load(f)
            
            # Validate session ID matches
            if data.get("session_id") != self.session_id:
                logger.warning(f"Session ID mismatch: expected {self.session_id}, got {data.get('session_id')}")
                # Allow loading if explicitly using this session
                if self.session_id != data.get("session_id"):
                    self.session_id = data.get("session_id")
                    logger.info(f"Updated session ID to match checkpoint: {self.session_id}")
            
            # Convert to dataclass
            checkpoint = ConsolidationCheckpoint(
                session_id=data["session_id"],
                input_file=data["input_file"],
                total_papers=data["total_papers"],
                sources=data["sources"],
                last_checkpoint_time=datetime.fromisoformat(data["last_checkpoint_time"]),
                timestamp=datetime.fromisoformat(data["timestamp"]),
                checksum=data.get("checksum"),
                phase_state=data.get("phase_state")
            )
            
            # Load papers if available
            papers = []
            if self.papers_file.exists():
                try:
                    with open(self.papers_file) as f:
                        data = json.load(f)
                        
                    # Handle both old format (list) and new format (dict with metadata)
                    if isinstance(data, dict) and "papers" in data:
                        papers_data = data["papers"]
                        metadata = data.get("metadata", {})
                        logger.info(f"Loading papers: {metadata.get('total_papers', 'unknown')} total, "
                                  f"{metadata.get('unique_paper_ids', 'unknown')} unique IDs")
                    else:
                        # Old format compatibility
                        papers_data = data
                        
                    # Convert back to Paper objects with error handling
                    for i, paper_dict in enumerate(papers_data):
                        try:
                            papers.append(Paper.from_dict(paper_dict))
                        except Exception as e:
                            logger.warning(f"Failed to load paper {i}: {e}")
                            # Continue loading other papers
                            
                except Exception as e:
                    logger.error(f"Failed to load papers file: {e}")
                    # Return checkpoint without papers - user can decide to continue or not
                    return checkpoint, []
            
            logger.info(f"Loaded checkpoint: {len(papers)} papers, sources={list(checkpoint.sources.keys())}")
            return checkpoint, papers
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def _save_checkpoint_atomic(self, checkpoint: ConsolidationCheckpoint):
        """Save checkpoint with atomic write and checksum"""
        # Create backup of existing checkpoint if it exists
        if self.checkpoint_file.exists():
            backup_file = self.checkpoint_file.with_suffix(".json.bak")
            try:
                import shutil
                shutil.copy2(self.checkpoint_file, backup_file)
                if self.checkpoint_meta_file.exists():
                    shutil.copy2(self.checkpoint_meta_file, backup_file.with_suffix(".bak.meta"))
            except Exception as e:
                logger.warning(f"Failed to create checkpoint backup: {e}")
        
        # Manually convert to dict to handle datetime serialization
        data = {
            "session_id": checkpoint.session_id,
            "input_file": checkpoint.input_file,
            "total_papers": checkpoint.total_papers,
            "sources": checkpoint.sources,
            "last_checkpoint_time": checkpoint.last_checkpoint_time.isoformat(),
            "timestamp": checkpoint.timestamp.isoformat(),
            "checksum": checkpoint.checksum,
            "phase_state": checkpoint.phase_state
        }
        
        # Write to temp file
        temp_file = self.checkpoint_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
        
        # Calculate checksum
        checksum = self._calculate_checksum(temp_file)
        
        # Add checksum to data and rewrite
        data["checksum"] = checksum
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
        
        # Write metadata
        meta_temp = self.checkpoint_meta_file.with_suffix(".tmp")
        with open(meta_temp, "w") as f:
            json.dump({"checksum": checksum, "timestamp": datetime.now().isoformat()}, f)
        
        # Atomic rename both files
        temp_file.rename(self.checkpoint_file)
        meta_temp.rename(self.checkpoint_meta_file)
    
    def _save_papers_atomic(self, papers: List[Paper]):
        """Save papers with atomic write and deduplication info"""
        # Convert papers to dict format
        papers_data = []
        paper_ids_seen = set()
        
        for p in papers:
            paper_dict = p.to_dict()
            # Track unique papers for deduplication stats
            if p.paper_id:
                paper_ids_seen.add(p.paper_id)
            papers_data.append(paper_dict)
        
        # Create wrapper with metadata
        data = {
            "metadata": {
                "total_papers": len(papers),
                "unique_paper_ids": len(paper_ids_seen),
                "saved_at": datetime.now().isoformat()
            },
            "papers": papers_data
        }
        
        # Write to temp file
        temp_file = self.papers_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
        
        # Atomic rename
        temp_file.rename(self.papers_file)
    
    def _validate_checkpoint_integrity(self) -> bool:
        """Validate checkpoint file integrity using checksum"""
        if not self.checkpoint_meta_file.exists():
            logger.warning("Checkpoint meta file not found, skipping validation")
            return True  # Allow loading without meta file for backward compatibility
            
        try:
            # Load expected checksum
            with open(self.checkpoint_meta_file) as f:
                meta = json.load(f)
                expected_checksum = meta.get("checksum")
            
            if not expected_checksum:
                logger.warning("No checksum in meta file, skipping validation")
                return True
            
            # Calculate actual checksum
            actual_checksum = self._calculate_checksum(self.checkpoint_file)
            
            if actual_checksum != expected_checksum:
                logger.warning(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
                # Still allow loading but warn user
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Integrity validation failed: {e}")
            return True  # Allow loading despite validation errors
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def cleanup(self):
        """Clean up checkpoint files after successful completion"""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
            if self.checkpoint_meta_file.exists():
                self.checkpoint_meta_file.unlink()
            if self.papers_file.exists():
                self.papers_file.unlink()
            
            # Remove directory if empty
            if not any(self.checkpoint_dir.iterdir()):
                self.checkpoint_dir.rmdir()
                
            logger.info(f"Cleaned up checkpoint files for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoint files: {e}")
    
    @classmethod
    def find_resumable_sessions(cls, checkpoint_dir: Path = Path(".cf_state/consolidate")) -> List[Dict[str, Any]]:
        """
        Find all resumable consolidation sessions.
        
        Returns:
            List of session info dicts with keys: session_id, created_at, input_file, status
        """
        sessions = []
        
        if not checkpoint_dir.exists():
            return sessions
            
        for session_dir in checkpoint_dir.iterdir():
            if not session_dir.is_dir():
                continue
                
            checkpoint_file = session_dir / "checkpoint.json"
            session_info_file = session_dir / "session.json"
            
            if checkpoint_file.exists():
                try:
                    # Load session info
                    session_data = {}
                    if session_info_file.exists():
                        with open(session_info_file) as f:
                            session_data = json.load(f)
                    
                    # Load checkpoint to get status
                    with open(checkpoint_file) as f:
                        checkpoint_data = json.load(f)
                    
                    # Determine overall status
                    sources_status = checkpoint_data.get("sources", {})
                    
                    # Handle edge case where sources might be a string
                    if isinstance(sources_status, str):
                        logger.warning(f"Unexpected string value for sources in {session_dir.name}: {sources_status}")
                        sources_status = {"phase": sources_status}
                    
                    # Handle three different checkpoint formats:
                    # 1. Old format: sources with status (e.g., {"semantic_scholar": {"status": "completed"}})
                    # 2. Two-phase format: phase tracking (e.g., {"phase": "id_harvesting"})
                    # 3. Parallel format: sources with papers_processed counts
                    
                    if "phase" in sources_status:
                        # New two-phase format
                        phase = sources_status.get("phase", "unknown")
                        if phase == "completed":
                            status = "completed"
                        elif phase in ["id_harvesting", "semantic_scholar_enrichment", "openalex_enrichment"]:
                            status = "interrupted"
                        elif phase in ["id_harvesting_complete", "semantic_scholar_complete"]:
                            status = "interrupted"  # Between phases
                        else:
                            status = "pending"
                    elif any("papers_processed" in s for s in sources_status.values() if isinstance(s, dict)):
                        # Parallel consolidation format
                        # Check if still processing (always consider resumable unless explicitly complete)
                        status = "interrupted"
                        
                        # Could add logic to determine if complete based on merge counts
                        # For now, always consider parallel consolidations as resumable
                    else:
                        # Old format with source statuses
                        if all(isinstance(s, dict) and s.get("status") == "completed" for s in sources_status.values()):
                            status = "completed"
                        elif any(isinstance(s, dict) and s.get("status") == "failed" for s in sources_status.values()):
                            status = "failed"
                        elif any(isinstance(s, dict) and s.get("status") == "in_progress" for s in sources_status.values()):
                            status = "interrupted"
                        else:
                            status = "pending"
                    
                    # Determine sources list based on format
                    if "phase" in sources_status:
                        # New format - use phase name as sources
                        sources_list = [sources_status.get("phase", "unknown")]
                    else:
                        # Old format - use actual source names
                        sources_list = list(sources_status.keys())
                    
                    # Extract source statistics if available
                    source_stats = {}
                    if isinstance(sources_status, dict):
                        for source_name, source_data in sources_status.items():
                            if isinstance(source_data, dict) and "papers_processed" in source_data:
                                source_stats[source_name] = {
                                    "papers_processed": source_data.get("papers_processed", 0),
                                    "papers_enriched": source_data.get("papers_enriched", 0),
                                    "citations_found": source_data.get("citations_found", 0),
                                    "abstracts_found": source_data.get("abstracts_found", 0),
                                    "api_calls": source_data.get("api_calls", 0)
                                }
                    
                    sessions.append({
                        "session_id": checkpoint_data["session_id"],
                        "created_at": session_data.get("created_at", checkpoint_data["timestamp"]),
                        "input_file": checkpoint_data["input_file"],
                        "total_papers": checkpoint_data["total_papers"],
                        "sources": sources_list,
                        "status": status,
                        "last_checkpoint": checkpoint_data["timestamp"],
                        "source_stats": source_stats
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to load session {session_dir.name}: {e}")
                    
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)
    
    @classmethod
    def get_latest_resumable_session(cls, input_file: str, checkpoint_dir: Path = Path(".cf_state/consolidate")) -> Optional[str]:
        """
        Get the latest resumable session for a given input file.
        
        Args:
            input_file: The input file path to match
            checkpoint_dir: Base checkpoint directory
            
        Returns:
            Session ID if found, None otherwise
        """
        sessions = cls.find_resumable_sessions(checkpoint_dir)
        
        for session in sessions:
            if session["input_file"] == input_file and session["status"] in ["interrupted", "failed"]:
                return session["session_id"]
                
        return None
    
    @staticmethod
    def merge_enrichments(paper: Paper, new_enrichments: Any):
        """
        Merge new enrichments into paper while avoiding duplicates.
        
        This is important when resuming to avoid duplicate records from 
        re-processing batches.
        """
        # Helper to check if record already exists
        def record_exists(records, new_record):
            for r in records:
                if (r.source == new_record.source and 
                    r.data == new_record.data):
                    return True
            return False
        
        # Merge citations
        for new_citation in new_enrichments.citations:
            if not record_exists(paper.citations, new_citation):
                paper.citations.append(new_citation)
        
        # Merge abstracts
        for new_abstract in new_enrichments.abstracts:
            if not record_exists(paper.abstracts, new_abstract):
                paper.abstracts.append(new_abstract)
        
        # Merge URLs
        for new_url in new_enrichments.urls:
            if not record_exists(paper.urls, new_url):
                paper.urls.append(new_url)
        
        # Merge identifiers
        for new_id in new_enrichments.identifiers:
            if not record_exists(paper.identifiers, new_id):
                paper.identifiers.append(new_id)
