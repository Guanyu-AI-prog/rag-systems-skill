# Skill Sharing & Desensitization Guide

When sharing RAG skills with others (via file transfer, messaging, etc.), sanitize personal/sensitive info first.

## What to Desensitize

| Pattern | Risk | Fix |
|---------|------|-----|
| `/home/admin/` paths | Leaks server username | Replace with `~/` |
| `/home/<any_user>/` paths | Leaks usernames | Replace with `~/` or generic paths |
| Hardcoded API keys | Credential leak | Should already be env vars — verify |
| Specific IP addresses | Server identification | Replace with `<server-ip>` or `localhost` |
| Project-specific names | Low risk if public repos | Keep if repo is public, redact if private |

## What NOT to Desensitize

- Environment variable references (`"your-api-key"`) — already safe
- Public model names (DeepSeek, GLM, SiliconFlow) — public knowledge
- Domain knowledge (telecom plans, pricing data) — this IS the value being shared
- Generic code patterns and architecture — the whole point of sharing

## Workflow

```python
import shutil

# 1. Copy skill directories to a temp location
shutil.copytree(src_skill_dir, out_dir)

# 2. Walk all .md/.py/.json files and replace patterns
replacements = {'/home/admin/': '~/', '/home/admin': '~'}
for root, dirs, files in os.walk(out_dir):
    for f in files:
        if f.endswith(('.md', '.py', '.json')):
            content = open(path).read()
            for old, new in replacements.items():
                content = content.replace(old, new)
            open(path, 'w').write(content)

# 3. Pack as tar.gz (or zip for Windows users)
import subprocess
# # Package using tar  # Uncomment to package
```

## Delivery Considerations

- **WeChat**: tar.gz won't open on mobile. Send as-is (user forwards to recipient who opens on computer).
- **WeChat file size**: Keep under 5MB per file. The rag-systems skill (~63KB) is well within limits.
- **Recipient setup**: Tell them to extract to `~/.hermes/skills/data-science/` to match the original structure.

## Checklist Before Sending

- [ ] No `/home/<username>/` paths remaining
- [ ] No hardcoded API keys
- [ ] No private IP addresses
- [ ] SKILL.md reads correctly with generic paths
- [ ] Templates still have XXX placeholders (not real values)
- [ ] Archive size reasonable (<1MB for text-only skills)
