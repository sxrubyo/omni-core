OpenClaw Gemini integration notes (internal, safe):
- Do not copy external Skill definitions verbatim from codex/codex-like sources.
- Implement internal adapters that wrap skills owned by you, with a standard interface.
- If you have a repository of skills you authorize, create a local importer to transform them into internal Melissa SKILL_DEFINITIONS blocks.
- Gemini integration can provide generated prompts or orchestration results, but Melissa keeps the actual decision logic.
- Audit trail: store mapping of skill names to sources (internal/built-in) for compliance.

Plan to migrate into Melissa:
- Create a directory structure: /home/ubuntu/Openclaw/skills/
- For each skill, create a module with a stable API: id, name, version, description, apply() method that returns a function/handler to be used by Melissa.
- A central registry to import all built-in skills on startup.

Note: This is internal scaffolding; actual code to utilize the skills will be added later when integrating with melissa.py.