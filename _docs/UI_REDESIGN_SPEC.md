
# 🎨 ZenAI Flow: UI Redesign Specification

## 1. Philosophy: "Thinking Canvas"
The goal of a chatbot (like Claude/Perplexity) is **Reading & Writing**.
-   **Current UI**: "Admin Dashboard". Sidebar is cluttered with controls.
-   **Target UI**: "Flow State". Hidden complexity.

## 2. Functional Grouping (hierarchy of Needs)

### Level 1: Primary (Always Visible)
*These interactions happen every minute.*
1.  **Chat Stream**: The content itself.
2.  **Input Bar**: Text entry, Voice Trigger, Attachment.
3.  **Send Button**: Large touch target.

### Level 2: Session Context (Top Bar / Floating)
*These happen once per session.*
1.  **Model Selector**: Which brain am I using?
    -   *Change*: Move from an open list in drawer to a **Compact Dropdown** in the header.
2.  **New Chat**: Clear canvas.
    -   *Change*: Floating Action Button (FAB) or Top-Right Icon.

### Level 3: Configuration (Hidden Menu)
*These happen rarely.*
1.  **RAG Source**: Picking a file/website.
    -   *Location*: Inside "Knowledge" menu or Settings.
2.  **Expert Mode (Swarm)**: Toggle for "Thinking Harder".
    -   *Location*: Advanced Settings or specific "Reasoning" toggle (like o1).
3.  **System Settings**: Dark Mode, Audio Output, Language.

## 3. Layout Strategy (Mobile First)

### A. The "Glass Header" (Top)
A minimal floating strip at the top.
-   **Left**: Burger Menu (≡) -> Opens History/Deep Config.
-   **Center**: Model Name (Tap to switch).
-   **Right**: New Chat (+).

### B. The "Command Capsule" (Bottom)
Instead of a full-width footer, a floating "capsule" floating above the bottom edge.
-   Contains: Input, Mic, Clip.
-   Background: Acrylic blur.

### C. The "Deep Drawer" (Hidden)
When you click the Burger Menu:
-   **History List**: Recent chats.
-   **Mode Toggles**: Swarm, RAG, Web Search.
-   **Settings**: Bottom of drawer.

## 4. Implementation Plan
1.  **Refactor `zena.py`**:
    -   Remove `ui.left_drawer` (the "Admin" drawer).
    -   Replace with `ui.header(elevated=False)` (Glass Header).
    -   Implement `ui.drawer` as a purely navigational overlay.
2.  **Refactor `ui_components.py`**:
    -   Create `ModelSelector` as a dropdown/dialog, not a card list.
    -   Group Toggles (Swarm/Router) into a single "Intelligence" expansion panel.

## 5. Visual Language (CSS)
-   **Font**: Inter (San Francisco/System stack).
-   **Colors**: Slate-950 (Dark), Slate-50 (Light).
-   **Accent**: Indigo/Violet gradients (Not corporate Blue).
-   **Radius**: `rounded-3xl` (Soft, organic).
