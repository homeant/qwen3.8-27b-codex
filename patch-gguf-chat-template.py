#!/usr/bin/env python3
"""Patch the `tokenizer.chat_template` embedded inside a GGUF file.

Why this exists
---------------
A GGUF file carries its chat template (the Jinja template that decides how a
conversation is turned into a prompt) inside its own metadata.  When you feed a
GGUF to ollama, ollama's OpenAI-compatible endpoints (/v1/chat/completions and
/v1/responses) render *that embedded template*, NOT the Modelfile's Go
`TEMPLATE`.  codex 0.163+ talks to ollama via /v1/responses, so if the embedded
template is a vLLM/HuggingFace-style template, codex breaks with errors like:

    Jinja Exception: System message must be at the beginning.

This script replaces the embedded template with one of the two templates in
this repo:

  chat-template.ollama.jinja   -> for ollama / codex  (multi-system friendly,
                                                      OpenAI <tool_call> format)
  chat-template.vllm.jinja     -> original vLLM / HF template (restore)

Usage
-----
  python3 patch-gguf-chat-template.py <gguf-path> <template.jinja>

The new template must not be longer than the one currently embedded.  If it is
shorter, it is padded with a Jinja comment so the file stays the same size (an
in-place edit; no need to rewrite the multi-GB tensor data).

Note: this modifies the GGUF in place.  Keep a copy if you want the original.
"""

import mmap
import struct
import sys


def find_chat_template(buf):
    """Return (value_offset, value_length) of the embedded chat_template."""
    key = b"tokenizer.chat_template"
    pos = buf.find(key)
    if pos < 0:
        raise SystemExit("ERROR: 'tokenizer.chat_template' key not found in GGUF")
    # key is stored as: u64 length + key bytes.  After the key bytes the value
    # type (u32) follows; a few bytes of alignment padding may sit in between.
    p = pos + len(key)
    for off in range(0, 64):
        value_type = struct.unpack_from("<I", buf, p + off)[0]
        if value_type == 8:  # GGUF_TYPE_STRING
            value_len = struct.unpack_from("<Q", buf, p + off + 4)[0]
            value_start = p + off + 4 + 8
            return value_start, value_len
    raise SystemExit("ERROR: could not locate the chat_template string value")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    gguf_path, tpl_path = sys.argv[1], sys.argv[2]

    new = open(tpl_path, "rb").read()

    with open(gguf_path, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        value_start, old_len = find_chat_template(mm)
        print(f"chat_template found at offset {value_start}, length {old_len}")

        if len(new) > old_len:
            raise SystemExit(
                f"ERROR: new template ({len(new)} bytes) is longer than the "
                f"original ({old_len} bytes); aborting to avoid a full rewrite."
            )

        pad = old_len - len(new)
        if pad:
            if pad >= 4:
                new = new + b"{#" + b" " * (pad - 4) + b"#}"
            else:
                new = new + b" " * pad
        assert len(new) == old_len, (len(new), old_len)

        mm[value_start : value_start + old_len] = new
        mm.flush()
        mm.close()

    print(f"patched OK ({old_len} bytes replaced)")


if __name__ == "__main__":
    main()
