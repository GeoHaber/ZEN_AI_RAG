<##>
# run_all_tests.ps1 - Run all tests and log output automatically
# Usage: Run this script in PowerShell to execute all tests and save results to test_results.txt

$logFile = "results_log.txt"
Write-Host "Running all tests and logging output to $logFile ..."
pytest -v 2>&1 | Tee-Object -FilePath $logFile
Write-Host "Test run complete. Results saved to $logFile."