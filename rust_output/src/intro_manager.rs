/// Intro/Tour Manager for ZEN_RAG
/// Shows an interactive first-run experience explaining app capabilities.

use anyhow::{Result, Context};

/// Manages the intro/onboarding tour for new users.
#[derive(Debug, Clone)]
pub struct IntroTour {
}

impl IntroTour {
    /// Check if intro should be shown.
    pub fn should_show_intro() -> bool {
        // Check if intro should be shown.
        !streamlit.session_state.get(&IntroTour.STATE_KEY).cloned().unwrap_or(false)
    }
    /// Mark intro as completed.
    pub fn mark_intro_completed() -> () {
        // Mark intro as completed.
        streamlit.session_state[IntroTour.STATE_KEY] = true;
    }
    /// Reset intro (for testing or user request).
    pub fn reset_intro() -> () {
        // Reset intro (for testing or user request).
        streamlit.session_state[IntroTour.STATE_KEY] = false;
        streamlit.session_state[IntroTour.SLIDE_KEY] = 0;
    }
    /// Display the intro tour as a modal overlay.
    pub fn show_intro_modal() -> () {
        // Display the intro tour as a modal overlay.
        if !IntroTour.should_show_intro() {
            return;
        }
        if !streamlit.session_state.contains(&IntroTour.SLIDE_KEY) {
            streamlit.session_state[IntroTour.SLIDE_KEY] = 0;
        }
        let mut current_slide = streamlit.session_state[&IntroTour.SLIDE_KEY];
        let mut slide = IntroTour.SLIDES[&current_slide];
        let _ctx = streamlit.container();
        {
            let (mut col1, mut col2, mut col3) = streamlit.columns(vec![1, 10, 1]);
            let _ctx = col2;
            {
                streamlit.markdown("---".to_string());
                streamlit.markdown(format!("<h1 style='text-align: center'>{}</h1>", slide["icon".to_string()]), /* unsafe_allow_html= */ true);
                streamlit.markdown(format!("<h2 style='text-align: center'>{}</h2>", slide["title".to_string()]), /* unsafe_allow_html= */ true);
                streamlit.markdown(format!("<h3 style='text-align: center; color: gray'>{}</h3>", slide["subtitle".to_string()]), /* unsafe_allow_html= */ true);
                streamlit.markdown("---".to_string());
                streamlit.markdown(slide["content".to_string()]);
                streamlit.markdown("---".to_string());
                let (mut col_prev, mut col_counter, mut col_next, mut col_skip) = streamlit.columns(4);
                let _ctx = col_prev;
                {
                    if current_slide > 0 {
                        if streamlit.button("← Previous".to_string(), /* use_container_width= */ true) {
                            streamlit.session_state[IntroTour.SLIDE_KEY] -= 1;
                            streamlit.rerun();
                        }
                    } else {
                        streamlit.button("← Previous".to_string(), /* use_container_width= */ true, /* disabled= */ true);
                    }
                }
                let _ctx = col_counter;
                {
                    streamlit.markdown(format!("<div style='text-align: center; padding-top: 10px'><strong>{} / {}</strong></div>", (current_slide + 1), IntroTour.SLIDES.len()), /* unsafe_allow_html= */ true);
                }
                let _ctx = col_next;
                {
                    if current_slide < (IntroTour.SLIDES.len() - 1) {
                        if streamlit.button("Next →".to_string(), /* use_container_width= */ true) {
                            streamlit.session_state[IntroTour.SLIDE_KEY] += 1;
                            streamlit.rerun();
                        }
                    } else if streamlit.button("Finish 🎉".to_string(), /* use_container_width= */ true, /* help= */ "Complete the tour and start using ZEN_RAG".to_string()) {
                        IntroTour.mark_intro_completed();
                        streamlit.rerun();
                    }
                }
                let _ctx = col_skip;
                {
                    if streamlit.button("Skip".to_string(), /* use_container_width= */ true) {
                        IntroTour.mark_intro_completed();
                        streamlit.rerun();
                    }
                }
                streamlit.markdown("---".to_string());
            }
        }
    }
}

/// Show intro management controls in sidebar (for testing/reset).
pub fn show_intro_in_sidebar() -> () {
    // Show intro management controls in sidebar (for testing/reset).
    let _ctx = streamlit.sidebar;
    {
        let _ctx = streamlit.expander("ℹ️ Help & Info".to_string(), /* expanded= */ false);
        {
            streamlit.caption("**Intro Tour**".to_string());
            if streamlit.session_state.get(&IntroTour.STATE_KEY).cloned().unwrap_or(false) {
                if streamlit.button("🔄 Show Intro Again".to_string(), /* use_container_width= */ true) {
                    IntroTour.reset_intro();
                    streamlit.rerun();
                }
            } else {
                streamlit.info("Intro tour will display on next visit.".to_string());
            }
            streamlit.markdown("---".to_string());
            streamlit.caption("📚 **Resources**".to_string());
            streamlit.markdown("\n            - [GitHub Repository](https://github.com/GeoHaber/ZEN_RAG)\n            - [Documentation](https://github.com/GeoHaber/ZEN_RAG#readme)\n            - [Issues & Feedback](https://github.com/GeoHaber/ZEN_RAG/issues)\n            ".to_string());
        }
    }
}
