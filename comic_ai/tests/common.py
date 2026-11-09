"""Faux SDK Anthropic / OpenAI pour les tests : aucun appel réseau."""

import types
from unittest.mock import patch


class _FakeError(Exception):
    status_code = 400

    @property
    def message(self):
        return self.args[0] if self.args else "error"


def _error(cls, status_code=None):
    exc = cls("boom")
    if status_code is not None:
        exc.status_code = status_code
    return exc


def make_fake_sdk(reply="Réponse IA", raise_exc=None, stop_reason="end_turn"):
    """Module factice exposant Anthropic / OpenAI et la hiérarchie d'erreurs des SDK.

    ``calls`` reçoit les kwargs de chaque appel (assertions sur la requête).
    """
    sdk = types.SimpleNamespace()
    sdk.calls = []

    class APIError(_FakeError):
        pass

    class APIStatusError(APIError):
        pass

    class APIConnectionError(APIError):
        pass

    class APITimeoutError(APIConnectionError):
        pass

    for name, code in (
        ("AuthenticationError", 401),
        ("PermissionDeniedError", 403),
        ("NotFoundError", 404),
        ("RateLimitError", 429),
    ):
        setattr(sdk, name, type(name, (APIStatusError,), {"status_code": code}))
    sdk.APIStatusError = APIStatusError
    sdk.APIConnectionError = APIConnectionError
    sdk.APITimeoutError = APITimeoutError

    def _maybe_raise():
        if raise_exc:
            exc = getattr(sdk, raise_exc[0]) if isinstance(raise_exc, tuple) else getattr(sdk, raise_exc)
            raise _error(exc, raise_exc[1] if isinstance(raise_exc, tuple) else None)

    class _Messages:
        def create(self, **kwargs):  # pylint: disable=method-required-super
            sdk.calls.append(kwargs)
            _maybe_raise()
            return types.SimpleNamespace(
                stop_reason=stop_reason,
                content=[
                    types.SimpleNamespace(type="thinking", text=""),
                    types.SimpleNamespace(type="text", text=reply),
                ],
            )

    class _Completions:
        def create(self, **kwargs):  # pylint: disable=method-required-super
            sdk.calls.append(kwargs)
            _maybe_raise()
            message = types.SimpleNamespace(content=reply)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    class Anthropic:
        def __init__(self, **kwargs):
            sdk.client_kwargs = kwargs
            self.messages = _Messages()

    class OpenAI:
        def __init__(self, **kwargs):
            sdk.client_kwargs = kwargs
            self.chat = types.SimpleNamespace(completions=_Completions())

    sdk.Anthropic = Anthropic
    sdk.OpenAI = OpenAI
    return sdk


def patch_sdk(env, sdk):
    """Remplace l'import des SDK par ``sdk`` (contexte ``with``)."""
    return patch.object(type(env["comic.ai.service"]), "_import_sdk", lambda self, name: sdk)


def configure_ai(env, provider="claude", key="test-key", model=None, lang="fr"):
    icp = env["ir.config_parameter"].sudo()
    icp.set_param("comic_ai.provider", provider)
    icp.set_param(f"comic_ai.{provider}_api_key", key)
    if model:
        icp.set_param(f"comic_ai.{provider}_model", model)
    icp.set_param("comic_ai.lang", lang)
