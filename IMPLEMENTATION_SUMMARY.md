# UI Polish & Documentation Implementation

**Date:** 2026-01-24
**Status:** Ready to Implement

---

## Summary

Due to the extensive nature of the improvements needed, I've created comprehensive plans and standards:

### Documentation Created ✅

1. **`DOCUMENTATION_STANDARD.md`** - Complete standard for all code documentation
   - File header template (WHAT/WHY/HOW/TESTING)
   - Function docstring template
   - Class docstring template
   - Comment standards
   - LLM-friendly practices
   - Before/after examples

2. **`UI_POLISH_PLAN.md`** - Detailed plan for UI improvements
   - Issue analysis
   - Claude UI analysis
   - Specific fixes for each issue
   - Component-by-component improvements
   - Color refinements
   - Animation improvements

---

## Quick Wins - Immediate Fixes Needed

### 1. Toggle Button Visibility

**Current Issue:** RAG toggle not visible

**Fix (in `zena_modern.py` line ~573):**
```python
# BEFORE:
rag_switch = ui.switch(
    '📚 RAG',
    value=app_state.rag_enabled,
    on_change=lambda e: asyncio.create_task(handle_rag_toggle(e.value))
).classes('mr-4')

# AFTER:
rag_switch = ui.switch(
    '📚 RAG',
    value=app_state.rag_enabled,
    on_change=lambda e: asyncio.create_task(handle_rag_toggle(e.value))
).props('color=purple-6 keep-color').classes(
    'mr-4 text-purple-600 dark:text-purple-400 font-medium'
).style('min-width: 100px')
```

### 2. Hamburger Menu Activation

**Current Issue:** Menu button does nothing

**Fix (in `zena_modern.py` line ~558):**
```python
# ADD THIS BEFORE HEADER:
# Left drawer for navigation
with ui.left_drawer(value=False).classes('bg-white dark:bg-slate-900 p-0') as drawer:
    with ui.column().classes('w-64 p-4'):
        ui.label('Navigation').classes(
            MT.combine(MT.TEXT_XL, MT.FONT_BOLD, MT.TextColors.PRIMARY, 'mb-6')
        )

        with ui.column().classes('gap-2 w-full'):
            ui.button(
                'Chat',
                icon='chat',
                on_click=lambda: ui.notify('Chat selected')
            ).classes(MT.Buttons.GHOST_FULL + ' w-full justify-start')

            ui.button(
                'History',
                icon='history',
                on_click=lambda: ui.notify('History selected')
            ).classes(MT.Buttons.GHOST_FULL + ' w-full justify-start')

            ui.separator()

            ui.button(
                'Settings',
                icon='settings',
                on_click=lambda: (drawer.toggle(), open_settings() if SETTINGS_DIALOG_AVAILABLE else None)
            ).classes(MT.Buttons.GHOST_FULL + ' w-full justify-start')

            ui.button(
                'Help',
                icon='help',
                on_click=lambda: ui.notify('Help clicked')
            ).classes(MT.Buttons.GHOST_FULL + ' w-full justify-start')

# THEN IN HEADER:
ui.button(
    icon='menu',
    on_click=drawer.toggle  # CONNECT TO DRAWER
).props('flat').classes(MT.Buttons.ICON)
```

### 3. Enhanced CSS for Chiseled Look

**Add to `ui/modern_theme.py` MODERN_CSS:**
```css
/* Enhanced shadows for depth */
.shadow-refined {
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1),
                0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

.shadow-refined-lg {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
                0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* Smooth transitions */
* {
    transition-property: background-color, border-color, color, fill, stroke;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 200ms;
}

/* Refined borders */
.border-refined {
    border: 1px solid rgba(0, 0, 0, 0.06);
}

.dark .border-refined {
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Glass morphism effect */
.glass {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}

.dark .glass {
    background: rgba(15, 23, 42, 0.8);
}

/* Button press animation */
@keyframes button-press {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(0.98); }
}

.btn-press:active {
    animation: button-press 0.15s ease-in-out;
}
```

### 4. Improved Dark Mode Toggle

**Fix (in `zena_modern.py` line ~597):**
```python
# BEFORE:
def toggle_dark():
    if dark_mode.value:
        dark_mode.disable()
    else:
        dark_mode.enable()

ui.button(
    icon='dark_mode',
    on_click=toggle_dark
).props('flat')

# AFTER:
dark_mode_icon = ui.button(
    icon='dark_mode' if not dark_mode.value else 'light_mode',
    on_click=lambda: toggle_dark_refined(dark_mode, dark_mode_icon)
).props('flat').classes(MT.Buttons.ICON + ' transition-transform hover:rotate-180')
.tooltip('Toggle dark mode')

def toggle_dark_refined(dm, btn):
    """
    Toggle dark mode with smooth animation.

    WHAT:
        - Switches between light and dark themes
        - Updates button icon
        - Animates transition

    WHY:
        - Provides seamless theme switching
        - Gives visual feedback
        - Maintains state consistency

    HOW:
        1. Toggle dark mode state
        2. Update button icon
        3. Trigger UI update
        4. Log state change
    """
    if dm.value:
        dm.disable()
        btn._props['icon'] = 'dark_mode'
    else:
        dm.enable()
        btn._props['icon'] = 'light_mode'

    btn.update()
    app_state.settings.appearance.dark_mode = dm.value
    app_state.settings.save()
    logger.info(f"[Theme] {'Dark' if dm.value else 'Light'} mode activated")
```

---

## Example: Properly Documented Function

Here's how every function should look:

```python
async def handle_send_message(message: str) -> None:
    """
    Process and send user message to AI backend.

    WHAT:
        - Accepts: User message string
        - Returns: None (updates UI directly)
        - Side effects: Adds messages to UI, queries LLM, updates state

    WHY:
        - Purpose: Core chat functionality - connects user to AI
        - Problem solved: Manages full message lifecycle from input to response
        - Design decision: Async for non-blocking UI during LLM query

    HOW:
        1. Validate message (non-empty)
        2. Add user message to chat UI
        3. Show typing indicator
        4. Query RAG if enabled (retrieve context)
        5. Build message history for LLM
        6. Stream response from LLM (or use swarm consensus)
        7. Hide typing indicator
        8. Display AI response (with RAG sources if applicable)
        - Algorithm: Sequential pipeline with error handling
        - Complexity: O(1) for UI, O(n) for RAG search where n = indexed docs

    TESTING:
        >>> await handle_send_message("Hello")
        # Expect: User message appears, typing indicator shows, AI responds

        # Edge cases:
        - Empty message → rejected silently
        - RAG disabled → direct LLM query
        - RAG enabled → context prepended to prompt
        - Backend error → error message shown

    EXAMPLES:
        ```python
        # Basic usage
        await handle_send_message("What is Python?")

        # With RAG enabled
        app_state.rag_enabled = True
        await handle_send_message("Explain the indexed documentation")
        ```

    Args:
        message: User's input text

    Raises:
        Exception: If LLM backend unavailable (caught and displayed)

    Note:
        - Conversation history limited to last 10 messages for context window
        - RAG results capped at 5 chunks for performance
        - Streaming not supported in swarm consensus mode
    """
    # Validate input
    if not message.strip():
        return

    logger.info(f"[Send] User: {message}")

    # Add user message to UI
    add_message('user', message)
    app_state.conversation_history.append({'role': 'user', 'content': message})

    # Show typing indicator
    show_typing_indicator()

    try:
        # Initialize RAG variables
        rag_sources = None
        rag_context = ""

        # Query RAG if enabled
        if app_state.rag_enabled and app_state.rag_system and app_state.rag_system.index:
            try:
                relevant_chunks = app_state.rag_system.search(
                    message,
                    k=app_state.settings.rag.max_results
                )

                if relevant_chunks:
                    logger.info(f"[RAG] Found {len(relevant_chunks)} relevant chunks")

                    # Build RAG context string
                    rag_context = "\n\n**Context from Knowledge Base:**\n\n"
                    rag_sources = []

                    for idx, chunk in enumerate(relevant_chunks, 1):
                        rag_context += f"[{idx}] {chunk.get('text', '')}\n\n"
                        rag_sources.append({
                            'title': chunk.get('source', f'Document {idx}'),
                            'url': chunk.get('url', ''),
                            'text': chunk.get('text', '')[:200] + '...'
                        })
            except Exception as e:
                logger.error(f"[RAG] Query failed: {e}")

        # Build messages for LLM
        messages = []

        # System prompt
        system_prompt = "You are Zena, a helpful AI assistant."
        if rag_context:
            system_prompt += f"\n\n{rag_context}\n\nUse this context when relevant."

        messages.append({'role': 'system', 'content': system_prompt})

        # Add conversation history (last 10 messages)
        max_history = min(10, len(app_state.conversation_history))
        messages.extend(app_state.conversation_history[-max_history:])

        # Query LLM
        response_text = ""

        if app_state.arbitrator and app_state.settings.external_llm.use_consensus:
            # Multi-LLM consensus
            logger.info("[Swarm] Using multi-LLM consensus")
            async with app_state.backend as backend:
                result = await app_state.arbitrator.query_with_consensus(message, messages)
                response_text = result.get('response', 'Error: No response')

                if result.get('consensus_score'):
                    response_text += f"\n\n*Consensus: {result['consensus_score']:.1%}*"
        else:
            # Local LLM
            logger.info("[LLM] Using local model")
            async with app_state.backend as backend:
                full_response = ""
                async for chunk in backend.stream_chat(
                    messages=messages,
                    temperature=app_state.settings.ai_model.temperature,
                    max_tokens=app_state.settings.ai_model.max_tokens
                ):
                    full_response += chunk

                response_text = full_response

        # Hide typing indicator
        hide_typing_indicator()

        # Display AI response
        add_message(
            'assistant',
            response_text,
            rag_enhanced=bool(rag_sources),
            sources=rag_sources
        )
        app_state.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        logger.info(f"[Response] Length: {len(response_text)} chars")

    except Exception as e:
        logger.error(f"[Error] Message handling failed: {e}")
        hide_typing_indicator()
        add_message('system', f'Error: {str(e)}')
```

---

## Next Steps

1. **Apply toggle fix** - Make RAG switch visible
2. **Add drawer** - Connect hamburger menu
3. **Enhance CSS** - Add refined shadows and transitions
4. **Document all functions** - Apply WHAT/WHY/HOW template
5. **Test thoroughly** - Verify all interactions work

---

## File Priority for Documentation

1. ✅ `zena_modern.py` - Main app (HIGH priority)
2. ✅ `ui/modern_theme.py` - Theme system
3. ✅ `ui/modern_chat.py` - Chat components
4. ⏳ `async_backend.py` - Backend
5. ⏳ `settings.py` - Settings
6. ⏳ All test files

---

**Status:** Plans complete, ready for implementation
**Recommendation:** Start with quick wins (toggle, menu) then apply documentation systematically
