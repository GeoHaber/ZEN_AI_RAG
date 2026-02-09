# Cleanup and reorganize ZEN_AI_RAG workspace
# - Deletes __pycache__ directories
# - Creates directory structure: docs/, tests/, scripts/, OLD/
# - Moves files to appropriate locations

$root = Get-Location
$ErrorActionPreference = "SilentlyContinue"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "ZEN_AI_RAG WORKSPACE CLEANUP" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Delete __pycache__ directories recursively
Write-Host "[1/6] Removing __pycache__ directories..." -ForegroundColor Yellow
$pycache_dirs = Get-ChildItem -Path $root -Directory -Name "__pycache__" -Recurse
if ($pycache_dirs) {
    $count = ($pycache_dirs | Measure-Object).Count
    $pycache_dirs | ForEach-Object {
        Remove-Item -Path (Join-Path $root $_) -Recurse -Force
    }
    Write-Host "      OK: Deleted $count __pycache__ directories" -ForegroundColor Green
} else {
    Write-Host "      OK: No __pycache__ directories found" -ForegroundColor Cyan
}
Write-Host ""

# Step 2: Create directory structure
Write-Host "[2/6] Creating directory structure..." -ForegroundColor Yellow
$dirs = @("docs", "tests", "scripts", "OLD")
foreach ($dir in $dirs) {
    $path = Join-Path $root $dir
    if (!(Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "      OK: Created $dir/" -ForegroundColor Green
    } else {
        Write-Host "      OK: $dir/ already exists" -ForegroundColor Cyan
    }
}
Write-Host ""

# Step 3: Move Markdown documentation files to docs/
Write-Host "[3/6] Moving documentation files to docs/..." -ForegroundColor Yellow
$docs_moved = 0

# Markdown files
Get-ChildItem -Path $root -MaxDepth 1 -Name "*.md" | ForEach-Object {
    Move-Item -Path (Join-Path $root $_) -Destination (Join-Path $root "docs" $_) -Force
    $docs_moved++
}

# Log and text files
Get-ChildItem -Path $root -MaxDepth 1 -Name "*.txt" | ForEach-Object {
    Move-Item -Path (Join-Path $root $_) -Destination (Join-Path $root "docs" $_) -Force
    $docs_moved++
}

Get-ChildItem -Path $root -MaxDepth 1 -Name "*.log" | ForEach-Object {
    Move-Item -Path (Join-Path $root $_) -Destination (Join-Path $root "docs" $_) -Force
    $docs_moved++
}

Write-Host "      OK: Moved $docs_moved documentation files" -ForegroundColor Green
Write-Host ""

# Step 4: Move test files to tests/
Write-Host "[4/6] Moving test files to tests/..." -ForegroundColor Yellow
$tests_moved = 0

# Test scripts
$test_patterns = @("test_*.py", "run_*.py", "verify*.py", "pytest.ini")
foreach ($pattern in $test_patterns) {
    Get-ChildItem -Path $root -MaxDepth 1 -Name $pattern | ForEach-Object {
        $dest = Join-Path $root "tests" $_
        if (!(Test-Path $dest)) {
            Move-Item -Path (Join-Path $root $_) -Destination $dest -Force
            $tests_moved++
        }
    }
}

# PowerShell test runners
Get-ChildItem -Path $root -MaxDepth 1 -Name "run_*.ps1" | ForEach-Object {
    Move-Item -Path (Join-Path $root $_) -Destination (Join-Path $root "tests" $_) -Force
    $tests_moved++
}

Write-Host "      OK: Moved $tests_moved test files" -ForegroundColor Green
Write-Host ""

# Step 5: Move setup/utility scripts to scripts/
Write-Host "[5/6] Moving setup scripts to scripts/..." -ForegroundColor Yellow
$scripts_moved = 0

$script_patterns = @("install.py", "cleanup*.py", "startup_check.py", "feature_detection.py", "reproduce_*.py")
foreach ($pattern in $script_patterns) {
    Get-ChildItem -Path $root -MaxDepth 1 -Name $pattern | ForEach-Object {
        Move-Item -Path (Join-Path $root $_) -Destination (Join-Path $root "scripts" $_) -Force
        $scripts_moved++
    }
}

Write-Host "      OK: Moved $scripts_moved setup scripts" -ForegroundColor Green
Write-Host ""

# Step 6: Move non-essential files to OLD/
Write-Host "[6/6] Moving non-essential files to OLD/..." -ForegroundColor Yellow

$essential_files = @(
    "zena.py", "start_llm.py", "config.py", "config_system.py", "settings.py",
    "voice_service.py", "model_manager.py", "utils.py", "security.py", 
    "state_management.py", "decorators.py",
    "async_backend.py", "intelligent_router.py", "mock_backend.py",
    "mini_rag.py", "rag_inspector.py", "semantic_cache.py",
    "cleanup_workspace.ps1",
    "start_zenAI.bat", "debug_start.bat", "debug_console.bat", "capture_crash.bat",
    "pytest.ini", "config.json", "settings.json", ".env.example",
    "requirements.txt", "README.md", "LICENSE", ".gitignore"
)

$old_moved = 0

Get-ChildItem -Path $root -MaxDepth 1 -File | ForEach-Object {
    $filename = $_.Name
    
    # Skip files already moved
    if ((Test-Path (Join-Path $root "docs" $filename)) -or 
        (Test-Path (Join-Path $root "tests" $filename)) -or
        (Test-Path (Join-Path $root "scripts" $filename))) {
        return
    }
    
    # Skip essential files
    if ($essential_files -contains $filename) {
        return
    }
    
    # Skip hidden/config files
    if ($filename.StartsWith(".")) {
        return
    }
    
    # Move to OLD
    try {
        Move-Item -Path (Join-Path $root $filename) -Destination (Join-Path $root "OLD" $filename) -Force
        $old_moved++
    } catch {
        # Silently skip
    }
}

# Move legacy directories
$legacy_dirs = @("_sandbox", "_Extra_files", "_legacy_audit", "_docs", "_static", "_zena_analisis", "build", "dist")
foreach ($dir in $legacy_dirs) {
    $src = Join-Path $root $dir
    if ((Test-Path $src) -and ((Get-Item $src).PSIsContainer)) {
        try {
            Move-Item -Path $src -Destination (Join-Path $root "OLD" (Split-Path $src -Leaf)) -Force
            $old_moved++
        } catch {
            # Silently continue
        }
    }
}

Write-Host "      OK: Moved $old_moved non-essential items" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "CLEANUP COMPLETE" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$root_files = (Get-ChildItem -Path $root -MaxDepth 1 -File | Measure-Object).Count
$root_dirs = (Get-ChildItem -Path $root -MaxDepth 1 -Directory | Measure-Object).Count

Write-Host "Current workspace state:" -ForegroundColor Yellow
Write-Host "  Root level files: $root_files" -ForegroundColor Cyan
Write-Host "  Root level directories: $root_dirs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  docs/       - Documentation and logs" -ForegroundColor Cyan
Write-Host "  tests/      - Test scripts and runners" -ForegroundColor Cyan
Write-Host "  scripts/    - Setup and utility scripts" -ForegroundColor Cyan
Write-Host "  OLD/        - Legacy and non-essential files" -ForegroundColor Cyan
Write-Host ""
Write-Host "A clean house is a healthy house!" -ForegroundColor Green
Write-Host ""
