"""
Intro/Tour Manager for ZEN_RAG
Shows an interactive first-run experience explaining app capabilities.
"""

import streamlit as st


class IntroTour:
    """Manages the intro/onboarding tour for new users."""

    # Session state key
    STATE_KEY = "intro_completed"
    SLIDE_KEY = "intro_slide"

    # Tour slides
    SLIDES = [
        {
            "title": "🔬 Welcome to ZEN_RAG",
            "subtitle": "Chat with your Documents",
            "content": """
            **ZEN_RAG** is a powerful Retrieval-Augmented Generation (RAG) system
            that lets you:
            
            • 📄 Upload and analyze documents (PDFs, images, text)
            • 🔍 Search across your document collection
            • 💬 Chat with your documents using AI
            • 🔐 Keep everything private with local models
            
            Let's explore the key features!
            """,
            "icon": "🔬",
        },
        {
            "title": "⚡ Hardware Aware",
            "subtitle": "Optimized for Your System",
            "content": """
            ZEN_RAG automatically detects and optimizes for your hardware:
            
            • **CPU**: Uses all available cores for parallel processing
            • **GPU**: Detects NVIDIA/AMD GPUs and offloads inference
            • **RAM**: Adaptive batch sizing based on available memory
            • **NPU**: Leverages Ryzen AI neural processors when available
            
            Your system is automatically configured for maximum performance!
            """,
            "icon": "⚡",
        },
        {
            "title": "🔒 Privacy Focused",
            "subtitle": "Your Data Stays Local",
            "content": """
            All processing happens on your machine:
            
            • **Local Models**: Run open-source LLMs via llama.cpp or Ollama
            • **No Cloud Dependency**: No data sent to external services
            • **Optional Cloud**: Use OpenAI, Claude, or Gemini if you prefer
            • **Full Control**: You decide what data to process and how
            
            Your privacy is guaranteed!
            """,
            "icon": "🔒",
        },
        {
            "title": "🚀 Getting Started",
            "subtitle": "Ready to Begin?",
            "content": """
            ### Next Steps:
            
            1. **Sidebar Settings**: Configure your LLM provider and model
            2. **Upload Documents**: Add PDFs or images to analyze
            3. **Chat**: Ask questions about your documents
            4. **Explore**: Check out advanced features in the sidebar
            
            ### Need Help?
            - See "Local Server Helper" to start llama-server
            - Visit the GitHub repo for documentation
            - Check out example documents in the sidebar
            
            Let's get started! ✨
            """,
            "icon": "🚀",
        },
    ]

    @staticmethod
    def should_show_intro() -> bool:
        """Check if intro should be shown."""
        return not st.session_state.get(IntroTour.STATE_KEY, False)

    @staticmethod
    def mark_intro_completed() -> None:
        """Mark intro as completed."""
        st.session_state[IntroTour.STATE_KEY] = True

    @staticmethod
    def reset_intro() -> None:
        """Reset intro (for testing or user request)."""
        st.session_state[IntroTour.STATE_KEY] = False
        st.session_state[IntroTour.SLIDE_KEY] = 0

    @staticmethod
    def show_intro_modal() -> None:
        """Display the intro tour as a modal overlay."""
        if not IntroTour.should_show_intro():
            return

        # Initialize slide counter
        if IntroTour.SLIDE_KEY not in st.session_state:
            st.session_state[IntroTour.SLIDE_KEY] = 0

        current_slide = st.session_state[IntroTour.SLIDE_KEY]
        slide = IntroTour.SLIDES[current_slide]

        # Create modal container
        with st.container():
            col1, col2, col3 = st.columns([1, 10, 1])

            with col2:
                st.markdown("---")

                # Header with icon
                st.markdown(
                    f"<h1 style='text-align: center'>{slide['icon']}</h1>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<h2 style='text-align: center'>{slide['title']}</h2>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<h3 style='text-align: center; color: gray'>{slide['subtitle']}</h3>",
                    unsafe_allow_html=True,
                )

                st.markdown("---")

                # Content
                st.markdown(slide["content"])

                st.markdown("---")

                # Navigation buttons
                col_prev, col_counter, col_next, col_skip = st.columns(4)

                with col_prev:
                    if current_slide > 0:
                        if st.button("← Previous", use_container_width=True):
                            st.session_state[IntroTour.SLIDE_KEY] -= 1
                            st.rerun()
                    else:
                        st.button("← Previous", use_container_width=True, disabled=True)

                with col_counter:
                    st.markdown(
                        f"<div style='text-align: center; padding-top: 10px'>"
                        f"<strong>{current_slide + 1} / {len(IntroTour.SLIDES)}</strong>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                with col_next:
                    if current_slide < len(IntroTour.SLIDES) - 1:
                        if st.button("Next →", use_container_width=True):
                            st.session_state[IntroTour.SLIDE_KEY] += 1
                            st.rerun()
                    else:
                        if st.button(
                            "Finish 🎉",
                            use_container_width=True,
                            help="Complete the tour and start using ZEN_RAG",
                        ):
                            IntroTour.mark_intro_completed()
                            st.rerun()

                with col_skip:
                    if st.button("Skip", use_container_width=True):
                        IntroTour.mark_intro_completed()
                        st.rerun()

                st.markdown("---")


def show_intro_in_sidebar():
    """Show intro management controls in sidebar (for testing/reset)."""
    with st.sidebar:
        with st.expander("ℹ️ Help & Info", expanded=False):
            st.caption("**Intro Tour**")

            if st.session_state.get(IntroTour.STATE_KEY, False):
                if st.button("🔄 Show Intro Again", use_container_width=True):
                    IntroTour.reset_intro()
                    st.rerun()
            else:
                st.info("Intro tour will display on next visit.")

            st.markdown("---")
            st.caption("📚 **Resources**")
            st.markdown("""
            - [GitHub Repository](https://github.com/GeoHaber/ZEN_RAG)
            - [Documentation](https://github.com/GeoHaber/ZEN_RAG#readme)
            - [Issues & Feedback](https://github.com/GeoHaber/ZEN_RAG/issues)
            """)
