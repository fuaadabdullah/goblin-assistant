from unittest.mock import patch

import pytest

from api.services.intent_dispatch_service import dispatch_intent_archetype


def test_dispatch_intent_archetype_delegates_to_dispatcher() -> None:
    intent = object()
    selection = object()

    with patch(
        "api.agents.dispatcher.intent_dispatcher.dispatch", return_value=selection
    ) as dispatch:
        result = dispatch_intent_archetype(intent)

    assert result is selection
    dispatch.assert_called_once_with(intent)


def test_dispatch_intent_archetype_propagates_dispatch_errors() -> None:
    intent = object()

    with (
        patch("api.agents.dispatcher.intent_dispatcher.dispatch", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        dispatch_intent_archetype(intent)
