# FastAPI SSE Streaming for RAG Systems

Add Server-Sent Events (SSE) streaming to an existing FastAPI RAG API so users see tokens as they're generated.

## Backend Pattern

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    session_id = request.session_id or str(uuid.uuid4())[:12]

    async def event_generator():
        # MUST set ContextVar INSIDE the generator (different async context)
        token = _session_ctx.set(session_id)
        try:
            # 1. Send route info first
            yield f"data: {json.dumps({'type': 'route', 'route': route})}\n\n"

            # 2. Stream LLM response
            response = client.chat.completions.create(
                model=MODEL, messages=[...], stream=True,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

            # 3. Send completion
            yield f"data: {json.dumps({'type': 'done', 'processing_time': elapsed})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            _session_ctx.reset(token)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
```

### SSE Event Types

| type | Fields | Purpose |
|------|--------|---------|
| `route` | `route` | Tell frontend which path (simple/comparison/complex) |
| `token` | `content` | Incremental text chunk |
| `tool` | `name`, `args` | Agent tool call started |
| `tool_result` | `name`, `result` | Agent tool call completed |
| `done` | `processing_time` | Query finished |
| `error` | `message` | Error occurred |

## The RAG Simple-Query Problem

**Problem**: RAG "simple" queries retrieve context and format the answer directly (no LLM streaming). The entire answer arrives as a single `data: {"type":"token","content":"<full answer>"}` event. Frontend sees it all at once — no streaming effect despite using `/query/stream`.

**Why it happens**: The RAG fast-path calls `_fast_path_rag(query)` which returns a complete string. Yielding it as one chunk defeats the purpose of SSE.

### Solution A: Server-Side Chunking (Recommended)

Split the pre-formed answer into sentence-level chunks and yield them with small delays:

```python
import re
import asyncio

if route == "simple":
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(executor, lambda: _fast_path_rag(query))
    answer = _deduplicate_answer(answer)
    _record_exchange(original_query, answer)

    # Split by sentence boundaries — Chinese punctuation
    chunks = re.split(r'(?<=[。！？\n])', answer)
    for chunk in chunks:
        if chunk.strip():
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            await asyncio.sleep(0.08)  # 80ms per chunk feels natural
```

**Regex choices**:
| Pattern | Splits on | Best for |
|---------|-----------|----------|
| `(?<=[。！？\n])` | Chinese sentence endings + newlines | Chinese text |
| `(?<=[.!?]\s)` | English sentence endings | English text |
| `(?<=\n)` | Newlines only | Structured/tabular answers |
| `(?:\n(?=- \|\*\*))` | Markdown list items | Bullet-point answers |

### Solution B: Frontend Typewriter Effect

Animate text appearance client-side. Works for ANY backend (even non-streaming):

```javascript
let fullText = '';
let typewriterIdx = 0;
let typewriterTimer = null;
let streamDone = false;

function startTypewriter() {
    if (typewriterTimer) return;  // Already running
    typewriterTimer = setInterval(() => {
        // Adaptive step: 2-3 chars for short text, more for long
        const step = Math.max(2, Math.floor(fullText.length / 80));
        typewriterIdx = Math.min(typewriterIdx + step, fullText.length);
        bubble.innerHTML = renderMarkdown(fullText.substring(0, typewriterIdx));
        msgs.scrollTop = msgs.scrollHeight;
        // Stop when all text shown AND stream is done
        if (typewriterIdx >= fullText.length && streamDone) {
            clearInterval(typewriterTimer);
            typewriterTimer = null;
            bubble.innerHTML = renderMarkdown(fullText);  // Final render with full markdown
        }
    }, 18);  // 18ms ≈ 55 chars/sec, fast enough to feel instant but visible
}

// In the SSE token handler:
if (evt.type === 'token') {
    fullText += evt.content;
    startTypewriter();  // Idempotent — only starts once
}

// In the done handler:
if (evt.type === 'done') {
    streamDone = true;
    if (!typewriterTimer && fullText) bubble.innerHTML = renderMarkdown(fullText);
}

// After the read loop:
if (typewriterTimer) clearInterval(typewriterTimer);
if (fullText) bubble.innerHTML = renderMarkdown(fullText);
```

**Combining A + B**: Server-side chunking gives real SSE streaming. Frontend typewriter adds a smooth animation on top. Together they feel like true LLM streaming.

## Frontend Pattern (Fetch Streams API)

```javascript
async function send() {
    const r = await fetch('/query/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: t, session_id: SID})
    });

    // Create empty bubble first
    const bubble = createBotBubble('...');
    let fullText = '';

    // Read SSE stream via Fetch Streams API (NOT EventSource — EventSource is GET-only)
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n');
        buffer = lines.pop();  // Keep incomplete line in buffer

        for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
                const evt = JSON.parse(line.slice(6));
                if (evt.type === 'token') {
                    fullText += evt.content;
                    bubble.innerHTML = renderMarkdown(fullText);
                    scrollToBottom();
                } else if (evt.type === 'done') {
                    showTiming(evt.processing_time);
                }
            } catch(e) {}  // Ignore parse errors from partial lines
        }
    }
    if (fullText) bubble.innerHTML = renderMarkdown(fullText);  // Final render
}
```

## Pitfalls

1. **ContextVar scope**: `ContextVar.set()` OUTSIDE `async def event_generator()` causes `"was created in a different Context"`. Always set INSIDE the generator.
2. **Buffer management**: SSE events may arrive split across chunks. Always buffer and split on `\n`, keeping the last incomplete line.
3. **X-Accel-Buffering**: If behind nginx, must set `X-Accel-Buffering: no` header or nginx buffers the entire response.
4. **Frontend scroll**: Call `scrollTop = scrollHeight` after each token update for auto-scroll.
5. **Non-streaming fallback**: Keep the non-streaming `/query` endpoint for API consumers who don't need streaming.
6. **Fetch Streams API vs EventSource**: `EventSource` only supports GET requests. For POST with JSON body, use `fetch()` + `ReadableStream` reader. Don't try to use `EventSource` for SSE POST endpoints.
7. **`renderMarkdown` must be defined**: If using markdown rendering in the typewriter/progressive display, ensure `renderMarkdown()` is defined BEFORE `send()`. JS loads top-to-bottom; a missing function causes `ReferenceError` that silently breaks the entire send flow.
8. **Typewriter `setInterval` cleanup**: Always clear the interval on stream completion AND on error. Leaked intervals cause increasing CPU usage and visual glitches.
9. **Editing JS via Python string replacement**: DON'T. Use `write_file` to write a Python script, then `scp` + execute. Python `str.replace()` on multi-line JS causes: double braces `}}`, regex escape issues, indentation mismatches. See pitfall #25 in main SKILL.md.
