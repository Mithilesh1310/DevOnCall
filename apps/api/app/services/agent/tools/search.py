import os
from typing import Dict, Any, List
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.workspace import default_workspace_manager

class SearchRepositoryTool(BaseTool):
    """
    Searches repository tree paths, file names, and text content inside workspace files.
    """

    @property
    def name(self) -> str:
        return "search_repository"

    @property
    def description(self) -> str:
        return "Searches repository file paths, directory names, and file text content matching a search query."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        query = input_params.get("query", "").strip().lower()
        if not query:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="INVALID_INPUT", message="Parameter 'query' is required.")
            )

        max_results = input_params.get("max_results", 50)
        path_filter = input_params.get("path", "").strip().lower()

        matches: List[Dict[str, Any]] = []

        # 1. Search snapshot tree
        if context.repository_snapshot:
            tree = context.repository_snapshot.get("tree", [])
            for node in tree:
                if len(matches) >= max_results:
                    break
                
                node_path = node.get("path", "").lower()
                if path_filter and not node_path.startswith(path_filter):
                    continue

                if query in node_path or query in node.get("name", "").lower():
                    matches.append(node)

        # 2. Search workspace file text content if workspace exists
        ws_root = default_workspace_manager.get_workspace_root(context.run_id)
        if os.path.exists(ws_root):
            for root, _, files in os.walk(ws_root):
                if len(matches) >= max_results:
                    break
                for file in files:
                    if len(matches) >= max_results:
                        break
                    rel_path = os.path.relpath(os.path.join(root, file), ws_root).replace("\\", "/")
                    if any(p in rel_path for p in [".git", ".env"]):
                        continue
                    if path_filter and not rel_path.lower().startswith(path_filter):
                        continue

                    abs_path = os.path.join(root, file)
                    try:
                        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                            lines = f.readlines()
                        for idx, line in enumerate(lines, start=1):
                            if query in line.lower():
                                matches.append({
                                    "path": rel_path,
                                    "type": "content_match",
                                    "line_number": idx,
                                    "line_content": line.strip()
                                })
                                if len(matches) >= max_results:
                                    break
                    except Exception:
                        pass

        data = {
            "query": query,
            "total_matches": len(matches),
            "results": matches
        }
        return ToolResult(success=True, tool=self.name, data=data)

