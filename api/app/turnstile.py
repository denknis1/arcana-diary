"""Cloudflare Turnstile token check (§4.2): POST secret + token to siteverify, accept only success == true.

The visitor's address (the optional remoteip field) is not sent: Cloudflare gets only the token.
"""
import logging

import httpx

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
MAX_TOKEN_LENGTH = 2048  # Cloudflare tokens are far shorter; a longer one is not sent
log = logging.getLogger("arcana.turnstile")


class TurnstileVerifier:
    def __init__(self, secret: str, client: httpx.Client | None = None, timeout_s: float = 5.0):
        self.secret = secret
        self._client = client or httpx.Client(timeout=timeout_s)

    def verify(self, token: str | None) -> bool:
        if not token or not self.secret or len(token) > MAX_TOKEN_LENGTH:
            return False
        try:
            response = self._client.post(SITEVERIFY_URL, data={"secret": self.secret, "response": token})
            if response.status_code != 200:
                return False
            body = response.json()
            return isinstance(body, dict) and body.get("success") is True
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("turnstile check failed: %s", type(exc).__name__)
            return False
