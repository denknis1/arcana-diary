from urllib.parse import parse_qs

import httpx

from app.turnstile import SITEVERIFY_URL, TurnstileVerifier


def verifier(handler, secret="secret-1") -> tuple[TurnstileVerifier, list]:
    seen = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return TurnstileVerifier(secret, client=httpx.Client(transport=httpx.MockTransport(wrapped))), seen


def test_success_posts_secret_and_token_only():
    v, seen = verifier(lambda r: httpx.Response(200, json={"success": True}))
    assert v.verify("token-1") is True
    [request] = seen
    assert str(request.url) == SITEVERIFY_URL
    assert parse_qs(request.content.decode()) == {"secret": ["secret-1"], "response": ["token-1"]}


def test_rejected_token():
    v, _ = verifier(lambda r: httpx.Response(200, json={"success": False, "error-codes": ["invalid-input-response"]}))
    assert v.verify("bad") is False


def test_server_error_is_false():
    v, _ = verifier(lambda r: httpx.Response(500, text="oops"))
    assert v.verify("token-1") is False


def test_network_error_is_false():
    def boom(request):
        raise httpx.ConnectError("no route", request=request)
    v, _ = verifier(boom)
    assert v.verify("token-1") is False


def test_invalid_json_is_false():
    v, _ = verifier(lambda r: httpx.Response(200, text="not json"))
    assert v.verify("token-1") is False


def test_empty_token_makes_no_request():
    v, seen = verifier(lambda r: httpx.Response(200, json={"success": True}))
    assert v.verify(None) is False and v.verify("") is False
    assert seen == []


def test_no_secret_makes_no_request():
    v, seen = verifier(lambda r: httpx.Response(200, json={"success": True}), secret="")
    assert v.verify("token-1") is False
    assert seen == []
