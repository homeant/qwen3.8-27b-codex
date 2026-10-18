# Qwen3.8-27B-Uncensored — ollama + codex 可用的两个模板版本

让 `Qwen3.8-27B-Uncensored.Q4_K_M.gguf` 这个 GGUF 既能被 **ollama** 正常加载，
也能被 **codex CLI**（0.163+，走 `/v1/responses`）正常调用。

## 背景

本仓库各文件的作用如下：

| 文件 | 说明 |
|------|------|
| `Modelfile` | ollama 使用的模型定义文件，内含 Go `TEMPLATE`，供 `/v1/chat/completions` 使用 |
| `chat-template.ollama.jinja` | 修正版 Jinja 模板，打补丁进 GGUF，供 ollama `/v1/responses`（codex）使用 |
| `chat-template.vllm.jinja` | 原版 vLLM / HuggingFace Jinja 模板，用于恢复 GGUF 原始模板 |
| `patch-gguf-chat-template.py` | 就地替换 GGUF 内嵌模板的脚本 |

## 使用方法

> **⚠️ 第一步必须先下载模型文件。** 本仓库**不包含** GGUF 模型权重
> （约 16.8GB），需从 HuggingFace 下载。

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

# 如需恢复原版
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
