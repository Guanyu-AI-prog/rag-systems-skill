# Hand-Typed Code Error Reference

Common errors when users manually type Python code (especially in restricted environments like internet cafes).

## Error Categories

### 1. Import Errors
```python
# WRONG - missing os import
import sys
os.path.dirname(__file__)  # NameError: name 'os' is not defined

# CORRECT
import os
import sys
```

### 2. Spelling Errors
```python
# WRONG
from cocurrent.futures import ThreadPoolExecutor  # ModuleNotFoundError
REQUER_TIMEOUT = 60  # NameError when referenced as REQUEST_TIMEOUT

# CORRECT
from concurrent.futures import ThreadPoolExecutor
REQUEST_TIMEOUT = 60
```

### 3. Model/API Name Errors
```python
# WRONG
LLM_MODEL = "THUDE/GLM-4-9b-0414"  # 404 Not Found from API

# CORRECT
LLM_MODEL = "THUDM/GLM-4-9B-0414"
```

### 4. URL Errors
```python
# WRONG
self.api_url = "https//api.siliconflow.cn/v1/embeddings"  # Missing colon

# CORRECT
self.api_url = "https://api.siliconflow.cn/v1/embeddings"
```

### 5. JSON/Dict Syntax Errors
```python
# WRONG - multiple errors
json={"model":self.model, "input:texts"},  # Invalid JSON
headers={"Authorization": f"Bearer {key}", "Content-Type":"application/jaon"}  # Typo

# CORRECT
json={"model": self.model, "input": texts},
headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
```

### 6. Method Name Errors
```python
# WRONG - doesn't match interface
def embeddings(self, texts: list) -> list:  # Should be embed_documents

# CORRECT
def embed_documents(self, texts: list) -> list:
```

### 7. Variable Reference Errors
```python
# WRONG
def embed_query(self, text: str) -> list:
    return seif.embed_documents([text])[0]  # 'seif' typo, wrong indent

# CORRECT
def embed_query(self, text: str) -> list:
    return self.embed_documents([text])[0]
```

### 8. Format String Errors
```python
# WRONG
logging.basicConfig(format="%(levelname)%(message)s")  # Missing 's'

# CORRECT
logging.basicConfig(format="%(levelname)s %(message)s")
```

## Validation Checklist

When reviewing hand-typed code, check:

- [ ] All imports present (os, sys, etc.)
- [ ] Variable names consistent throughout
- [ ] URLs have proper scheme (https://)
- [ ] JSON syntax valid (quotes, commas, colons)
- [ ] Method names match expected interface
- [ ] String literals spelled correctly (self, not seif)
- [ ] Indentation consistent (4 spaces)
- [ ] Format strings have correct specifiers
- [ ] API model names exactly match documentation
