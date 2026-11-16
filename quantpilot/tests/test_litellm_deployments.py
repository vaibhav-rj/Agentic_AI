# tests/test_litellm_deployments.py

import os
from unittest.mock import patch

from src.llm.litellm_gateway import _build_model_list


def test_reasoning_deployments():
    with patch.dict(os.environ, {
        "GROQ_API_KEY": "test",
        "NVIDIA_API_KEY": "test",
        "GOOGLE_API_KEY": "test",
        "CLOUDFLARE_API_KEY": "test",
        "KILOCODE_API_KEY": "test",
    }):
        deployments, candidates = _build_model_list("reasoning")

    assert deployments
    assert len(deployments) == len(candidates)

    # Every deployment must belong to the reasoning Router group.
    assert all(
        d["model_name"] == "quantpilot-reasoning"
        for d in deployments
    )

    # Priority and deployment identity must be preserved.
    assert all(
        isinstance(d["litellm_params"]["order"], int)
        for d in deployments
    )

    ids = [d["model_info"]["id"] for d in deployments]
    assert len(ids) == len(set(ids))

    # Provider metadata and temperature must be present.
    assert all(d["model_info"]["provider"] for d in deployments)
    assert all(
        d["litellm_params"]["temperature"] == 0.1
        for d in deployments
    )