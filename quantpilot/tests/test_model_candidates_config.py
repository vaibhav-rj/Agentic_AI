from src.llm.config import MODEL_CANDIDATES, ModelRole
from typing import cast, Literal

NEW_CANDIDATES = {
    "reasoning": {
        "@cf/qwen/qwen3-30b-a3b-fp8",
        "@cf/zai-org/glm-4.7-flash",
        "@cf/nvidia/nemotron-3-120b-a12b",
        "nvidia/nemotron-3.5-super-vl:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    },
    "judge": {
        "@cf/meta/llama-4-scout-17b-16e-instruct",
        "@cf/mistralai/mistral-small-3.1-24b-instruct",
        "reflection/beam-free",
        "cohere/north-mini-code:free",
        "@cf/ibm-granite/granite-4.0-h-micro",
        "nvidia/nemotron-3.5-lightning:free",
    },
    "guardrail": {
        "@cf/mistral/mistral-7b-instruct-v0.2-lora",
        "@cf/meta/llama-3.2-3b-instruct",
        "stealth/glyph-cluster",
        "stealth/crouton-alpha",
    },
}

EXPECTED_NEW_PRIORITIES = {
    "reasoning": {1: 2, 2: 2, 3: 2},
    "judge": {1: 2, 2: 2, 3: 2},
    "guardrail": {1: 1, 2: 2, 3: 1},
}


def test_candidate_counts_and_original_sequences_preserved():
    for role, new_ids in NEW_CANDIDATES.items():
        candidates = MODEL_CANDIDATES[cast(ModelRole, role)]

        assert len(candidates) == 4 + len(new_ids)

        original_candidates = [
            c for c in candidates if c.model_id not in new_ids
        ]

        assert len(original_candidates) == 4
        assert sorted(c.priority for c in original_candidates) == [
            1, 2, 3, 4
        ]


def test_new_candidate_registration():
    for role, expected_ids in NEW_CANDIDATES.items():
        candidates = MODEL_CANDIDATES[cast(ModelRole, role)]
        new_candidates = [
            c for c in candidates if c.model_id in expected_ids
        ]

        assert {c.model_id for c in new_candidates} == expected_ids
        assert len(new_candidates) == len(expected_ids)
        assert all(not c.enabled for c in new_candidates)

        actual_priorities = {}
        for candidate in new_candidates:
            actual_priorities[candidate.priority] = (
                actual_priorities.get(candidate.priority, 0) + 1
            )

        assert actual_priorities == EXPECTED_NEW_PRIORITIES[role]


def test_new_candidate_provider_and_api_key_configuration():
    for role, expected_ids in NEW_CANDIDATES.items():
        for candidate in MODEL_CANDIDATES[cast(ModelRole, role)]:
            if candidate.model_id not in expected_ids:
                continue

            if candidate.provider == "cloudflare":
                assert candidate.api_key_env == "CLOUDFLARE_API_KEY"
            elif candidate.provider == "kilocode":
                assert candidate.api_key_env == "KILOCODE_API_KEY"
            else:
                raise AssertionError(
                    f"Unexpected provider: {candidate.provider}"
                )