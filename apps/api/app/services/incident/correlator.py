from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.incident.stack_parser import ParsedStackFrame

class FrameMatch(BaseModel):
    frame: ParsedStackFrame
    repository_file: Optional[str] = None
    status: str  # MATCHED or UNMATCHED
    confidence: float

class RepositoryCorrelator:
    """
    Correlates extracted stack trace frames with file paths in a RepositorySnapshot.
    Does not fabricate matches; returns MATCHED (confidence 1.0) or UNMATCHED (confidence 0.0).
    """

    @classmethod
    def correlate(cls, frames: List[ParsedStackFrame], repository_snapshot: Optional[Dict[str, Any]]) -> List[FrameMatch]:
        if not repository_snapshot or "tree" not in repository_snapshot:
            return [
                FrameMatch(frame=f, repository_file=None, status="UNMATCHED", confidence=0.0)
                for f in frames
            ]

        tree_nodes = repository_snapshot.get("tree", [])
        repo_paths = [node.get("path", "").replace("\\", "/") for node in tree_nodes if node.get("type") == "file"]

        matches: List[FrameMatch] = []

        for frame in frames:
            frame_file = frame.file.replace("\\", "/").lstrip("/")

            matched_path = None
            # 1. Exact match
            if frame_file in repo_paths:
                matched_path = frame_file
            else:
                # 2. Suffix match (e.g. "src/api/users.ts" matches "app/src/api/users.ts" or "users.ts")
                for rp in repo_paths:
                    if rp.endswith(frame_file) or frame_file.endswith(rp):
                        matched_path = rp
                        break

            if matched_path:
                matches.append(FrameMatch(
                    frame=frame,
                    repository_file=matched_path,
                    status="MATCHED",
                    confidence=1.0
                ))
            else:
                matches.append(FrameMatch(
                    frame=frame,
                    repository_file=None,
                    status="UNMATCHED",
                    confidence=0.0
                ))

        return matches
