"""Tests de los canales Telegram y Teams (Fase 5) con engine falso y HTTP mock."""
from __future__ import annotations

import httpx

from zenaidarag.api import Engine
from zenaidarag.channels import format_reply
from zenaidarag.channels.teams_adapter import handle_activity
from zenaidarag.channels.telegram import TelegramBot, reply_for_message
from zenaidarag.config import Settings
from zenaidarag.llm.fake import FakeLLM
from zenaidarag.rag.answer import Answer
from zenaidarag.store import Chunk, Retrieved


class StubStore:
    def __init__(self, results):
        self._results = results

    def query(self, vector, top_k):
        return self._results[:top_k]

    def get_all(self):
        return [r.chunk for r in self._results]

    def count(self):
        return len(self._results)


class StubEmbeddings:
    def embed_query(self, text):
        return [0.0]

    def embed_documents(self, texts):
        return [[0.0] for _ in texts]


def _res(text, source, score):
    return Retrieved(chunk=Chunk(id=source, text=text, source=source), score=score)


def _engine(results, min_score=0.15):
    return Engine(
        store=StubStore(results),
        embeddings=StubEmbeddings(),
        llm=FakeLLM(),
        settings=Settings(min_score=min_score),
    )


# ---------- format_reply ----------

def test_format_reply_appends_sources():
    ans = Answer(text="respuesta", sources=["a.md", "b.md"], refused=False)
    out = format_reply(ans)
    assert "respuesta" in out and "Fuentes: a.md, b.md" in out


def test_format_reply_refusal_has_no_sources():
    ans = Answer(text="No tengo informacion suficiente.", sources=[], refused=True)
    assert format_reply(ans) == "No tengo informacion suficiente."


# ---------- reply_for_message (Telegram logic) ----------

def test_reply_start_shows_welcome():
    out = reply_for_message("/start", _engine([_res("a", "s.md", 0.9)]))
    assert "ZenaidaRAG" in out


def test_reply_grounded_question_cites_sources():
    out = reply_for_message("algo", _engine([_res("contexto", "dental.md", 0.9)]))
    assert "Fuentes: dental.md" in out


def test_reply_out_of_domain_refuses():
    out = reply_for_message("capital de Francia", _engine([_res("x", "x.md", 0.01)]))
    assert "no tengo" in out.lower()


def test_reply_empty_prompts_for_text():
    out = reply_for_message("   ", _engine([_res("a", "s.md", 0.9)]))
    assert "pregunta" in out.lower()


# ---------- Teams adapter ----------

def test_teams_message_activity_answers():
    act = {"type": "message", "text": "algo sobre perros"}
    resp = handle_activity(act, _engine([_res("contexto", "dental.md", 0.9)]))
    assert resp["type"] == "message"
    assert "Fuentes: dental.md" in resp["text"]


def test_teams_non_message_ignored():
    resp = handle_activity({"type": "conversationUpdate"}, _engine([_res("a", "s.md", 0.9)]))
    assert resp == {"type": "message"}


# ---------- TelegramBot con HTTP mockeado ----------

def test_bot_process_update_sends_reply():
    engine = _engine([_res("contexto", "dental.md", 0.9)])
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        # Captura la llamada a sendMessage.
        import json

        body = json.loads(request.content)
        sent["chat_id"] = body.get("chat_id")
        sent["text"] = body.get("text")
        return httpx.Response(200, json={"ok": True, "result": {}})

    bot = TelegramBot("fake-token", engine)
    bot._client = httpx.Client(transport=httpx.MockTransport(handler))

    update = {"update_id": 1, "message": {"chat": {"id": 42}, "text": "algo"}}
    bot.process_update(update)

    assert sent["chat_id"] == 42
    assert "Fuentes: dental.md" in sent["text"]


def test_bot_ignores_update_without_text():
    engine = _engine([_res("a", "s.md", 0.9)])
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True, "result": {}})

    bot = TelegramBot("fake-token", engine)
    bot._client = httpx.Client(transport=httpx.MockTransport(handler))
    bot.process_update({"update_id": 2, "message": {"chat": {"id": 1}}})  # sin text
    assert calls == []  # no se envio nada


def test_poll_once_tolerates_read_timeout():
    # Un timeout de long-polling (sin mensajes) NO debe romper: se conserva offset.
    engine = _engine([_res("a", "s.md", 0.9)])

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    bot = TelegramBot("fake-token", engine)
    bot._client = httpx.Client(transport=httpx.MockTransport(handler))
    assert bot.poll_once(5) == 5  # offset intacto, sin excepcion


def test_poll_once_processes_and_advances_offset():
    engine = _engine([_res("contexto", "dental.md", 0.9)])
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        if request.url.path.endswith("getUpdates"):
            return httpx.Response(200, json={"ok": True, "result": [
                {"update_id": 10, "message": {"chat": {"id": 7}, "text": "algo"}}
            ]})
        sent.append(body.get("text"))
        return httpx.Response(200, json={"ok": True, "result": {}})

    bot = TelegramBot("fake-token", engine)
    bot._client = httpx.Client(transport=httpx.MockTransport(handler))
    new_offset = bot.poll_once(None)
    assert new_offset == 11  # update_id + 1
    assert sent and "Fuentes: dental.md" in sent[0]
