# Research Notes: Emotional Audio Integration

## Target Model: Qwen2-Audio-7B-Instruct

Qwen2-Audio is a multi-modal model that can accept both audio and text inputs and generate text or audio outputs.

### Hugging Face Pipeline
```python
from transformers import Qwen2AudioForConditionalGeneration, AutoProcessor

processor = AutoProcessor.from_pretrained("Qwen/Qwen2-Audio-7B-Instruct")
model = Qwen2AudioForConditionalGeneration.from_pretrained("Qwen/Qwen2-Audio-7B-Instruct", device_map="auto")

conversation = [
    {'role': 'system', 'content': 'You are a helpful assistant.'},
    {'role': 'user', 'content': [
        {'type': 'audio', 'audio_url': 'path/to/input.wav'}, # Optional: simple TTS doesn't need input audio
        {'type': 'text', 'text': 'Read this text with excitement: "Hello World!"'}
    ]}
]

text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)

inputs = processor(text=text, return_tensors="pt", padding=True)

# Generate
generate_ids = model.generate(**inputs, max_new_tokens=256)
```

**Issue**: Qwen2-Audio generates *text* responses describing audio, or processes audio input. The *Speech Generation* (TTS) capability specifically for "emotional text-to-speech" might strictly require **CosyVoice** or using Qwen2-Audio in a specific mode if it supports direct waveform output (which is rare for LLMs directly, usually they output tokens for a vocoder).

## Qwen Native Strategy (User Request)

The user has identified that the latest Qwen models (likely **Qwen2-Audio** or **Qwen2.5-Omni**) have native emotional capabilities. We will leverage this directly to avoid "starting from zero" with separate TTS systems.

### Capabilities
- **Audio Generation**: Qwen2-Audio can generate speech from text.
- **Emotional Control**: By prompting with specific instructions (e.g., "Read this with excitement"), the model modulates its output prosody.
- **Voice Interaction Mode**: The model can operate in a "Voice Chat" mode where it outputs audio tokens directly.

### Integration Approach
1. **Model**: Load `Qwen/Qwen2-Audio-7B-Instruct` (or the specific "Emotional" variant if available).
2. **Prompting**:
   ```
   User: <|audio_start|> [Generate Audio] Read the following sentence in a [Sad] voice: "I cannot do that." <|audio_end|>
   Model: <|audio_start|> [Audio Tokens] <|audio_end|>
   ```
3. **Architecture**:
   - The **Orchestrator** will detect the need for voice.
   - It will forward the text + emotion tag to the **Audio Expert** (Qwen Native).
   - The Audio Expert returns the waveform.

### Advantages
- **Single Ecosystem**: Keeps everything within the Qwen family (Text + Audio).
- **Richness**: LLM-based audio is often more expressive than standard TTS.

