
import gc
import torch

from typing import Any

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline,
)

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline


_ACTIVE_MODEL_ID = None
_ACTIVE_MODEL = None
_ACTIVE_TOKENIZER = None

class TemplateAwareChatModel(BaseChatModel):
    tokenizer: Any
    llm: Any

    @property
    def _llm_type(self) -> str:
        return "template-aware-huggingface"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        role_map = {
            "system": "system",
            "human": "user",
            "ai": "assistant",
            "tool": "tool",
        }
        formatted = [
            {"role": role_map.get(m.type, "user"), "content": m.content}
            for m in messages
        ]

        try:
            prompt = self.tokenizer.apply_chat_template(
                formatted,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            prompt = self.tokenizer.apply_chat_template(
                formatted,
                tokenize=False,
                add_generation_prompt=True,
            )

        response = self.llm.invoke(prompt, stop=stop)
        if not isinstance(response, str):
            response = str(response)

        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=response))]
        )

def build_crude_model(model_id: str):
    global _ACTIVE_MODEL_ID, _ACTIVE_MODEL, _ACTIVE_TOKENIZER

    if _ACTIVE_MODEL_ID == model_id and _ACTIVE_MODEL is not None:
        return _ACTIVE_MODEL, _ACTIVE_TOKENIZER

    # Evict the previous cached base model before loading another.
    _ACTIVE_MODEL = None
    _ACTIVE_TOKENIZER = None
    _ACTIVE_MODEL_ID = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    tokenizer = AutoTokenizer.from_pretrained(model_id)

    ''''
    if "Qwen3" in model_id and tokenizer.chat_template:
        tokenizer.chat_template = tokenizer.chat_template.replace(
            "set enable_thinking = true",
            "set enable_thinking = false",
        )
    '''

    quantized_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quantized_config,
        device_map="auto",
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    _ACTIVE_MODEL_ID = model_id
    _ACTIVE_MODEL = model
    _ACTIVE_TOKENIZER = tokenizer

    print(f"[HF] Base model ready: {model_id}", flush=True)
    return model, tokenizer


def integrate_parameters(
    model_id: str,
    temperature: float,
    max_new_tokens: int,
) -> TemplateAwareChatModel: # ChatHuggingFace
    model, tokenizer = build_crude_model(model_id)

    generation_pipeline = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        do_sample=temperature > 0,
        return_full_text=False,
    )

    #return ChatHuggingFace(llm=HuggingFacePipeline(pipeline=generation_pipeline))
    return TemplateAwareChatModel(tokenizer=tokenizer,llm=HuggingFacePipeline(pipeline=generation_pipeline),)


def build_huggingface_chat_model(
    model_id: str,
    temperature: float,
    max_new_tokens: int,
) -> TemplateAwareChatModel:# ChatHuggingFace
    return integrate_parameters(model_id, temperature, max_new_tokens)
