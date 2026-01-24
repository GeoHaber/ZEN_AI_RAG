# Phase 2 Test Runner with Free API Keys
# Run this script after getting at least one FREE API key

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Phase 2: External LLM Testing with FREE API Keys" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Instructions
Write-Host "📝 Quick Setup (choose ONE or ALL):" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: Google Gemini (EASIEST - FREE forever)" -ForegroundColor Green
Write-Host "  1. Visit: https://aistudio.google.com/app/apikey"
Write-Host "  2. Sign in with Google (no credit card needed)"
Write-Host "  3. Click 'Create API Key'"
Write-Host "  4. Copy the key (starts with AIza...)"
Write-Host "  5. Paste below when prompted"
Write-Host ""
Write-Host "Option 2: Anthropic Claude (BEST - `$5 free credits)" -ForegroundColor Green
Write-Host "  1. Visit: https://console.anthropic.com/"
Write-Host "  2. Sign up (no card initially)"
Write-Host "  3. Get `$5 free credits"
Write-Host "  4. Copy API key from Settings"
Write-Host "  5. Paste below when prompted"
Write-Host ""
Write-Host "Option 3: Grok (GENEROUS - `$25 free credits)" -ForegroundColor Green
Write-Host "  1. Visit: https://x.ai/api"
Write-Host "  2. Sign up (may need X/Twitter account)"
Write-Host "  3. Get `$25 free credits"
Write-Host "  4. Copy API key"
Write-Host "  5. Paste below when prompted"
Write-Host ""
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host ""

# Prompt for API keys (optional - press Enter to skip)
Write-Host "Enter API keys (or press Enter to skip):" -ForegroundColor Cyan
Write-Host ""

# Google Gemini
$geminiKey = Read-Host "Google Gemini API Key (starts with AIza...)"
if ($geminiKey) {
    $env:GOOGLE_API_KEY = $geminiKey
    Write-Host "✅ Google Gemini key set" -ForegroundColor Green
}

# Anthropic Claude
$anthropicKey = Read-Host "Anthropic Claude API Key (starts with sk-ant-...)"
if ($anthropicKey) {
    $env:ANTHROPIC_API_KEY = $anthropicKey
    Write-Host "✅ Anthropic Claude key set" -ForegroundColor Green
}

# Grok
$grokKey = Read-Host "Grok API Key (starts with xai-...)"
if ($grokKey) {
    $env:XAI_API_KEY = $grokKey
    Write-Host "✅ Grok key set" -ForegroundColor Green
}

Write-Host ""

# Check if at least one key is set
$hasKey = $false
if ($env:GOOGLE_API_KEY) { $hasKey = $true }
if ($env:ANTHROPIC_API_KEY) { $hasKey = $true }
if ($env:XAI_API_KEY) { $hasKey = $true }

if (-not $hasKey) {
    Write-Host "❌ No API keys provided. Tests will be skipped." -ForegroundColor Red
    Write-Host ""
    Write-Host "To run Phase 2, you need at least ONE free API key:" -ForegroundColor Yellow
    Write-Host "• Google Gemini: https://aistudio.google.com/app/apikey (FREE forever)"
    Write-Host "• Anthropic: https://console.anthropic.com/ (`$5 free credits)"
    Write-Host "• Grok: https://x.ai/api (`$25 free credits)"
    Write-Host ""
    Write-Host "Re-run this script after getting a key!" -ForegroundColor Yellow
    exit
}

# Show which keys are set
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "API Keys Status:" -ForegroundColor Cyan
if ($env:GOOGLE_API_KEY) { Write-Host "  ✅ Google Gemini" -ForegroundColor Green } else { Write-Host "  ⊗ Google Gemini (not set)" -ForegroundColor DarkGray }
if ($env:ANTHROPIC_API_KEY) { Write-Host "  ✅ Anthropic Claude" -ForegroundColor Green } else { Write-Host "  ⊗ Anthropic Claude (not set)" -ForegroundColor DarkGray }
if ($env:XAI_API_KEY) { Write-Host "  ✅ Grok" -ForegroundColor Green } else { Write-Host "  ⊗ Grok (not set)" -ForegroundColor DarkGray }
Write-Host ""

# Run Phase 2 tests
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "🚀 Running Phase 2 Tests..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Expected cost: ~`$0.03 (from your FREE credits)" -ForegroundColor Yellow
Write-Host "Expected time: ~30 seconds" -ForegroundColor Yellow
Write-Host ""

# Change to project directory
Set-Location "C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli"

# Run tests
python -m pytest tests/test_external_llm_real.py -v --tb=short

# Check exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✅ Phase 2 Complete! All tests passed!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 External LLM integration is now fully tested and validated!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  • Review test output above"
    Write-Host "  • Check total cost (should be ~`$0.03)"
    Write-Host "  • Ready for production use!"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  ⚠️ Some tests failed or were skipped" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Cyan
    Write-Host "  • Check API keys are correct (no extra spaces)"
    Write-Host "  • Verify API keys are active (check provider console)"
    Write-Host "  • Check internet connection"
    Write-Host "  • See FREE_API_KEYS_GUIDE.md for troubleshooting"
    Write-Host ""
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
