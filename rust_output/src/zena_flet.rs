/// **DEPRECATED** — Use ``app::py`` instead.
/// 
/// zena_flet::py was the original Flet UI.  It has been superseded by app::py
/// which uses the shared UIBackend protocol and has full feature parity with
/// the NiceGUI frontend (zena.py).
/// 
/// To migrate, simply run::
/// 
/// python app::py               # or:  flet run app::py
/// 
/// This file is kept only for backward compatibility and will be removed in a
/// future release.

use anyhow::{Result, Context};
