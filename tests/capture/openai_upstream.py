"""A stand-in for the OpenAI Chat Completions API, answering as the real one does."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def completion(message: dict, prompt: int, completion_tokens: int) -> dict:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "gpt-5",
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt + completion_tokens,
        },
    }


class OpenAi(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        answered_tool = any(m.get("role") == "tool" for m in body["messages"])
        if body.get("tools") and not answered_tool:
            call = {
                "id": "call_1",
                "type": "function",
                "function": {"name": "search", "arguments": '{"query": "dismissal"}'},
            }
            reply = completion({"role": "assistant", "content": None, "tool_calls": [call]}, 90, 12)
        elif answered_tool:
            reply = completion({"role": "assistant", "content": "Invalid dismissal."}, 150, 8)
        else:
            reply = completion({"role": "assistant", "content": "Short: invalid."}, 30, 4)
        payload = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def start_openai() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), OpenAi)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
