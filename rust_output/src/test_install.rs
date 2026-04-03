use anyhow::{Result, Context};
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

/// TestDistribution class.
#[derive(Debug, Clone)]
pub struct TestDistribution {
}

impl TestDistribution {
    /// Setup.
    pub fn setUp(&mut self) -> () {
        // Setup.
        self.project_root = PathBuf::from(std::env::current_dir().unwrap().to_str().unwrap().to_string());
        self.dist_path = ((self.project_root / "dist".to_string()) / "ZenAI_Dist.zip".to_string());
        if !self.dist_path.exists() {
            self.fail(format!("Distribution ZIP not found at {}", self.dist_path));
        }
        self.sandbox = (self.project_root / "sandbox_test".to_string());
        if self.sandbox.exists() {
            std::fs::remove_dir_all(self.sandbox).ok();
        }
        self.sandbox.create_dir_all();
    }
    /// Teardown.
    pub fn tearDown(&self) -> Result<()> {
        // Teardown.
        if self.sandbox.exists() {
            // try:
            {
                std::fs::remove_dir_all(self.sandbox).ok();
            }
            // except PermissionError as _e:
        }
    }
    /// Unpack logic and verify file structure.
    pub fn test_installation_layout(&mut self) -> Result<()> {
        // Unpack logic and verify file structure.
        println!("\n📦 Unpacking {}...", self.dist_path.file_name().unwrap_or_default().to_str().unwrap_or(""));
        // try:
        {
            let mut zip_ref = zipfile.ZipFile(self.dist_path, "r".to_string());
            {
                zip_ref.extractall(self.sandbox);
            }
        }
        // except Exception as e:
        println!("{}", "✅ Unpack success.".to_string());
        let mut critical_files = vec!["zena.py".to_string(), "requirements.txt".to_string(), "USER_MANUAL.md".to_string(), "ui_components.py".to_string(), "ui/locales/en::py".to_string()];
        let mut missing = vec![];
        for f in critical_files.iter() {
            let mut p = (self.sandbox / f);
            if !p.exists() {
                missing.push(f);
            }
        }
        assert!(!missing, format!("Missing critical files in distribution: {}", missing));
        println!("{}", "✅ Critical files verified.".to_string());
        let mut garbage_signatures = vec![".venv".to_string(), "node_modules".to_string(), ".git".to_string(), "__pycache__".to_string()];
        let mut found_garbage = vec![];
        for (root, dirs, files) in os::walk(self.sandbox).iter() {
            for d in dirs.iter() {
                if garbage_signatures.contains(&d) {
                    found_garbage.push(d);
                }
            }
        }
        assert!(!found_garbage, format!("Distribution contains garbage directories: {}", found_garbage));
        Ok(println!("{}", "✅ Cleanliness verified.".to_string()))
    }
    /// Simulate running 'python zena.py' (dry run).
    pub fn test_startup_simulation(&mut self) -> Result<()> {
        // Simulate running 'python zena.py' (dry run).
        let mut zip_ref = zipfile.ZipFile(self.dist_path, "r".to_string());
        {
            zip_ref.extractall(self.sandbox);
        }
        println!("{}", "🚀 Simulating Startup Check...".to_string());
        let mut checker_script = "\nimport sys\nimport os\ntry:\n    # Add CWD to path implicit\n    import zena\n    import config_system\n    import utils\n    print(\"IMPORT_SUCCESS\")\nexcept ImportError as e:\n    print(f\"IMPORT_ERROR: {e}\")\n    std::process::exit(1)\nexcept Exception as e:\n    # nicegui might fail to install, we catch that\n    print(f\"RUNTIME_ERROR: {e}\")\n".to_string();
        let mut check_file = (self.sandbox / "check_install.py".to_string());
        check_filestd::fs::write(&checker_script);
        let mut result = std::process::Command::new("sh").arg("-c").arg(vec![sys::executable, "check_install.py".to_string().output().unwrap()], /* cwd= */ self.sandbox, /* capture_output= */ true, /* text= */ true, /* shell= */ false);
        println!("Output: {}", result.stdout);
        println!("Stderr: {}", result.stderr);
        if (result.stderr.to_lowercase().contains(&"nicegui".to_string()) && result.stderr.to_lowercase().contains(&"install".to_string())) {
            // pass
        }
        assert!((result.stdout + result.stderr), "Failed to import core modules in sandbox".to_string().contains("IMPORT_SUCCESS".to_string()));
        Ok(println!("{}", "✅ Startup Simulation Passed (Imports Working)".to_string()))
    }
}
