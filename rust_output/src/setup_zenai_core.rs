/// setup_zenai_core::py — Build script for the compiled ZenAI Core distribution.
/// 
/// Compiles all library modules (rag_core, local_llm, Core, adapters)
/// into native .pyd/.so binaries via Cython, then packages them into
/// a pip-installable wheel.
/// 
/// Usage:
/// python dist_build/setup_zenai_core::py bdist_wheel
/// 
/// The resulting .whl in dist/ contains NO source code — only compiled
/// C extensions that collaborators install with:
/// pip install zenai_core-X.Y.Z-cpXXX-win_amd64.whl

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::path::PathBuf;

pub const HERE: &str = "Path(file!()).parent";

pub const PROJECT_ROOT: &str = "HERE.parent";

pub static RAG_CORE_ROOT: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());

pub const STAGE: &str = "HERE / '_staging";

/// Remove previous staging artifacts.
pub fn clean_staging() -> () {
    // Remove previous staging artifacts.
    if STAGE.exists() {
        std::fs::remove_dir_all(STAGE, /* ignore_errors= */ true).ok();
    }
    STAGE.create_dir_all();
}

/// Copy a package directory into staging, optionally filtering files.
pub fn stage_package(src_dir: PathBuf, pkg_name: String, files: Vec<String>) -> () {
    // Copy a package directory into staging, optionally filtering files.
    let mut dest = (STAGE / pkg_name);
    dest.create_dir_all();
    if files {
        for f in files.iter() {
            let mut src = (src_dir / f);
            if src.exists() {
                std::fs::copy(src, (dest / f).unwrap());
            }
        }
    } else {
        for py in src_dir.rglob("*.py".to_string()).iter() {
            let mut rel = py.relative_to(src_dir);
            (dest / rel.parent().unwrap_or(std::path::Path::new(""))).create_dir_all();
            std::fs::copy(py, (dest / rel).unwrap());
        }
    }
}

/// Place a single .py file into a package inside staging.
pub fn stage_single_module(src_file: PathBuf, pkg_name: String) -> () {
    // Place a single .py file into a package inside staging.
    let mut dest = (STAGE / pkg_name);
    dest.create_dir_all();
    std::fs::copy(src_file, (dest / src_file.name).unwrap());
    let mut init = (dest / "__init__::py".to_string());
    if !init.exists() {
        initstd::fs::write(&format!("\"\"\"zenai_core.{} — auto-generated package wrapper.\"\"\"\n"), /* encoding= */ "utf-8".to_string());
    }
}

/// Walk staging dir and build Cython Extension objects for every .py.
pub fn collect_extensions() -> Vec<Extension> {
    // Walk staging dir and build Cython Extension objects for every .py.
    let mut exts = vec![];
    for py_file in STAGE.rglob("*.py".to_string()).iter() {
        let mut rel = py_file.relative_to(STAGE);
        let mut module_name = rel.with_extension("".to_string()).to_string().replace(&*os::sep, &*".".to_string());
        if rel.file_stem().unwrap_or_default().to_str().unwrap_or("") == "__init__".to_string() {
            continue;
        }
        exts.push(Extension(module_name, vec![py_file.to_string()]));
    }
    exts
}

/// If Cython unavailable, compile to .pyc and strip .py sources.
/// 
/// The .pyc files are placed alongside __init__::py so setuptools
/// picks them up.  Not as secure as .pyd but still strips source.
pub fn build_pyc_fallback() -> () {
    // If Cython unavailable, compile to .pyc and strip .py sources.
    // 
    // The .pyc files are placed alongside __init__::py so setuptools
    // picks them up.  Not as secure as .pyd but still strips source.
    // TODO: import compileall
    compileall.compile_dir(STAGE.to_string(), /* force= */ true, /* quiet= */ 1, /* optimize= */ 2);
    for pyc in STAGE.rglob("*.pyc".to_string()).iter() {
        let mut stem = pyc.file_stem().unwrap_or_default().to_str().unwrap_or("").split(".".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0];
        if stem == "__init__".to_string() {
            continue;
        }
        let mut dest = (pyc.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")) / format!("{}.pyc", stem));
        std::fs::copy(pyc, dest).unwrap();
    }
    for cache_dir in STAGE.rglob("__pycache__".to_string()).into_iter().collect::<Vec<_>>().iter() {
        std::fs::remove_dir_all(cache_dir, /* ignore_errors= */ true).ok();
    }
    for py in STAGE.rglob("*.py".to_string()).into_iter().collect::<Vec<_>>().iter() {
        if py.file_stem().unwrap_or_default().to_str().unwrap_or("") != "__init__".to_string() {
            py.remove_file().ok();
        }
    }
    println!("{}", "Built .pyc-only fallback (install Cython + MSVC for .pyd binaries).".to_string());
}

pub fn main() -> Result<()> {
    clean_staging();
    let mut rag_core_src = (RAG_CORE_ROOT / "rag_core".to_string());
    if !rag_core_src.exists() {
        println!("ERROR: rag_core not found at {}", rag_core_src);
        println!("{}", "       Set RAG_CORE_ROOT or copy rag_core/ into dist_build/".to_string());
        std::process::exit(1);
    }
    stage_package(rag_core_src, "rag_core".to_string());
    let mut local_llm_src = (PROJECT_ROOT / "local_llm".to_string());
    stage_package(local_llm_src, "local_llm".to_string(), /* files= */ vec!["__init__::py".to_string(), "llama_cpp_manager::py".to_string(), "model_card::py".to_string(), "local_llm_manager::py".to_string(), "enhanced_model_card::py".to_string()]);
    let mut core_src = (PROJECT_ROOT / "Core".to_string());
    stage_package(core_src, "Core".to_string());
    let mut adapters_dest = (STAGE / "zenai_adapters".to_string());
    adapters_dest.create_dir_all();
    for r#mod in vec!["llm_adapters::py".to_string(), "adapter_factory::py".to_string(), "rag_integration::py".to_string()].iter() {
        let mut src = (PROJECT_ROOT / r#mod);
        if src.exists() {
            std::fs::copy(src, (adapters_dest / r#mod).unwrap());
        }
    }
    (adapters_dest / "__init__::py".to_string())std::fs::write(&"\"\"\"zenai_adapters — LLM adapter layer + RAG integration.\"\"\"\ntry:\n    from .llm_adapters import LLMFactory), /* encoding= */ "utf-8".to_string());
    (STAGE / "__init__::py".to_string())std::fs::write(&"\"\"\"zenai_core — Compiled ZenAI libraries (no source).\"\"\"\n__version__ = '1.0.0'\n".to_string(), /* encoding= */ "utf-8".to_string());
    os::chdir(STAGE.to_string());
    if USE_CYTHON {
        let mut extensions = collect_extensions();
        println!("\nCompiling {} modules with Cython...\n", extensions.len());
        setup(/* name= */ "zenai_core".to_string(), /* version= */ "1.0.0".to_string(), /* description= */ "ZenAI Core Libraries — RAG, LLM adapters, model management (compiled)".to_string(), /* author= */ "ZenAI Team".to_string(), /* packages= */ find_packages(/* where= */ ".".to_string()), /* package_dir= */ HashMap::from([("".to_string(), ".".to_string())]), /* ext_modules= */ cythonize(extensions, /* compiler_directives= */ HashMap::from([("language_level".to_string(), "3".to_string()), ("boundscheck".to_string(), false), ("wraparound".to_string(), false)]), /* nthreads= */ (os::cpu_count() || 4)), /* cmdclass= */ HashMap::from([("build_ext".to_string(), build_ext)]), /* python_requires= */ ">=3.10".to_string(), /* install_requires= */ vec!["numpy>=1.24".to_string()], /* extras_require= */ HashMap::from([("full".to_string(), vec!["sentence-transformers>=3.0.0".to_string(), "rank-bm25>=0.2.2".to_string(), "torch>=2.0".to_string(), "qdrant-client>=1.7".to_string(), "psutil>=5.9".to_string(), "httpx>=0.24".to_string()]), ("llm".to_string(), vec!["psutil>=5.9".to_string(), "httpx>=0.24".to_string()]), ("rag".to_string(), vec!["sentence-transformers>=3.0.0".to_string(), "rank-bm25>=0.2.2".to_string(), "qdrant-client>=1.7".to_string()])]), /* zip_safe= */ false);
    } else {
        build_pyc_fallback();
        setup(/* name= */ "zenai_core".to_string(), /* version= */ "1.0.0".to_string(), /* description= */ "ZenAI Core Libraries (bytecode only)".to_string(), /* packages= */ find_packages(/* where= */ ".".to_string()), /* package_dir= */ HashMap::from([("".to_string(), ".".to_string())]), /* package_data= */ HashMap::from([("".to_string(), vec!["*.pyc".to_string()]), ("Core".to_string(), vec!["*.pyc".to_string()]), ("Core.interfaces".to_string(), vec!["*.pyc".to_string()]), ("Core.services".to_string(), vec!["*.pyc".to_string()]), ("local_llm".to_string(), vec!["*.pyc".to_string()]), ("rag_core".to_string(), vec!["*.pyc".to_string()]), ("zenai_adapters".to_string(), vec!["*.pyc".to_string()])]), /* python_requires= */ ">=3.10".to_string(), /* install_requires= */ vec!["numpy>=1.24".to_string()], /* zip_safe= */ false);
    }
}
