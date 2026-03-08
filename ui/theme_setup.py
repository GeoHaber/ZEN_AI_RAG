from nicegui import ui


def setup_app_theme():
    """Configures the application theme, colors, and CSS."""
    # Theme & Layout (Zena Style - Light & Professional)
    ui.colors(primary="#3b82f6", secondary="#6c757d", accent="#17a2b8", dark=False)
    # Set light background
    ui.query("body").classes("bg-gray-50 dark:bg-slate-900")

    # CSS Fixes for Markdown Headers and Code Blocks in Chat
    ui.add_head_html("""
        <script>
            // Sync Quasar Dark Mode (body--dark) with Tailwind Dark Mode (dark class on html)
            function syncDarkMode() {
                const isDark = document.body.classList.contains('body--dark');
                console.log('Syncing dark mode:', isDark);
                if (isDark) {
                    document.documentElement.classList.add('dark');
                    document.documentElement.setAttribute('data-theme', 'dark');
                    // Force body styling for elements that check body directly
                    document.body.style.setProperty('--body-bg', '#0f172a');
                    document.body.style.setProperty('color-scheme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    document.documentElement.setAttribute('data-theme', 'light');
                    document.body.style.setProperty('--body-bg', '#f8fafc');
                    document.body.style.setProperty('color-scheme', 'light');
                }
            }
            
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        syncDarkMode();
                    }
                });
            });
            
            // Start observing immediately
            function startObserver() {
                observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
                syncDarkMode(); // Initial sync
            }
            
            // Run as soon as body is available
            if (document.body) {
                startObserver();
            } else {
                document.addEventListener('DOMContentLoaded', startObserver);
            }
            
            // Also check periodically for the first few seconds (handles NiceGUI async init)
            let checkCount = 0;
            const checkInterval = setInterval(() => {
                syncDarkMode();
                checkCount++;
                if (checkCount >= 10) clearInterval(checkInterval);
            }, 500);
        </script>
        
        <!-- MODERN SLATE THEME - GLOBAL STYLING -->
        <style>
            /* 1. TYPOGRAPHY & RESET */
            :root {
                --primary: #3b82f6;
                --slate-950: #0f172a;
                --slate-900: #0f172a; /* Deep Match */
                --slate-800: #1e293b;
                --slate-50: #f8fafc;
            }
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
                -webkit-font-smoothing: antialiased;
            }

            /* 2. GLOBAL THEME LAYERS */
            /* Light Mode Defaults */
            body, .q-page, .q-page-container, .nicegui-content {
                background-color: var(--slate-50) !important;
                color: #1e293b !important;
            }
            
            /* Dark Mode Defaults */
            .body--dark, .body--dark .q-page, .body--dark .q-page-container, .body--dark .nicegui-content {
                background-color: var(--slate-950) !important;
                color: #f1f5f9 !important;
            }

            /* 3. CARD & DIALOG STYLING (Glassmorphism Lite) */
            .q-card, .q-dialog .q-card {
                border-radius: 16px !important;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
            }
            /* Light Cards */
            .q-card { background-color: #ffffff !important; border: 1px solid #e2e8f0; }
            /* Dark Cards */
            .body--dark .q-card { 
                background-color: var(--slate-800) !important; 
                border: 1px solid #334155;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
            }

            /* 4. INPUTS & CONTROLS (The "Google" Look) */
            .q-field__control {
                border-radius: 10px !important; /* Rounded inputs */
                height: 48px !important;
            }
            .q-field__native, .q-input {
                padding-left: 4px;
            }
            
            /* Input Colors - Light */
            .q-field--outlined .q-field__control:before { border: 1px solid #cbd5e1; }
            .q-input__inner, .q-field__native { color: #1e293b !important; }
            
            /* Input Colors - Dark */
            .body--dark .q-field--outlined .q-field__control:before { border: 1px solid #475569; }
            .body--dark .q-input__inner, 
            .body--dark .q-field__native, 
            .body--dark .q-field__label, 
            .body--dark .q-select__dropdown-icon { 
                color: #f1f5f9 !important; 
            }
            .body--dark .q-field__control { background-color: #1e293b !important; }

            /* 5. MENUS & DROPDOWNS (Fixing "Invisible Text") */
            .q-menu {
                border-radius: 12px !important;
                padding: 4px;
            }
            /* Light Menu */
            .q-menu { background: #ffffff !important; color: #1e293b !important; border: 1px solid #e2e8f0; }
            .q-menu .q-item__label { color: #1e293b !important; }
            .q-menu .q-item { color: #1e293b !important; }
            /* Dark Menu */
            .body--dark .q-menu { 
                background: #1e293b !important; 
                color: #f1f5f9 !important; 
                border: 1px solid #334155; 
            }
            .body--dark .q-item { color: #f1f5f9 !important; }
            .body--dark .q-item__label { color: #f1f5f9 !important; }
            .body--dark .q-item--active { background: #334155 !important; color: #60a5fa !important; }
            
            /* Select Dropdown Popup */
            .q-select__dialog { background: #ffffff !important; }
            .body--dark .q-select__dialog { background: #1e293b !important; }
            .q-virtual-scroll__content .q-item { color: #1e293b !important; }
            .body--dark .q-virtual-scroll__content .q-item { color: #f1f5f9 !important; }

            /* 6. DRAWER STYLING */
            /* Light Drawer */
            .q-drawer { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
            /* Dark Drawer */
            .body--dark .q-drawer { 
                background-color: #0f172a !important; 
                border-right: 1px solid #1e293b; 
            }
            .body--dark .q-drawer__content { background-color: transparent !important; }

            /* 7. CHAT BUBBLES */
            /* User */
            .q-message-name { font-size: 0.75rem; opacity: 0.7; margin-bottom: 2px; }
            .q-message-text { 
                border-radius: 18px !important; 
                padding: 12px 18px !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
            .body--dark .q-message-text { border: 1px solid #334155; }
            .q-message-text h1 { font-size: 1.25rem; line-height: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; }
            .q-message-text h2 { font-size: 1.1rem; line-height: 1.4rem; font-weight: 600; margin-bottom: 0.5rem; margin-top: 1rem; }
            .q-message-text h3 { font-size: 1rem; line-height: 1.3rem; font-weight: 600; margin-bottom: 0.5rem; }
            .q-message-text pre { background-color: #f3f4f6; padding: 0.5rem; border-radius: 0.375rem; overflow-x: auto; }
            
            .body--dark .q-message-text pre { background-color: #0f172a; color: #e2e8f0; border: 1px solid #1e293b; }
            .body--dark .q-message-text code { background-color: rgba(255,255,255,0.1); color: #cbd5e1; }
            
            /* 8. BUTTONS */
            .q-btn { 
                border-radius: 8px !important; 
                font-weight: 600 !important; 
                text-transform: none !important; /* Proper Case */
            }
            /* System sidebar buttons - Light */
            .q-btn--flat.q-btn--align-left { 
                background: #f1f5f9 !important; 
                color: #1e293b !important; 
            }
            .q-btn--flat.q-btn--align-left:hover { 
                background: #e2e8f0 !important; 
            }
            /* System sidebar buttons - Dark */
            .body--dark .q-btn--flat.q-btn--align-left { 
                background: #1e293b !important; 
                color: #f1f5f9 !important; 
            }
            .body--dark .q-btn--flat.q-btn--align-left:hover { 
                background: #334155 !important; 
            }
            
            /* 9. SCROLLBARS */
            ::-webkit-scrollbar { width: 8px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
            .body--dark ::-webkit-scrollbar-thumb { background: #475569; }
            
            /* 10. PROGRESS BARS */
            .body--dark .q-linear-progress__track {
                background: rgba(255, 255, 255, 0.2) !important;
                opacity: 1 !important;
            }
            .body--dark .q-linear-progress__model {
                background: var(--q-primary) !important;
            }
            
            /* 11. LABELS & TEXT - Ensure visibility in both modes */
            .q-field__label { color: #64748b !important; } /* Light mode label */
            .body--dark .q-field__label { color: #94a3b8 !important; } /* Dark mode label */
            
            /* 12. EXPANSION PANELS */
            .q-expansion-item { color: #1e293b; background: #eff6ff !important; }
            .q-expansion-item__container { background: transparent !important; }
            .q-item__label { color: inherit !important; }
            .body--dark .q-expansion-item { color: #f1f5f9; background: #1e293b !important; }
            .body--dark .q-expansion-item .q-item__label { color: #f1f5f9 !important; }
            .body--dark .q-expansion-item .q-icon { color: #94a3b8 !important; }
            .body--dark .q-expansion-item__content { background: #0f172a !important; }
            
            /* 13. SWITCHES & TOGGLES */
            .q-toggle__label { color: #1e293b !important; }
            .body--dark .q-toggle__label { color: #f1f5f9 !important; }
            
            /* 14. GENERAL TEXT INHERITANCE */
            .body--dark label, 
            .body--dark .q-field__bottom,
            .body--dark .text-gray-600,
            .body--dark .text-gray-700,
            .body--dark .text-gray-800 { 
                color: #cbd5e1 !important; 
            }
            
            /* 15. TOOLTIP & NOTIFICATIONS */
            .q-tooltip { 
                background: #1e293b !important; 
                color: #f1f5f9 !important; 
            }
            
            /* 16. FIX: Tailwind dark: classes need body--dark context */
            .body--dark .dark\\:text-white { color: #ffffff !important; }
            .body--dark .dark\\:text-gray-100 { color: #f3f4f6 !important; }
            .body--dark .dark\\:text-gray-200 { color: #e5e7eb !important; }
            .body--dark .dark\\:text-gray-300 { color: #d1d5db !important; }
            .body--dark .dark\\:text-gray-400 { color: #9ca3af !important; }
            .body--dark .dark\\:text-slate-300 { color: #cbd5e1 !important; }
            .body--dark .dark\\:text-blue-400 { color: #60a5fa !important; }
            .body--dark .dark\\:bg-slate-800 { background-color: #1e293b !important; }
            .body--dark .dark\\:bg-slate-900 { background-color: #0f172a !important; }
            .body--dark .dark\\:bg-slate-950 { background-color: #020617 !important; }
            .body--dark .dark\\:border-slate-700 { border-color: #334155 !important; }
            .body--dark .dark\\:border-slate-800 { border-color: #1e293b !important; }
            .body--dark .dark\\:hover\\:bg-slate-700:hover { background-color: #334155 !important; }
            
            /* 17. CHAT MESSAGE BUBBLES - Specific dark mode fixes */
            .body--dark .bg-gray-100 { background-color: #1e293b !important; }
            .body--dark .text-gray-900 { color: #f1f5f9 !important; }
            
            /* 18. DIALOG STYLING */
            .q-dialog__backdrop { background: rgba(0, 0, 0, 0.5) !important; }
            .q-dialog .q-card { 
                max-height: 90vh; 
                overflow: auto;
            }
            /* Dialog dark mode */
            .body--dark .q-dialog .q-card {
                background-color: #1e293b !important;
                color: #f1f5f9 !important;
            }
            
            /* 19. SWITCH/TOGGLE DARK MODE */
            .body--dark .q-toggle { color: #f1f5f9 !important; }
            .body--dark .q-toggle__inner { color: #94a3b8 !important; }
            
            /* 20. STATUS TEXT */
            .body--dark .text-gray-600 { color: #94a3b8 !important; }
            .body--dark .text-gray-500 { color: #64748b !important; }
            
            /* 21. MODEL CATALOG CARDS */
            .model-card { transition: all 0.2s ease; }
            .model-card:hover { transform: translateY(-2px); }
            
            /* 22. COMPREHENSIVE DARK MODE OVERRIDES FOR TAILWIND CLASSES */
            /* Background colors that need dark mode conversion */
            .body--dark .bg-blue-50,
            .body--dark .bg-blue-100 { 
                background-color: rgba(59, 130, 246, 0.15) !important; 
            }
            .body--dark .bg-gray-50,
            .body--dark .bg-gray-100 { 
                background-color: #1e293b !important; 
            }
            .body--dark .bg-white {
                background-color: #0f172a !important;
            }
            
            /* Text colors for dark mode */
            .body--dark .text-blue-700 { color: #93c5fd !important; }
            .body--dark .text-blue-600 { color: #60a5fa !important; }
            .body--dark .text-blue-500 { color: #3b82f6 !important; }
            .body--dark .text-green-600 { color: #86efac !important; }
            .body--dark .text-green-500 { color: #22c55e !important; }
            .body--dark .text-red-600 { color: #fca5a5 !important; }
            .body--dark .text-red-500 { color: #ef4444 !important; }
            .body--dark .text-purple-600 { color: #c4b5fd !important; }
            .body--dark .text-orange-600 { color: #fdba74 !important; }
            .body--dark .text-yellow-600 { color: #fde047 !important; }
            
            /* Hover states for dark mode */
            .body--dark .hover\\:bg-gray-100:hover,
            .body--dark .hover\\:bg-gray-50:hover {
                background-color: #334155 !important;
            }
            .body--dark .hover\\:bg-blue-100:hover {
                background-color: rgba(59, 130, 246, 0.25) !important;
            }
            
            /* Border colors for dark mode */
            .body--dark .border-gray-200 { border-color: #334155 !important; }
            .body--dark .border-gray-300 { border-color: #475569 !important; }
            .body--dark .border-blue-500 { border-color: #3b82f6 !important; }
            
            /* Ensure all q-card elements get dark background */
            .body--dark .q-card {
                background-color: #1e293b !important;
                color: #f1f5f9 !important;
            }
            
            /* Main page container */
            .body--dark .q-page-container,
            .body--dark .q-page {
                background-color: #0f172a !important;
            }
            
            /* 23. FULL HEIGHT CHAT LAYOUT (Like LM Studio / Ollama) */
            .q-page-container {
                display: flex !important;
                flex-direction: column !important;
                height: 100vh !important;
                overflow: hidden !important;
            }
            .q-page {
                display: flex !important;
                flex-direction: column !important;
                flex: 1 !important;
                overflow: hidden !important;
                min-height: 0 !important;
            }
            /* Chat scroll container fills remaining space */
            .chat-scroll-area {
                flex: 1 !important;
                overflow-y: auto !important;
                overflow-x: hidden !important;
                scroll-behavior: smooth;
            }
            /* Compact header */
            .q-header {
                flex-shrink: 0 !important;
            }
            /* Compact footer with input */
            .q-footer {
                flex-shrink: 0 !important;
                max-height: 120px !important;
            }
            
            /* 24. MAXIMIZED DIALOG */
            .q-dialog__inner--maximized > div {
                max-width: 1200px !important;
                margin: 0 auto;
            }
        </style>
    """)
