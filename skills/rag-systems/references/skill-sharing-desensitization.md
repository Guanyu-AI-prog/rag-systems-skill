# Skill Desensitization for Sharing

When sharing Hermes skills with others (via file transfer, GitHub, etc.), check for and remove sensitive information before packaging.

## What to Desensitize

| Type | Pattern | Replace With |
|------|---------|--------------|
| Server paths | `/home/admin/`, `/home/username/` | `~/` or relative paths |
| API keys | Actual key strings | Environment variable references (`"your-api-key"`) |
| Internal project names | Specific client/project codenames | Generic names or keep if public |
| IP addresses | Internal server IPs | Placeholder or remove |
| Personal info | Names, phone numbers, emails | Generic placeholders |

## Desensitization Process

1. **Copy skill directory** to a temp location (don't modify original)
2. **Search all .md/.py/.json files** for sensitive patterns
3. **Replace paths** using string replacement
4. **Verify no API keys** remain (grep for `sk-`, `Bearer`, etc.)
5. **Check file references** - ensure relative paths still work
6. **Package as tar.gz** for sharing

## Example Script

```python
import os, shutil

# Copy to temp
shutil.copytree(src_dir, dst_dir)

# Replace paths in all text files
replacements = {'/home/admin/': '~/'}
for root, dirs, files in os.walk(dst_dir):
    for f in files:
        if f.endswith(('.md', '.py', '.json')):
            path = os.path.join(root, f)
            content = open(path).read()
            for old, new in replacements.items():
                content = content.replace(old, new)
            open(path, 'w').write(content)
```

## Sharing Platforms

| Platform | Format | Notes |
|----------|--------|-------|
| WeChat | tar.gz | Mobile can't open; send individually with 12s intervals |
| GitHub | Direct push | Public repos OK, private repos need auth |
| Direct file | Copy folder | Simplest for local sharing |

## Pitfalls

1. **tar.gz doesn't open on WeChat mobile** - Send files individually or use zip
2. **Don't modify the original skill** - Always work on a copy
3. **Check README references** - Relative links may break after path changes
4. **Verify the packaged skill works** - Test loading it before sharing
