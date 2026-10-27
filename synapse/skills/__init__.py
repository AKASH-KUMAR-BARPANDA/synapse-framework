"""Skills module for specialized agent instructions, templates, and domain personas."""

from synapse.skills.skill import (
    Skill,
    SkillRegistry,
    SkillTemplate,
    list_premade_skills,
    load_premade_skill,
    makeskills,
)

__all__ = [
    "Skill",
    "SkillRegistry",
    "SkillTemplate",
    "list_premade_skills",
    "load_premade_skill",
    "makeskills",
]
