"""Question check before a reading (§3.1, §8.6, §9.3): crisis stop-phrases first, then a short GUARD_MODEL call.

- An unambiguous stop-phrase (either language, after normalize()) gives crisis at once; the model is not called.
- An ambiguous one ("hurt myself if I go back to my ex", "lastimarme otra vez", "¿Está mejor sin mí?") goes to
  the model; if the model does not answer, refuses or returns something unknown — crisis. A continuation turns an
  unambiguous phrase into an ambiguous one: "no quiero vivir" is a crisis at once, "no quiero vivir con él" goes to
  the model (В17).
- A refusal of the guard model on the person's text is a strong danger sign: crisis.
- Otherwise a timeout, an API error or an unknown group gives ok; the reader prompt has its own crisis safety net.
- Over the guard's own budget (GUARD_BUDGET_USD, §9.2) the model is not called: an ambiguous phrase gives crisis,
  anything else raises GuardUnavailable ("service temporarily unavailable", never a reading without a check).
- Every result says where the group came from (source), so timeouts and refusals are counted in guard_events.
The 3-second timeout is the provider's own (ClaudeProvider json_timeout_s); there is no thread pool here.
The question text is never logged.
"""
import html
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from app.reader.errors import ProviderRefusal, ProviderTimeout
from app.terms import compile_terms, find_banned, normalize

SAFETY_DIR = Path(__file__).resolve().parent
CRISIS_TERMS = SAFETY_DIR / "crisis_terms.json"
GROUPS = ("ok", "redirect_money", "redirect_topic", "redirect_person", "crisis")
NO_VERDICT_GROUPS = frozenset({"redirect_topic", "redirect_person"})  # §8.1: no yes/no for these
GUARD_SCHEMA = {
    "type": "object",
    "properties": {"group": {"type": "string", "enum": list(GROUPS)}, "violence": {"type": "boolean"}},
    "required": ["group", "violence"],
    "additionalProperties": False,
}
log = logging.getLogger("arcana.guard")


@dataclass(frozen=True)
class GuardResult:
    group: str
    source: str  # "terms" | "model" | "timeout" | "refusal" | "error" | "invalid" | "budget"
    violence: bool = False
    model: str | None = None
    ms_total: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    stop_reason: str | None = None


class GuardUnavailable(Exception):
    """The guard's own budget is spent and the question needs the model: the route answers 503 (§9.2)."""


class CrisisFilter:
    """Stop-phrases from crisis_terms.json: unambiguous self_harm and violence lists, the ambiguous
    ask_model_self_harm and ask_model_violence lists (§9.3), ask_model_continuations ("don't want to live with",
    "no quiero vivir con": cut before the unambiguous lists are searched and themselves ambiguous self_harm, В17),
    and idioms that are excluded first ("me quiero morir de la vergüenza", "my ex hit me up", "Suicide Squad").
    Everything is compared after normalize()."""

    KINDS = ("self_harm", "violence", "ask_model_self_harm", "ask_model_violence", "ask_model_continuations")

    def __init__(self, path: Path = CRISIS_TERMS):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.phrases = {kind: compile_terms([normalize(t) for terms in data[kind].values() for t in terms])
                        for kind in self.KINDS}
        self.exclude = [rx for _, rx in compile_terms([normalize(t) for terms in data["exclude"].values()
                                                       for t in terms])]

    def _clean(self, text: str) -> str:
        clean = normalize(text)
        for rx in self.exclude:
            clean = rx.sub(" ", clean)
        return clean

    def match(self, text: str) -> str | None:
        """An unambiguous stop-phrase: "violence", "self_harm" or None."""
        clean = self._clean(text)
        for _, rx in self.phrases["ask_model_continuations"]:
            clean = rx.sub(" ", clean)
        for kind in ("violence", "self_harm"):
            if find_banned(clean, self.phrases[kind]):
                return kind
        return None

    def ambiguous(self, text: str) -> str | None:
        """An ambiguous stop-phrase that the model decides: "violence", "self_harm" or None."""
        clean = self._clean(text)
        if find_banned(clean, self.phrases["ask_model_violence"]):
            return "violence"
        if find_banned(clean, self.phrases["ask_model_self_harm"] + self.phrases["ask_model_continuations"]):
            return "self_harm"
        return None


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


class Guard:
    def __init__(self, provider, system_prompt: str, prompt_version: str, terms_path: Path = CRISIS_TERMS,
                 max_tokens: int = 1024):
        self.provider = provider
        self.system_prompt = system_prompt
        self.prompt_version = prompt_version
        self.filter = CrisisFilter(terms_path)
        self.max_tokens = max_tokens

    def answers_without_model(self, text: str) -> bool:
        """True when a stop-phrase settles the question even over the guard's budget (no GuardUnavailable)."""
        return bool(self.filter.match(text) or self.filter.ambiguous(text))

    def classify(self, text: str, allow_model: bool = True) -> GuardResult:
        """allow_model=False: the guard's own budget is spent (§9.2)."""
        kind = self.filter.match(text)
        if kind:
            return GuardResult("crisis", "terms", violence=kind == "violence")
        unsure = self.filter.ambiguous(text)
        if not allow_model:
            if unsure:
                return GuardResult("crisis", "budget", violence=unsure == "violence")
            raise GuardUnavailable("guard budget reached")
        # an ambiguous stop-phrase that the model did not settle is a crisis (§9.3); otherwise ok
        failed = "crisis" if unsure else "ok"
        failed_violence = unsure == "violence"
        model = getattr(self.provider, "model", None)
        messages = [{"role": "user", "content": f"<question>{html.escape(text, quote=False)}</question>"}]
        started = time.monotonic()
        try:
            data, usage = self.provider.complete_json(self.system_prompt, messages, GUARD_SCHEMA, self.max_tokens)
        except ProviderRefusal as exc:
            log.warning("guard model refused: treated as crisis")
            r = exc.result
            return GuardResult("crisis", "refusal", False, model, _ms(started), r and r.tokens_in,
                               r and r.tokens_out, "refusal")
        except ProviderTimeout:
            log.warning("guard timeout")
            return GuardResult(failed, "timeout", failed_violence, model, _ms(started), stop_reason="timeout")
        except Exception as exc:  # any other provider failure: ok, the reader prompt has its own safety net
            log.warning("guard call failed: %s", type(exc).__name__)
            return GuardResult(failed, "error", failed_violence, model, _ms(started), stop_reason="error")
        group = data.get("group") if isinstance(data, dict) else None
        if group not in GROUPS:
            log.warning("guard returned an unknown group")
            return GuardResult(failed, "invalid", failed_violence, model, _ms(started), usage.tokens_in,
                               usage.tokens_out, usage.stop_reason)
        violence = group == "crisis" and data.get("violence") is True
        return GuardResult(group, "model", violence, model, _ms(started), usage.tokens_in, usage.tokens_out,
                           usage.stop_reason)
