# Qwen3.8-27B-Uncensored — ollama + codex 可用的两个模板版本

让 `Qwen3.8-27B-Uncensored.Q4_K_M.gguf` 这个 GGUF 既能被 **ollama** 正常加载，
也能被 **codex CLI**（0.163+，走 `/v1/responses`）正常调用。

## 背景：为什么有两个模板

一个 GGUF 里有两套「对话转 prompt」的模板：

| 模板 | 存放位置 | 被谁使用 |
|------|----------|----------|
| Go `TEMPLATE` | 你的 Modelfile 里 | ollama 的 `/api/chat`、`/v1/chat/completions` |
| Jinja `tokenizer.chat_template` | **GGUF 文件内部** | ollama 的 `/v1/responses`（codex 用的就是它） |

关键点：**codex 0.163 只支持 `wire_api = "responses"`**，走的是 GGUF 内部那个
Jinja 模板，而不是 Modelfile 里的 Go `TEMPLATE`。

上游 GGUF 自带的 Jinja 模板是 vLLM / HuggingFace 风格，有两个问题会让 codex 直接报错：

1. **`System message must be at the beginning.`** —— codex 会发两条 `developer`
   消息，ollama 把它们转成两条 `system` 消息，而 vLLM 模板要求 system 必须在第一条。
2. **工具调用格式不对** —— vLLM 模板输出 `<function>/<parameter>` 格式，
   而 ollama/codex 期望的是 OpenAI 的 `<tool_call>{"name": ..., "arguments": {...}}</tool_call>`。

本仓库提供两个版本：

- `chat-template.ollama.jinja` —— **修正版**，给 ollama + codex 用（合并多条
  system/developer、OpenAI `<tool_call>` 格式、放宽 `reasoning_effort` 取值）。
- `chat-template.vllm.jinja` —— **原版**（vLLM / HF 风格），如果你想恢复或给
  vLLM / HF 直接用，保留这个。

## 文件清单

| 文件 | 说明 |
|------|------|
| `Modelfile` | ollama 用的 Modelfile（含 Go `TEMPLATE`，供 `/v1/chat/completions` 走） |
| `chat-template.ollama.jinja` | 修正版 Jinja 模板（打补丁进 GGUF） |
| `chat-template.vllm.jinja` | 原版 vLLM Jinja 模板（打补丁进 GGUF 恢复） |
| `patch-gguf-chat-template.py` | 就地替换 GGUF 内嵌模板的脚本 |

## 使用方法

> **⚠️ 第一步必须先下载模型文件。** 本仓库**不包含** GGUF 模型权重
> （约 16.8GB），需要你自己从 HuggingFace 下载。

### 1. 下载 GGUF（必需，先做这一步）

从 HuggingFace 下载量化的 GGUF，并把下载下来的文件**放到本仓库目录下**（与
`Modelfile` 同级），文件名需与 Modelfile 里的 `FROM` 一致：

```bash
# 在项目目录下执行，例如用 huggingface-cli 或 wget
huggingface-cli download mradermacher/Qwen3.8-27B-Uncensored-GGUF Qwen3.8-27B-Uncensored.Q4_K_M.gguf --local-dir .
```

下载地址：https://huggingface.co/mradermacher/Qwen3.8-27B-Uncensored-GGUF

下载完成后，目录里应能看到 `Qwen3.8-27B-Uncensored.Q4_K_M.gguf`（约 16.8GB），
然后才能继续下面第 2 步打补丁和第 3 步 `ollama create`。

### 2. 给 GGUF 打补丁（关键一步，codex 必需）

```bash
# 用修正版模板（ollama + codex 用）
python3 patch-gguf-chat-template.py Qwen3.8-27B-Uncensored.Q4_K_M.gguf chat-template.ollama.jinja

# 如果之后想恢复原版
python3 patch-gguf-chat-template.py Qwen3.8-27B-Uncensored.Q4_K_M.gguf chat-template.vllm.jinja
```

脚本是**就地修改**，不重写几十 GB 的 tensor 数据；新模板若比原模板短，
会用 Jinja 注释补足到等长，保证文件大小不变。

### 3. 用 ollama 创建模型

```bash
ollama create qwen-27b:latest -f Modelfile
```

### 4. 配置 codex

`~/.codex/config.toml`：

```toml
model = "qwen-27b:latest"
model_provider = "custom"
base_url = "http://localhost:11434/v1"
wire_api = "responses"
requires_openai_auth = false
experimental_bearer_token = "ollama"
```

### 5. 验证

```bash
codex exec "Reply with exactly: OK"
```

## 模型信息

- **架构**：`qwen35`（Qwen3.8）
- **上下文长度**：`262144`（`PARAMETER num_ctx` 可按需调小，Modelfile 里默认 `16384`）
- **基础模型**：https://huggingface.co/Qwen/Qwen3.8-27B
- **无审查版**：https://huggingface.co/JonathanColetti/Qwen3.8-27B-Uncensored
- **GGUF 量化**：https://huggingface.co/mradermacher/Qwen3.8-27B-Uncensored-GGUF
