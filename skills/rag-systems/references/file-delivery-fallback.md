# File Delivery Fallback via HTTP Server

When messaging platforms (WeChat, Telegram, etc.) can't deliver large files.

## Problem

User needs to download files from server but:
- WeChat only shows filename, not the actual file
- File size exceeds platform limits
- Platform doesn't support file transfers

## Solution: Temporary HTTP Server

Start a simple HTTP server on the server, give user the download URL.

### Step 1: Start HTTP Server

```bash
cd /root
python3 -m http.server 8080 --bind 0.0.0.0 &
```

### Step 2: Give User Download URL

```
http://<server_ip>:8080/rag_windows_package_v4.tar.gz
```

### Step 3: Stop Server After Download

```bash
# Find and kill the server
kill $(lsof -t -i :8080)
```

## Alternative: Direct Download Commands

For Python installer (user can run in CMD):
```cmd
curl -O https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe
```

For Huawei mirror (faster in China):
```cmd
curl -O https://mirrors.huaweicloud.com/python/3.12.4/python-3.12.4-amd64.exe
```

## Pitfall: Alibaba Cloud Security Group Blocks Ports

On Alibaba Cloud ECS, most ports are **blocked by default** in the security group. Even if the HTTP server starts fine and `curl localhost:8080` works, external browsers cannot connect.

**Symptoms**: `ERR_NETWORK_CHANGED`, `连接已中断`, `ERR_CONNECTION_TIMED_OUT`

**Diagnosis**:
```bash
# Server-side check (should return 200):
# curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT  # Health check/file.tar.gz

# If local works but browser fails → security group is blocking
```

**Fix options (in order of simplicity)**:

1. **Open port in Alibaba Cloud security group**:
   ECS Console -> Instance -> Security Group -> Inbound Rules -> Add Rule
   - Protocol: TCP, Port: 8888 (or chosen port), Source: 0.0.0.0/0
   Then retry the HTTP server method.

2. **Use an already-open port** (check with `ss -tlnp`):
   If RAG service port (e.g. 8001) is already allowed, use it temporarily. Stop the service first to free the port.

3. **SCP from local machine** (requires SSH port 22 open):
   `scp root@<server_ip>:/root/file.tar.gz .`

4. **Base64 encode and copy-paste** (last resort, slow for large files):
   ```bash
   base64 /root/file.tar.gz | split -b 60000 - /tmp/chunk_
   # Copy each chunk from terminal, decode on Windows CMD:
   # certutil -decode chunk_a file.tar.gz
   ```

## Notes

- HTTP server exposes all files in the directory - be careful with sensitive data
- Always verify security group rules before assuming a port is accessible
- Kill server immediately after user downloads
- For production, use proper file hosting (S3, OSS, etc.)
