"""
OpenAI-Compatible Request/Response Models + InferenceRequest dataclass.

Extracted from api_server.py to keep models in one place.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


# =========================================================================
# OpenAI-Compatible Request/Response Models
# =========================================================================


class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class ChatCompletionRequest(BaseModel):
    """OpenAI /v1/chat/completions request format."""

    model: str = "auto"
    messages: List[ChatMessage] = []
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: Optional[int] = 2048
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None
    n: int = 1
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    user: Optional[str] = None
    grammar: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    seed: Optional[int] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    logit_bias: Optional[Dict[str, float]] = None
    top_k: Optional[int] = None
    min_p: Optional[float] = None
    repeat_penalty: Optional[float] = None


class CompletionRequest(BaseModel):
    """OpenAI /v1/completions (legacy)."""

    model: str = "auto"
    prompt: Union[str, List[str]] = ""
    suffix: Optional[str] = None
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: Optional[int] = 2048
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None
    echo: bool = False
    seed: Optional[int] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    logit_bias: Optional[Dict[str, float]] = None


class CompactRequest(BaseModel):
    """Request for /v1/compact endpoint."""

    messages: List[ChatMessage] = []
    keep_last_n: int = 4
    summarize_older: bool = True
    compress_text: bool = True
    target_tokens: int = 4096


class EmbeddingRequest(BaseModel):
    """OpenAI /v1/embeddings request format."""

    input: Union[str, List[str]]
    model: str = "auto"
    encoding_format: str = "float"


class TokenizeRequest(BaseModel):
    """Tokenize request."""

    content: str
    add_special: bool = False
    with_pieces: bool = False


class DetokenizeRequest(BaseModel):
    """Detokenize request."""

    tokens: List[int]


class TokenCountRequest(BaseModel):
    """Count tokens without full tokenization."""

    content: str


class InfillRequest(BaseModel):
    """Dedicated FIM/infill endpoint request."""

    prompt: str = ""
    suffix: str = ""
    model: str = "auto"
    max_tokens: Optional[int] = 256
    temperature: float = 0.2
    top_p: float = 0.9
    stop: Optional[Union[str, List[str]]] = None
    stream: bool = False


class LoRALoadRequest(BaseModel):
    """Request to load a LoRA adapter at runtime."""

    lora_path: str
    scale: float = 1.0


class ModelPullRequest(BaseModel):
    """Download a GGUF model from HuggingFace Hub."""

    repo_id: str
    filename: str


class StateSaveRequest(BaseModel):
    """Save model KV-cache state to disk."""

    slot_name: str = "default"


class StateLoadRequest(BaseModel):
    """Load model KV-cache state from disk."""

    slot_name: str = "default"


# =========================================================================
# Inference Request — proper dataclass
# =========================================================================


@dataclass
class InferenceRequest:
    """Structured request passed to the adapter."""

    prompt: str = ""
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    stream: bool = False
    messages: List[Dict[str, str]] = field(default_factory=list)
    grammar: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    suffix: Optional[str] = None
    echo: bool = False
    seed: Optional[int] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    logit_bias: Optional[Dict[str, float]] = None
    top_k: Optional[int] = None
    min_p: Optional[float] = None
    repeat_penalty: Optional[float] = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
