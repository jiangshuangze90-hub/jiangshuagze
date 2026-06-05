#!/usr/bin/env python3
"""Small OpenAI Responses-compatible bridge for using DeepSeek from Codex.

The official DeepSeek API is OpenAI Chat Completions compatible. Current Codex
custom providers speak the OpenAI Responses wire API, so this local process
accepts the subset of /v1/responses that Codex needs and forwards it to
DeepSeek's /chat/completions endpoint.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def _response_id() -> str:
    return f"resp_{uuid.uuid4().hex}"


def _item_id(prefix: str = "msg") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("input_text") or item.get("output_text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)
    return "" if content is None else str(content)


def _messages_from_responses_input(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        return [{"role": "user", "content": value}]
    messages: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return messages

    for item in value:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        role = item.get("role") or ("assistant" if item_type in {"message", "function_call"} else "user")

        if item_type == "function_call_output":
            messages.append({
                "role": "tool",
                "tool_call_id": item.get("call_id") or item.get("id") or _item_id("call"),
                "content": _text_from_content(item.get("output")),
            })
            continue

        if item_type == "function_call":
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": item.get("call_id") or item.get("id") or _item_id("call"),
                    "type": "function",
                    "function": {
                        "name": item.get("name") or "tool",
                        "arguments": item.get("arguments") or "{}",
                    },
                }],
            })
            continue

        text = _text_from_content(item.get("content") if "content" in item else item.get("input"))
        if text:
            messages.append({"role": role, "content": text})
    return messages


def _tools_from_responses(tools: Any) -> list[dict[str, Any]] | None:
    if not isinstance(tools, list):
        return None
    converted: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if tool.get("type") not in {"function", "custom"}:
            continue
        name = tool.get("name") or tool.get("function", {}).get("name")
        if not name:
            continue
        parameters = tool.get("parameters") or tool.get("function", {}).get("parameters") or {"type": "object"}
        converted.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool.get("description") or tool.get("function", {}).get("description") or "",
                "parameters": parameters,
            },
        })
    return converted or None


def _deepseek_chat(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")

    request = urllib.request.Request(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {body}") from exc


def _responses_payload(body: dict[str, Any]) -> dict[str, Any]:
    model = body.get("model") or DEFAULT_MODEL
    chat_payload: dict[str, Any] = {
        "model": model,
        "messages": _messages_from_responses_input(body.get("input")),
        "stream": False,
    }
    if instructions := body.get("instructions"):
        chat_payload["messages"].insert(0, {"role": "system", "content": _text_from_content(instructions)})
    if max_tokens := body.get("max_output_tokens"):
        chat_payload["max_tokens"] = max_tokens
    if temperature := body.get("temperature"):
        chat_payload["temperature"] = temperature
    tools = _tools_from_responses(body.get("tools"))
    if tools:
        chat_payload["tools"] = tools
        chat_payload["tool_choice"] = "auto"

    chat = _deepseek_chat(chat_payload)
    choice = (chat.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    output: list[dict[str, Any]] = []
    output_text = message.get("content") or ""

    if output_text:
        output.append({
            "id": _item_id(),
            "type": "message",
            "status": "completed",
            "role": "assistant",
            "content": [{"type": "output_text", "text": output_text, "annotations": []}],
        })

    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function") or {}
        output.append({
            "id": tool_call.get("id") or _item_id("fc"),
            "type": "function_call",
            "status": "completed",
            "call_id": tool_call.get("id") or _item_id("call"),
            "name": function.get("name") or "tool",
            "arguments": function.get("arguments") or "{}",
        })

    now = int(time.time())
    return {
        "id": _response_id(),
        "object": "response",
        "created_at": now,
        "status": "completed",
        "model": model,
        "output": output,
        "output_text": output_text,
        "usage": chat.get("usage"),
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path.rstrip("/") == "/v1/models":
            self._send_json(200, {
                "object": "list",
                "data": [
                    {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
                    {"id": "deepseek-reasoner", "object": "model", "owned_by": "deepseek"},
                ],
            })
            return
        self._send_json(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path.rstrip("/") != "/v1/responses":
            self._send_json(404, {"error": {"message": "not found"}})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            result = _responses_payload(body)
            self._send_json(200, result)
        except Exception as exc:  # Return API-style errors to Codex instead of crashing the bridge.
            self._send_json(500, {"error": {"message": str(exc), "type": "bridge_error"}})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local Codex Responses bridge for DeepSeek.")
    parser.add_argument("--host", default=os.environ.get("CODEX_DEEPSEEK_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CODEX_DEEPSEEK_PORT", "5098")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Codex DeepSeek bridge listening on http://{args.host}:{args.port}/v1")
    server.serve_forever()


if __name__ == "__main__":
    main()
