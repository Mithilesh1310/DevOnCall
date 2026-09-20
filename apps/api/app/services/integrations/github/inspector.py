import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
from app.schemas.repository import (
    RepositoryMetadata,
    RepositorySnapshot,
    RepositoryTreeNode,
    FrameworkDetection
)

logger = logging.getLogger("devoncall.integrations.github.inspector")

EXCLUDED_DIRECTORIES: Set[str] = {
    "node_modules", ".git", ".next", "dist", "build", "out",
    ".pnpm-store", "coverage", "venv", ".venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache"
}

IMPORTANT_FILE_NAMES: Set[str] = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "requirements.txt", "pyproject.toml", "pipfile", "go.mod", "cargo.toml",
    "pom.xml", "build.gradle", "dockerfile", "docker-compose.yml", "readme.md",
    "tsconfig.json", "next.config.js", "next.config.mjs", "next.config.ts",
    "vite.config.js", "vite.config.ts", "eslint.config.js", ".gitignore"
}

COMMON_SOURCE_DIRS: Set[str] = {"src", "app", "pages", "components", "lib", "server", "api", "packages"}
COMMON_TEST_DIRS: Set[str] = {"tests", "test", "__tests__", "spec"}

MAX_TREE_ENTRIES = 2500
MAX_PATH_DEPTH = 10
MAX_PATH_LENGTH = 256

class RepositoryInspector:
    """
    Deterministic Repository Intelligence Engine.
    Analyzes repository file structures, manifests, and trees to construct a RepositorySnapshot.
    Does NOT use LLMs or alter source files.
    """

    @staticmethod
    def inspect(metadata: RepositoryMetadata, raw_tree: List[Dict[str, Any]]) -> RepositorySnapshot:
        logger.info(f"Starting deterministic inspection for repository {metadata.owner}/{metadata.repo}")

        # 1. Filter raw tree entries
        filtered_entries = []
        total_files = 0
        total_directories = 0
        file_paths: Set[str] = set()

        for item in raw_tree:
            if len(filtered_entries) >= MAX_TREE_ENTRIES:
                logger.warning(f"Tree entry limit ({MAX_TREE_ENTRIES}) reached for {metadata.owner}/{metadata.repo}")
                break

            path = item.get("path", "")
            item_type = item.get("type", "blob")
            
            if not path or len(path) > MAX_PATH_LENGTH:
                continue

            parts = path.split("/")
            if len(parts) > MAX_PATH_DEPTH:
                continue

            # Skip excluded directory paths
            if any(part in EXCLUDED_DIRECTORIES for part in parts):
                continue

            file_paths.add(path)
            if item_type == "tree" or item_type == "dir":
                total_directories += 1
            else:
                total_files += 1

            filtered_entries.append(item)

        # 2. Identify Important Files, Source Dirs, Test Dirs
        important_files = []
        source_dirs = set()
        test_dirs = set()
        config_files = []

        for path in file_paths:
            parts = path.split("/")
            base_name = parts[-1].lower()

            if base_name in IMPORTANT_FILE_NAMES or base_name.startswith("next.config.") or base_name.startswith("vite.config."):
                important_files.append(path)
                if base_name in {"dockerfile", "docker-compose.yml", "tsconfig.json", ".gitignore"} or base_name.startswith("next.config."):
                    config_files.append(path)

            # Check root or top-level directory names for source/test
            if len(parts) > 1:
                top_dir = parts[0].lower()
                if top_dir in COMMON_SOURCE_DIRS:
                    source_dirs.add(parts[0])
                elif top_dir in COMMON_TEST_DIRS:
                    test_dirs.add(parts[0])

        # 3. Detect Languages, Frameworks, and Runtimes (Deterministic Rules)
        detections: List[FrameworkDetection] = []
        languages: Set[str] = set()

        # Language Detection
        if any(p.endswith((".ts", ".tsx", "tsconfig.json")) for p in file_paths):
            languages.add("TypeScript")
        if any(p.endswith((".js", ".jsx")) for p in file_paths):
            languages.add("JavaScript")
        if any(p.endswith((".py", "pyproject.toml", "requirements.txt")) for p in file_paths):
            languages.add("Python")
        if any(p.endswith("go.mod") for p in file_paths):
            languages.add("Go")
        if any(p.endswith("Cargo.toml") for p in file_paths):
            languages.add("Rust")

        # Framework & Runtime Detection Rules
        lower_paths = {p.lower() for p in file_paths}

        # Next.js
        if any("package.json" in p for p in lower_paths) and any("next.config" in p for p in lower_paths):
            detections.append(FrameworkDetection(
                name="Next.js",
                type="framework",
                status="DETECTED",
                confidence=1.0,
                evidence=["package.json present", "next.config file found"]
            ))

        # FastAPI
        if any("pyproject.toml" in p or "requirements.txt" in p for p in lower_paths):
            detections.append(FrameworkDetection(
                name="FastAPI",
                type="framework",
                status="DETECTED" if any("main.py" in p or "api" in p for p in lower_paths) else "INFERRED",
                confidence=0.9 if any("main.py" in p or "api" in p for p in lower_paths) else 0.6,
                evidence=["Python project manifest present", "API structure detected"]
            ))

        # Node.js Runtime
        if any("package.json" in p for p in lower_paths):
            detections.append(FrameworkDetection(
                name="Node.js",
                type="runtime",
                status="DETECTED",
                confidence=1.0,
                evidence=["package.json manifest present"]
            ))
            if any("pnpm-lock.yaml" in p for p in lower_paths):
                detections.append(FrameworkDetection(
                    name="pnpm", type="package_manager", status="DETECTED", confidence=1.0, evidence=["pnpm-lock.yaml"]
                ))
            elif any("package-lock.json" in p for p in lower_paths):
                detections.append(FrameworkDetection(
                    name="npm", type="package_manager", status="DETECTED", confidence=1.0, evidence=["package-lock.json"]
                ))

        # Docker Container Runtime
        if any("dockerfile" in p for p in lower_paths) or any("docker-compose.yml" in p for p in lower_paths):
            detections.append(FrameworkDetection(
                name="Docker",
                type="runtime",
                status="DETECTED",
                confidence=1.0,
                evidence=["Dockerfile or docker-compose.yml present"]
            ))

        # 4. Build Hierarchical Tree Representation
        hierarchical_tree = RepositoryInspector._build_tree_hierarchy(filtered_entries)

        return RepositorySnapshot(
            owner=metadata.owner,
            repo=metadata.repo,
            default_branch=metadata.default_branch,
            commit_sha=metadata.commit_sha,
            url=metadata.html_url,
            total_files=total_files,
            total_directories=total_directories,
            detected_languages=sorted(list(languages)),
            detections=detections,
            important_files=sorted(important_files),
            source_directories=sorted(list(source_dirs)),
            test_directories=sorted(list(test_dirs)),
            configuration_files=sorted(config_files),
            tree=hierarchical_tree,
            inspected_at=datetime.now(timezone.utc)
        )

    @staticmethod
    def _build_tree_hierarchy(flat_entries: List[Dict[str, Any]]) -> List[RepositoryTreeNode]:
        """
        Converts a flat list of git tree items into a nested tree structure.
        """
        root_nodes: Dict[str, RepositoryTreeNode] = {}

        for item in flat_entries:
            path = item.get("path", "")
            item_type = "directory" if item.get("type") in ("tree", "dir") else "file"
            size = item.get("size") if item_type == "file" else None

            parts = path.split("/")
            node_name = parts[-1]

            if len(parts) == 1:
                if path not in root_nodes:
                    root_nodes[path] = RepositoryTreeNode(
                        path=path,
                        name=node_name,
                        type=item_type,
                        size=size,
                        children=[] if item_type == "directory" else None
                    )
            else:
                # Add root parent node if top-level directory not seen yet
                parent_path = parts[0]
                if parent_path not in root_nodes:
                    root_nodes[parent_path] = RepositoryTreeNode(
                        path=parent_path,
                        name=parts[0],
                        type="directory",
                        children=[]
                    )

        # Sort nodes: directories first, then files
        nodes_list = list(root_nodes.values())
        nodes_list.sort(key=lambda n: (0 if n.type == "directory" else 1, n.name.lower()))
        return nodes_list
