import pytest
from langchain_core.messages import HumanMessage
from src.llm.litellm_gateway import get_litellm_model
from src.llm import invoke_with_fallback

@pytest.mark.parametrize(
    "role",
    ["reasoning", "judge", "guardrail"]
)

def test_litellm_gateway(role):
    model = get_litellm_model(role)

    response = model.invoke([
        HumanMessage(content="Reply with exactly: QuantPilot API ready")
    ])

    print(f"\n{role}: {response.content!r}")

    print("Response metadata:", repr(response.response_metadata))
    print("Additional kwargs:", repr(response.additional_kwargs))
    print("Hidden params:", repr(getattr(response, "hidden_params", None)))

    assert response.content


def test_invoke_with_fallback():
    response = invoke_with_fallback(
        "guardrail",
        [
            HumanMessage(
                content="Reply with exactly: QuantPilot fallback ready"
            )
        ]
    )

    print(f"\ninvoke_with_fallback: {response.content!r}")
    assert response is not None
    assert isinstance(response.content, str)
    assert response.content.strip()