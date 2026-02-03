# ZenAI Visual & RAG Operations Guide 🛡️

This guide provides a mental map of the ZenAI interface and explain how the RAG (Retrieval-Augmented Generation) system handles your files.

## 🖥️ UI Layout Map

### 1. The Right Side: **Interactive Help Drawer**
- **Guided Tour**: Launch a 1-minute visual tutorial that highlights key buttons.
- **System Awareness**: ZenAI is "self-aware"—it has indexed its own source code and documentation. Ask it "How do you handle PDF files?" to see this in action.

### 2. The Bottom: **Integrated Chat & Input**
- **Type/Voice**: Use `ui-input-chat` (Type) or `ui-btn-voice` (Speak).
- **Attachments**: The `ui-btn-attach` button (Paperclip) supports PDFs, Images, and Text files.

### 3. The Left: **Configuration Drawer**
- **Model Switcher**: Hot-swap between different GGUF models.
- **RAG Status**: Toggle whether the AI should query your local knowledge base.

## 📚 RAG Deep Dive: How we "Read" your Data

### Universal Extraction 🔍
ZenAI uses a multi-stage **UniversalExtractor** to process your data:
1. **Plain Text**: Standard `.txt`, `.md`, `.py` files are read directly.
2. **PDF Files**: Logic extracts text layer by layer. If no text layer exists, it falls back to OCR.
3. **Images (OCR + YOLOv26)**: Scanned documents or screenshots are pre-processed and then analyzed via Tesseract OCR and YOLOv26 Object Detection.
4. **Video Analysis**: High-performance keyframe extraction and scene analysis using YOLOv26.

### Advanced Vision (YOLOv26) 👁️
ZenAI is equipped with **YOLOv26 (SOTA)** for real-time visual understanding:
- **Object Detection**: Identifies objects (person, car, laptop, etc.) with high confidence.
- **Scene Narratives**: Summarizes the visual content of an image for the AI's internal context.
- **Video Timelines**: Breaks down videos into a chronological narrative of events.

### Visual Heuristics & Analysis
When you upload an image, ZenAI doesn't just "read text." It uses OpenCV and YOLO to detect:
- **Screenshot vs. Photo**: Heuristics check for sharp corners and UI patterns.
- **Visual Context**: Average brightness and contrast are used to optimize OCR reliability.

### Hybrid Search 🔗
We combine two search methods for maximum accuracy:
1. **Vector Search (Qdrant)**: Finds "conceptual" matches (e.g., searching for "pets" might find "dogs").
2. **Keyword Search (BM25)**: Finds "literal" matches (e.g., searching for a specific product ID).

## 🟢 The "Local Context" Signal
When you see a **Green Tint** or a "Source [1]" citation in the AI's response, it means the information came directly from your **Private Knowledge Base**, not from the AI's training data.
