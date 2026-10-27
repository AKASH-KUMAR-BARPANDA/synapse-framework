"""Skills module for specialized agent instructions, personas, and domain knowledge."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


class Skill:
    """Represents a discrete skill, persona, or behavioral capability for Synapse.

    Skills package natural language instructions (typically loaded from Markdown files
    with optional YAML frontmatter), domain guidelines, and optional tool associations
    that guide the model's responses.

    Example:
        ```python
        from synapse.skills import makeskills

        # From a markdown file:
        skill = makeskills("skills/python_expert.md")

        # Or inline:
        reviewer = makeskills(
            prompt="# PR Reviewer\nCarefully inspect code diffs for edge cases.",
            name="reviewer",
            description="Reviews code PRs for performance and edge cases",
        )
        ```
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        instructions: str = "",
        tools: list[Any] | None = None,
        tags: list[str] | None = None,
        path: str | Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initializes a Skill instance.

        Args:
            name: Human-readable identifier for the skill.
            description: Concise summary of what this skill does.
            instructions: Full markdown instructions given to the LLM.
            tools: Optional list of callables or connector tools associated with the skill.
            tags: Categorical tags (e.g. ['coding', 'review', 'research']).
            path: Optional source filesystem path if loaded from disk.
            metadata: Arbitrary additional properties.
        """
        self.name = name
        self.description = description
        self.instructions = instructions.strip()
        self.tools = list(tools or [])
        self.tags = list(tags or [])
        self.path = Path(path).resolve() if path else None
        self.metadata = dict(metadata or {})

    @property
    def prompt(self) -> str:
        """Alias for instructions."""
        return self.instructions

    def format_prompt(self) -> str:
        """Renders the skill into a formatted system prompt section."""
        lines = [f"### SKILL: {self.name}"]
        if self.description:
            lines.append(f"Description: {self.description}")
        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")
        lines.append("")
        lines.append(self.instructions)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the skill metadata into a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "tags": self.tags,
            "tools": [getattr(t, "name", str(t)) for t in self.tools],
            "path": str(self.path) if self.path else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_markdown(
        cls,
        content: str,
        name: str | None = None,
        description: str | None = None,
        tools: list[Any] | None = None,
        tags: list[str] | None = None,
        path: str | Path | None = None,
        **extra_metadata: Any,
    ) -> Skill:
        """Parses a markdown string with optional YAML frontmatter into a Skill.

        Args:
            content: Markdown content string.
            name: Optional explicit name override.
            description: Optional description override.
            tools: Associated tools.
            tags: Categorical tags.
            path: Optional source path.
            **extra_metadata: Additional metadata fields.

        Returns:
            A populated Skill instance.
        """
        text = content.strip()
        frontmatter: dict[str, Any] = {}
        body = text

        # Check for YAML frontmatter block: --- ... ---
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                raw_yaml = parts[1].strip()
                body = parts[2].strip()
                if yaml:
                    try:
                        parsed = yaml.safe_load(raw_yaml)
                        if isinstance(parsed, dict):
                            frontmatter = parsed
                    except Exception:
                        pass  # nosec B110
                else:
                    # Fallback simple line parser if PyYAML is not present
                    for line in raw_yaml.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            frontmatter[k.strip()] = v.strip().strip("\"'")

        # Infer name if not specified
        resolved_name = (
            name
            or frontmatter.get("name")
            or frontmatter.get("title")
        )
        if not resolved_name:
            # Try to grab top markdown header: # Skill Name
            match = re.search(r"^#+\s+(.+)$", body, re.MULTILINE)
            if match:
                resolved_name = match.group(1).strip()
            elif path:
                resolved_name = Path(path).stem.replace("_", " ").replace("-", " ").title()
            else:
                resolved_name = "Custom Skill"

        # Infer description if not specified
        resolved_desc = (
            description
            or frontmatter.get("description")
            or frontmatter.get("summary")
            or ""
        )
        if not resolved_desc:
            # Grab the first non-header paragraph
            for para in body.split("\n\n"):
                para_clean = para.strip()
                if para_clean and not para_clean.startswith("#"):
                    resolved_desc = para_clean[:200]
                    break

        resolved_tags = list(tags or frontmatter.get("tags") or [])
        merged_meta = {**frontmatter, **extra_metadata}

        return cls(
            name=str(resolved_name),
            description=str(resolved_desc),
            instructions=body,
            tools=tools,
            tags=resolved_tags,
            path=path,
            metadata=merged_meta,
        )

    @classmethod
    def from_file(
        cls,
        file_path: str | Path,
        name: str | None = None,
        description: str | None = None,
        tools: list[Any] | None = None,
        tags: list[str] | None = None,
        **extra_metadata: Any,
    ) -> Skill:
        """Loads a Skill from a Markdown or text file on disk.

        Args:
            file_path: Filesystem path to the skill file (.md, .txt).
            name: Optional explicit skill name override.
            description: Optional description override.
            tools: Associated tools.
            tags: Categorical tags.
            **extra_metadata: Additional metadata fields.

        Returns:
            A populated Skill instance.

        Raises:
            FileNotFoundError: If the specified file does not exist.
        """
        p = Path(file_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Skill file not found at: {p}")

        content = p.read_text(encoding="utf-8")
        return cls.from_markdown(
            content=content,
            name=name,
            description=description,
            tools=tools,
            tags=tags,
            path=p,
            **extra_metadata,
        )

    def __repr__(self) -> str:
        return f"<Skill name='{self.name}' description='{self.description[:40]}...'>"


def makeskills(
    prompt: str | Path | Skill,
    name: str | None = None,
    description: str | None = None,
    tools: list[Any] | None = None,
    tags: list[str] | None = None,
    **metadata: Any,
) -> Skill:
    """Factory function for creating or loading a Synapse Skill.

    Accepts a filepath (.md or .txt), raw markdown string, or existing Skill instance.

    Args:
        prompt: File path (str or Path) to a markdown file, raw markdown instructions,
            or an existing Skill object.
        name: Optional explicit skill name.
        description: Optional summary of the skill's purpose.
        tools: Optional list of callables or connector tools.
        tags: Optional list of categories/tags.
        **metadata: Additional keyword attributes stored on the skill.

    Returns:
        A fully initialized Skill instance.

    Example:
        ```python
        from synapse.skills import makeskills

        # Load from file:
        python_skill = makeskills("skills/python_expert.md")

        # Create inline:
        fastapi_skill = makeskills(
            prompt="Write asynchronous FastAPI routes using Pydantic v2 schemas.",
            name="FastAPI Architect",
            description="Designs modern async APIs",
        )
        ```
    """
    if isinstance(prompt, Skill):
        if name:
            prompt.name = name
        if description:
            prompt.description = description
        if tools:
            prompt.tools.extend(tools)
        if tags:
            prompt.tags.extend(tags)
        prompt.metadata.update(metadata)
        return prompt

    if isinstance(prompt, Path):
        return Skill.from_file(
            file_path=prompt,
            name=name,
            description=description,
            tools=tools,
            tags=tags,
            **metadata,
        )

    # String input: check if it points to an existing file
    raw_str = str(prompt).strip()
    candidate_path = Path(raw_str)
    if candidate_path.exists() and candidate_path.is_file():
        return Skill.from_file(
            file_path=candidate_path,
            name=name,
            description=description,
            tools=tools,
            tags=tags,
            **metadata,
        )

    # Otherwise treat as markdown text
    return Skill.from_markdown(
        content=raw_str,
        name=name,
        description=description,
        tools=tools,
        tags=tags,
        **metadata,
    )


class SkillTemplate:
    """Helper for generating standardized SKILL.md documents and Skill instances."""

    @staticmethod
    def get_template(
        name: str = "custom-skill",
        description: str = "Description of capability and activation criteria",
        tags: list[str] | None = None,
        tools: list[str] | None = None,
    ) -> str:
        """Generates a standard markdown string with YAML frontmatter for a new skill."""
        tag_list = tags or ["agent-skill", "custom"]
        tool_list = tools or []
        tags_str = ", ".join(tag_list)
        tools_str = ", ".join(tool_list)
        return (
            f"---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"tags: [{tags_str}]\n"
            f"tools: [{tools_str}]\n"
            f"---\n\n"
            f"# {name.title().replace('-', ' ')}\n\n"
            f"## Overview\n"
            f"Detailed description of the skill and goals.\n\n"
            f"## Operational Protocol\n"
            f"1. **Analyze Input**: Extract user parameters.\n"
            f"2. **Execute Actions**: Call necessary tools and retrieve context.\n"
            f"3. **Format Output**: Provide grounded, structured response.\n"
        )

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        instructions: str = "",
        tags: list[str] | None = None,
        tools: list[Any] | None = None,
        **metadata: Any,
    ) -> Skill:
        """Creates a Skill instance with template validation."""
        return Skill(
            name=name,
            description=description,
            instructions=instructions,
            tags=tags,
            tools=tools,
            metadata=metadata,
        )


PREMADE_SKILLS: dict[str, str] = {
    "rag-analyst": "rag_analyst/SKILL.md",
    "rag_analyst": "rag_analyst/SKILL.md",
    "knowledge-graph": "knowledge_graph/SKILL.md",
    "knowledge_graph": "knowledge_graph/SKILL.md",
    "mcp-orchestrator": "mcp_orchestrator/SKILL.md",
    "mcp_orchestrator": "mcp_orchestrator/SKILL.md",
    "mlflow-evaluator": "mlflow_evaluator/SKILL.md",
    "mlflow_evaluator": "mlflow_evaluator/SKILL.md",
    "template": "template/SKILL.md",
    "synapse": "SKILL.md",
}


def list_premade_skills() -> list[str]:
    """Returns a list of unique names of all premade skills bundled with Synapse."""
    return [
        "rag-analyst",
        "knowledge-graph",
        "mcp-orchestrator",
        "mlflow-evaluator",
        "template",
    ]


def load_premade_skill(name: str) -> Skill:
    """Loads a pre-built, specialized agent skill from Synapse bundled skills."""
    normalized = name.strip().lower().replace("_", "-")
    rel_path = PREMADE_SKILLS.get(normalized) or PREMADE_SKILLS.get(name.strip().lower())
    if not rel_path:
        raise ValueError(
            f"Unknown premade skill '{name}'. Available: {list_premade_skills()}"
        )

    # 1. Check package internal premade directory
    package_file = Path(__file__).parent / "premade" / rel_path
    if package_file.exists():
        return Skill.from_file(package_file)

    # 2. Check repo root skills directory
    repo_file = Path(__file__).parent.parent.parent / "skills" / rel_path
    if repo_file.exists():
        return Skill.from_file(repo_file)

    # 3. Check single file in repo root
    root_skill = Path(__file__).parent.parent.parent / "SKILL.md"
    if (normalized == "synapse" or rel_path == "SKILL.md") and root_skill.exists():
        return Skill.from_file(root_skill)

    raise FileNotFoundError(f"Premade skill file not found for '{name}' (looked in {package_file})")


class SkillRegistry:
    """Registry and directory scanner for modular agent skills."""

    def __init__(self, skills: list[Skill] | None = None) -> None:
        self._skills: dict[str, Skill] = {}
        for s in skills or []:
            self.register(s)

    def register(self, skill: Skill) -> None:
        """Registers a Skill in the registry."""
        self._skills[skill.name.lower()] = skill

    def get(self, name: str) -> Skill | None:
        """Retrieves a registered Skill by name."""
        return self._skills.get(name.lower())

    def list(self) -> list[Skill]:
        """Returns all registered skills."""
        return list(self._skills.values())

    def __len__(self) -> int:
        return len(self._skills)

    @classmethod
    def discover(cls, directory: str | Path) -> SkillRegistry:
        """Scans a directory recursively for SKILL.md files and registers them."""
        reg = cls()
        dir_path = Path(directory)
        if dir_path.exists() and dir_path.is_dir():
            for f in dir_path.rglob("*.md"):
                if f.name.upper() == "SKILL.MD" or f.name.endswith(".skill.md"):
                    try:
                        reg.register(Skill.from_file(f))
                    except Exception:
                        pass  # nosec B110
        return reg


__all__ = [
    "Skill",
    "SkillRegistry",
    "SkillTemplate",
    "list_premade_skills",
    "load_premade_skill",
    "makeskills",
]
