# SiliconFlow API Configuration

## API Endpoints

- **Base URL**: `https://api.siliconflow.cn/v1`
- **Rerank URL**: `https://api.siliconflow.cn/v1/rerank`

## Models

| Purpose | Model ID | Status (2026-06) | Notes |
|---------|----------|-------------------|-------|
| Embeddings | `BAAI/bge-large-zh-v1.5` | ✅ | Chinese-optimized, 1024 dim, **500 char input limit** |
| Embeddings | `BAAI/bge-large-en-v1.5` | ✅ | English-optimized, 1024 dim |
| Reranking | `BAAI/bge-reranker-v2-m3` | ✅ | Cross-lingual reranker |
| LLM (fast) | `deepseek-ai/DeepSeek-V4-Flash` | ✅ | ~5s, good for most tasks |
| LLM (quality) | `deepseek-ai/DeepSeek-V3` | ✅ | ~15s, better reasoning |
| LLM (alt) | `Qwen/Qwen2.5-7B-Instruct` | ✅ | Alternative option |
| LLM (disabled) | `THUDM/glm-4-9b-chat` | ❌ | 403 "Model disabled" |
| LLM (disabled) | `THUDM/GLM-4-9B-0414` | ❌ | May also be disabled, verify before use |

**⚠️ Always verify model availability before deployment.** SiliconFlow disables models without notice. Test with:
```python
import openai
client = openai.OpenAI(base_url='https://api.siliconflow.cn/v1', api_key=key)
resp = client.chat.completions.create(model="MODEL_ID", messages=[{"role":"user","content":"hi"}], max_tokens=5)
```

## Environment Variables

```env
YOUR_API_KEY_HERE=sk-xxx
SILICONFLOW_API_BASE=https://api.siliconflow.cn/v1
EMBED_MODEL=BAAI/bge-large-zh-v1.5
RERANK_MODEL=BAAI/bge-reranker-v2-m3
RERANK_API_URL=https://api.siliconflow.cn/v1/rerank
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
QUERY_REWRITE_MODEL=deepseek-ai/DeepSeek-V4-Flash  # Must match provider!
```

## Verification

```bash
# Test API key validity
# curl example (add your own auth) batch embeddings in chunks of 30
- Reranking adds ~1-2s latency but improves relevance
- For production, consider dedicated embedding endpoints

## Pitfall: Model-to-Provider Mismatch

**Symptom:** `Error code: 400 - {'code': 20012, 'message': 'Model does not exist.'}`

**Cause:** `.env` has a model name from a different provider (e.g., `glm-4.5-air` is 智谱AI, not SiliconFlow). The SiliconFlow API doesn't recognize models from other providers.

**Fix:** Match model names to the API base URL:
- SiliconFlow (`api.siliconflow.cn`): Use `deepseek-ai/DeepSeek-V4-Flash`, `Qwen/Qwen2.5-7B-Instruct`, etc.
- 智谱AI (`open.bigmodel.cn`): Use `glm-4.5-air`, `glm-4`, etc.
- Xiaomi MiMo (`api.xiaomimimo.com`): Use `mimo-v2.5-pro`, etc.

**Common mistake:** Copying `.env` from one project (智谱) to another (SiliconFlow) without updating `LLM_MODEL`.
