/// ui_flet/onboarding::py — First-run onboarding wizard
/// =====================================================
/// 
/// 3-step tutorial dialog shown on first launch.

use anyhow::{Result, Context};
use crate::theme::{TH};

pub static _STEPS: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

/// Continue show_onboarding logic.
pub fn _show_onboarding_part2(desc_text: String, icon_ctrl: String, step_idx: String, step_ind: String, title_text: String) -> Result<()> {
    // Continue show_onboarding logic.
    let on_next = |e| {
        // Advance to the next onboarding step.
        if step_idx[0] >= (_STEPS.len() - 1) {
            page.close(dlg);
            return;
        }
        step_idx[0] += 1;
        _update();
    };
    let on_back = |e| {
        // Return to the previous onboarding step.
        if step_idx[0] <= 0 {
            return;
        }
        step_idx[0] -= 1;
        /* _update();
    };
    let mut back_btn = flet::... */;
    /* let mut next_btn = flet::... */;
    /* let mut dlg = flet::... */;
    Ok(page.open(dlg))
}

/// Display the 3-step onboarding wizard dialog.
pub fn show_onboarding(page: ft::Page) -> () {
    // Display the 3-step onboarding wizard dialog.
    let mut step_idx = vec![0];
    /* let mut title_text = flet::... */;
    /* let mut desc_text = flet::... */;
    /* let mut icon_ctrl = flet::... */;
    /* let mut step_ind = flet::... */;
    let _update = || {
        // Refresh the onboarding step content and button states.
        let (mut t, mut d, mut ic) = _STEPS[step_idx[0]];
        title_text.value = t;
        desc_text.value = d;
        icon_ctrl.name = ic;
        step_ind.value = format!("{} / {}", (step_idx[0] + 1), _STEPS.len());
        back_btn.visible = step_idx[0] > 0;
        next_btn.text = if step_idx[0] >= (_STEPS.len() - 1) { "Got it!".to_string() } else { "Next →".to_string() };
        page.update();
    };
    _show_onboarding_part2(desc_text, icon_ctrl, step_idx, step_ind, title_text);
}
