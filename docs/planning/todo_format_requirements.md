# Todo Management in Code Agent

## Overview
Code Agent uses `TodoManager` to parse and track tasks in the target project. For optimal performance, the TODO file must follow a specific structure.

## Recommended Format (Markdown)
The agent works best with Markdown files using checkboxes (`- [ ]` and `- [x]`).

```markdown
# Current Tasks
- [ ] Implement new feature
- [x] Fix urgent bug
  - [ ] Add unit test for the fix
```

## Parsing Rules
1. **Active Tasks**: Lines starting with `- [ ]` are parsed as pending tasks.
2. **Completed Tasks**: Lines starting with `- [x]` are parsed as completed.
3. **Hierarchy**: Indentation using spaces indicates sub-tasks.
4. **Ignored Elements**:
   - Numbered lists (`1. Task`) are **not** parsed as actionable tasks.
   - Plain text or headers are ignored by the task executor.
   - "Implemented" sections without checkboxes should be kept as plain text to avoid being parsed as new tasks.

## Configuration
You can set the preferred format in `config/config.yaml`:
```yaml
project:
  todo_format: md  # Options: md, txt, yaml
```

## Best Practices
- **Use Checkboxes**: Always use `- [ ]` for new tasks to ensure they are discovered.
- **Archive Details**: Move long roadmaps and architectural debt to separate files (e.g., `ROADMAP.md`) and keep the main `todo.md` concise.
- **Automatic Updates**: The agent can automatically mark tasks as done if configured, but manual verification is recommended.
