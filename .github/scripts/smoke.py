"""Serve one sample agent locally and run every example it advertises over A2A.

Run it from a sample's directory, inside that sample's environment, the way CI does:

    poetry run python ../../../.github/scripts/smoke.py

A local agent accepts only requests that carry a token signed with Aion's key, and
it loads that key from ``{AION_API_HOST}/runtime/a2a/verification-keys``. The script
stands in for that part of the platform: it publishes a key of its own at that path
and signs an anonymous session token with it, as Aion does for a chat client. Then it
starts ``aion serve`` with no credentials and sends each skill example from
``aion.yaml`` as one turn, first with SendMessage and then with SendStreamingMessage,
each mode in a conversation of its own.

What a turn must end in is the same for every sample: ``FAILED`` for ``fail``,
``INPUT_REQUIRED`` for ``ask`` (answered at once, after which the same task must
complete), and ``COMPLETED`` for everything else. A task that stops short of ``COMPLETED`` must
say why in its status message. The text of the answers is not checked.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator, Optional

import httpx
import jwt
import yaml
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

KEYS_PATH = "/runtime/a2a/verification-keys"
ISSUER = "aion.io"
SESSION_AUDIENCE = "urn:aion:a2a:anonymous-session"
SESSION_LIFETIME = 30 * 24 * 3600
EXPECTED_STATE = {"fail": "TASK_STATE_FAILED", "ask": "TASK_STATE_INPUT_REQUIRED"}
ANSWER = "staging"
START_TIMEOUT = 180
REQUEST_TIMEOUT = 120


class SigningKey:
    """A P-256 key that signs tokens the way Aion does, and the key set that publishes it."""

    def __init__(self) -> None:
        self.key = ec.generate_private_key(ec.SECP256R1())
        public = ECAlgorithm.to_jwk(self.key.public_key(), as_dict=True)
        members = {name: public[name] for name in ("crv", "kty", "x", "y")}
        canonical = json.dumps(members, separators=(",", ":"), sort_keys=True).encode()
        self.kid = base64.urlsafe_b64encode(hashlib.sha256(canonical).digest()).rstrip(b"=").decode()
        self.jwks = {"keys": [{**public, "kid": self.kid, "alg": "ES256", "use": "sig"}]}

    def session_token(self) -> str:
        """A token for a fresh anonymous session, with the session lifetime the contract fixes."""
        session = base64.urlsafe_b64encode(str(uuid.uuid4()).encode()).rstrip(b"=").decode()
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "aud": SESSION_AUDIENCE,
            "sub": f"aion:v1:AnonymousSession:{session}",
            "token_use": "anonymous_session",
            "contract_version": 1,
            "assurance": "session",
            "iat": now,
            "nbf": now,
            "exp": now + SESSION_LIFETIME,
        }
        headers = {"typ": "aion-session+jwt", "kid": self.kid}
        return jwt.encode(claims, self.key, algorithm="ES256", headers=headers)


@contextmanager
def key_server(signing_key: SigningKey) -> Iterator[str]:
    """Publish the key set on a local port; yields the base URL to use as AION_API_HOST."""
    body = json.dumps(signing_key.jwks).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - the name http.server dispatches on
            found = self.path == KEYS_PATH
            self.send_response(200 if found else 404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if found:
                self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()


def free_port_pair() -> int:
    """A port P with P + 1 also free: `aion serve` puts its proxy on P and the agent on P + 1."""
    while True:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        if port < 65535 and _is_free(port) and _is_free(port + 1):
            return port


def _is_free(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


@contextmanager
def serve(agent_dir: Path, api_host: str, port: int, card_url: str, log_path: Path) -> Iterator[None]:
    """Run `aion serve` from this environment with no credentials until its proxy serves the agent card."""
    env = {name: value for name, value in os.environ.items() if name not in ("AION_CLIENT_ID", "AION_CLIENT_SECRET", "DEPLOYMENT_ID")}
    env.update(
        AION_API_HOST=api_host,
        AION_API_CLIENT_AUTH_ISSUER=ISSUER,
        PYTHON_DOTENV_DISABLED="1",
        PYTHONPATH=os.pathsep.join(filter(None, [str(agent_dir), env.get("PYTHONPATH")])),
    )
    aion = Path(sys.executable).with_name("aion")
    with log_path.open("w") as log:
        process = subprocess.Popen(
            [str(aion), "serve", "--port", str(port)],
            cwd=agent_dir, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    try:
        deadline = time.monotonic() + START_TIMEOUT
        while not _serves(card_url):
            if process.poll() is not None:
                raise RuntimeError(f"aion serve exited with code {process.returncode} before the agent was ready")
            if time.monotonic() > deadline:
                raise RuntimeError(f"the agent was not ready within {START_TIMEOUT} s")
            time.sleep(0.5)
        yield
    finally:
        _stop(process)


def _serves(url: str) -> bool:
    try:
        return httpx.get(url, timeout=5).status_code == 200
    except httpx.HTTPError:
        return False


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


class Client:
    """Sends turns to one agent over A2A JSON-RPC and reads back the task each one ends in."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.http = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            headers={"Authorization": f"Bearer {token}", "A2A-Version": "1.0"},
        )

    def turn(self, text: str, *, context_id: str, task_id: Optional[str], stream: bool) -> dict[str, Any]:
        """Send one message and return the task it left, as GetTask reports it."""
        message = {"messageId": str(uuid.uuid4()), "role": "ROLE_USER", "contextId": context_id, "parts": [{"text": text}]}
        if task_id:
            message["taskId"] = task_id
        params = {"message": message}
        if stream:
            task_id = self._stream(params) or task_id
        else:
            task_id = self._call("SendMessage", params).get("task", {}).get("id") or task_id
        if not task_id:
            raise RuntimeError("the agent answered without a task")
        return self._call("GetTask", {"id": task_id})

    def _call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.http.post(self.url, json=_request(method, params))
        if response.is_error:
            raise RuntimeError(f"{method} answered HTTP {response.status_code}: {response.text[:300]}")
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"{method} failed: {body['error']}")
        return body["result"]

    def _stream(self, params: dict[str, Any]) -> Optional[str]:
        task_id = None
        with self.http.stream("POST", self.url, json=_request("SendStreamingMessage", params)) as response:
            if response.is_error:
                raise RuntimeError(f"SendStreamingMessage answered HTTP {response.status_code}: {response.read()[:300]!r}")
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                body = json.loads(line[5:])
                if "error" in body:
                    raise RuntimeError(f"SendStreamingMessage failed: {body['error']}")
                event = body["result"]
                update = event.get("statusUpdate") or event.get("artifactUpdate") or {}
                task_id = task_id or event.get("task", {}).get("id") or update.get("taskId")
        return task_id


def _request(method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}


def check(task: dict[str, Any], expected: str) -> Optional[str]:
    """Why ``task`` does not end as ``expected``, or None when it does."""
    status = task.get("status", {})
    state = status.get("state")
    if state != expected:
        return f"ended {state}, expected {expected}"
    if expected != "TASK_STATE_COMPLETED":
        parts = status.get("message", {}).get("parts", [])
        if not any(part.get("text", "").strip() for part in parts):
            return f"ended {state} without saying why in its status message"
    return None


def run(client: Client, examples: list[str], *, stream: bool) -> list[str]:
    """Send every example in one conversation; returns the failures."""
    mode = "stream" if stream else "send"
    context_id = str(uuid.uuid4())
    failures = []
    for text in examples:
        keyword = text.split()[0].lower()
        expected = EXPECTED_STATE.get(keyword, "TASK_STATE_COMPLETED")
        turns = [(text, expected)]
        if expected == "TASK_STATE_INPUT_REQUIRED":
            turns.append((ANSWER, "TASK_STATE_COMPLETED"))
        task_id = None
        for sent, wanted in turns:
            label = f"{mode:6} {sent!r}"
            try:
                task = client.turn(sent, context_id=context_id, task_id=task_id, stream=stream)
                if task_id and task.get("id") != task_id:
                    problem = "the answer opened a new task instead of continuing the paused one"
                else:
                    problem = check(task, wanted)
                task_id = task.get("id")
            except (httpx.HTTPError, RuntimeError) as error:
                problem = str(error)
            print(f"{'FAIL' if problem else 'ok':4}  {label}{'  — ' + problem if problem else ''}", flush=True)
            if problem:
                failures.append(f"{label}: {problem}")
                break
    return failures


def main() -> int:
    agent_dir = Path.cwd()
    agents = yaml.safe_load((agent_dir / "aion.yaml").read_text())["aion"]["agents"]
    if len(agents) != 1:
        print(f"expected one agent in aion.yaml, found {len(agents)}")
        return 1
    (agent_id, definition), = agents.items()
    examples = [example for skill in definition.get("skills", []) for example in skill.get("examples", [])]
    if not examples:
        print(f"agent {agent_id!r} advertises no skill examples to run")
        return 1

    signing_key = SigningKey()
    log_path = Path(tempfile.mkdtemp(prefix="aion-smoke-")) / "serve.log"
    failures: list[str] = []
    try:
        with key_server(signing_key) as api_host:
            # Chosen once the key server holds its port, so the two cannot meet.
            port = free_port_pair()
            agent_url = f"http://127.0.0.1:{port}/agents/{agent_id}/"
            with serve(agent_dir, api_host, port, f"{agent_url}.well-known/agent-card.json", log_path):
                client = Client(agent_url, signing_key.session_token())
                print(f"agent {agent_id!r}: {len(examples)} examples, send and stream", flush=True)
                for stream in (False, True):
                    failures += run(client, examples, stream=stream)
    except RuntimeError as error:
        failures.append(str(error))

    if failures:
        print(f"\n{len(failures)} failed:")
        for failure in failures:
            print(f"  {failure}")
        print(f"\nLast lines of the aion serve log ({log_path}):")
        print("\n".join(log_path.read_text(errors="replace").splitlines()[-80:]))
        return 1
    print("all turns ended as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
