/* /// Gateways panel — Telegram / WhatsApp bot toggles.

use anyhow::{Result, Context};
use crate::theme::{TH};

/// Panel for starting/stopping Telegram & WhatsApp gateways.
pub fn build_gateways_panel(page: ft::Page, state: String, backend: String) -> Result<ft::Container> {
    // Panel for starting/stopping Telegram & WhatsApp gateways.
    let mut tg_status = flet::... */;
    /* let mut wa_status = flet::... */;
    /* let mut log_view = flet::... */;
    let _log = |msg| {
        log_view.controls.push(/* flet::Text */(msg, /* size= */ 11, /* color= */ TH.dim));
        if log_view.controls.len() > 200 {
            log_view.controls = log_view.controls[-100..];
        }
        page.update();
    };
    let _toggle_telegram = |e| {
        let mut enabled = e.control.value;
        if /* hasattr(state, "telegram_enabled".to_string()) */ true {
            state::telegram_enabled = enabled;
        }
        if enabled {
            tg_status.value = "Starting…".to_string();
            tg_status.color = TH.accent;
            page.update();
            // try:
            {
                if (backend && /* hasattr(backend, "start_gateways".to_string()) */ true) {
                    backend.start_gateways(/* telegram= */ true, /* whatsapp= */ false).await;
                }
                tg_status.value = "Running".to_string();
                _log("Telegram gateway started".to_string());
            }
            // except Exception as exc:
        } else {
            tg_status.value = "Stopped".to_string();
            tg_status.color = TH.dim;
            _log("Telegram gateway stopped".to_string());
        }
        page.update();
    };
    let _toggle_whatsapp = |e| {
        let mut enabled = e.control.value;
        if /* hasattr(state, "whatsapp_enabled".to_string()) */ true {
            state::whatsapp_enabled = enabled;
        }
        if enabled {
            wa_status.value = "Starting…".to_string();
            wa_status.color = TH.accent;
            page.update();
            // try:
            {
                if (backend && /* hasattr(backend, "start_gateways".to_string()) */ true) {
                    backend.start_gateways(/* telegram= */ false, /* whatsapp= */ true).await;
                }
                wa_status.value = "Running".to_string();
                _log("WhatsApp gateway started".to_string());
            }
            // except Exception as exc:
        } else {
            wa_status.value = "Stopped".to_string();
            wa_status.color = TH.dim;
            /* _log("WhatsApp gateway stopped".to_string());
        }
        page.update();
    };
    let mut tg_switch = flet::... */;
    /* let mut wa_switch = flet::... */;
    Ok(/* flet::Container */(/* content= */ /* flet::Column */(vec![/* flet::Text */("Gateways".to_string(), /* size= */ 16, /* weight= */ /* flet::FontWeight.W_600 */, /* color= */ TH.text), /* flet::Text */("Connect Zena to messaging platforms.".to_string(), /* size= */ 12, /* color= */ TH.dim), /* flet::Container */(/* height= */ 12), /* flet::Row */(vec![tg_switch, tg_status], /* spacing= */ 12), /* flet::Row */(vec![wa_switch, wa_status], /* spacing= */ 12), /* flet::Divider */(/* color= */ TH.divider, /* height= */ 16), /* flet::Text */("Gateway Log".to_string(), /* size= */ 13, /* weight= */ /* flet::FontWeight.W_500 */, /* color= */ TH.text), log_view], /* expand= */ true, /* spacing= */ 8), /* expand= */ true, /* padding= */ 20))
}
