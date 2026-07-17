# Windows Portable RAG Package

Complete guide for deploying LangChain RAG to Windows machines without Python installation.

## Package Structure

```
rag_windows_package/
├── install.bat                            # Install dependencies (run once)
├── start.bat                              # Launch RAG system
├── lc_lx.py                               # RAG main script
├── 郑寅文.md                               # Knowledge base document
├── python-3.12.4-embed-amd64.zip          # Embedded Python (11MB)
├── requirements.txt                       # Python dependencies
└── README.txt                             # User instructions
```

## Creating the Package

### 1. Download Embedded Python
```bash
wget https://mirrors.huaweicloud.com/python/3.12.4/python-3.12.4-embed-amd64.zip
```

### 2. Copy RAG Files
```bash
cp /home/rag_lx/lc_lx.py .
cp /home/rag_lx/郑寅文.md .
```

### 3. Create Two Scripts (English Only!)

**Critical lesson**: Use TWO separate scripts - `install.bat` for setup, `start.bat` for running. This makes debugging much easier.

#### install.bat (run once to setup)
```batch
@echo off
title RAG Installer

echo ================================
echo   Installing Dependencies
echo ================================
echo.

python -m # pip install --upgrade pip
python -m # pip install langchain langchain-openai langchain-chroma chromadbommunity langchain-chroma langchain-core langchain-text-splitters openai chromadb pydantic requests

echo.
echo ================================
echo   Done!
echo   Now run: python lc_lx.py
echo ================================
pause
```

#### start.bat (run to start RAG)
```batch
@echo off
title RAG System

echo ================================
echo   Starting RAG System
echo ================================
echo.

python lc_lx.py

pause
```

**Important**: Keep scripts SIMPLE and ENGLISH-ONLY. Complex scripts with Chinese characters cause encoding errors.

### 4. Create requirements.txt
```
langchain>=0.2.0
langchain-openai>=0.1.0
langchain-community>=0.2.0
langchain-chroma>=0.1.0
langchain-core>=0.2.0
langchain-text-splitters>=0.0.1
openai>=1.0.0
chromadb>=0.4.0
pydantic>=2.0.0
requests>=2.28.0
```

### 5. Package
```bash
tar -czf rag_windows_package.tar.gz rag_windows_package/
```

## User Workflow (Critical!)

Users must follow this order:

### Step 1: Extract to English-named folder
```
C:\rag\           ✅ Good
C:\新建文件夹\    ❌ BAD - causes encoding errors
C:\My RAG\        ❌ BAD - spaces cause issues
```

### Step 2: Install Python
Download and install Python from python.org. **CHECK "Add Python to PATH"** during installation.

### Step 3: Run install.bat
Double-click `install.bat` to install all dependencies.

### Step 4: Run start.bat
Double-click `start.bat` to start the RAG system.

### Step 5: Set API Key
On first run, create `.env` file:
```
YOUR_API_KEY_HERE=your_key_here
```

## Common Issues

### Issue 1: Chinese Characters Garbled in CMD
**Symptoms**: `'HON DIR'`, `'不是内部或外部命令'`, garbled text like `'溴瑕佶喱镲嗦捻铇'`
**Cause**: Windows CMD defaults to GBK encoding, .bat saved as UTF-8
**Fix**: 
- Use English-only in .bat files
- Add `chcp 65001 >nul` at start (but English-only is better)

### Issue 2: "python.exe: can't open file"
**Symptoms**: `can't open file 'C:\...\\lc_lx.py': [Errno 2] No such file`
**Cause**: Path with Chinese characters (e.g., "新建文件夹") gets mangled
**Fix**: 
- Rename folder to English (e.g., "rag")
- Use `%~dp0lc_lx.py` in batch script

### Issue 3: ModuleNotFoundError
**Symptoms**: `ModuleNotFoundError: No module named 'langchain_chroma'`
**Cause**: Dependencies not installed
**Fix**: Run `install.bat` first, then `start.bat`

### Issue 4: pip Not Found
**Symptoms**: `'pip' is not recognized`
**Cause**: Python not in PATH or not installed
**Fix**: Install Python with "Add to PATH" checked, or use the full Python pathull path: `python -m pip install ...`

## Troubleshooting Checklist

1. **Is Python installed?** → Run `python --version` in cmd
2. **Is Python in PATH?** → Run `where python` in cmd
3. **Are dependencies installed?** → Run `pip list` to check
4. **Is the folder name English?** → Check path for Chinese characters
5. **Did you run install.bat first?** → Must run before start.bat

## Notes

- Embedded Python is ~11MB, dependencies add ~200MB
- First run requires internet to download packages
- After first run, can work offline (packages cached)
- Users MUST extract to English-named folders
- Users MUST run install.bat before start.bat
