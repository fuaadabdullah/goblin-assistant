use std::env;
use std::fs;
use std::path::{Path, PathBuf};

/// Try to locate `goblins.yaml` starting from the current working directory
/// and walking up parent directories. If an explicit `GOBLINOS_CONFIG` env var
/// is set, prefer that path. This avoids hard-coded repo paths and makes the
/// desktop app work relative to the active project root.
pub fn find_goblins_config() -> Result<PathBuf, String> {
    // If the demo indicates a project root explicitly, prefer that over
    // any monorepo-level or legacy GOBLINOS_CONFIG value. This makes the
    // desktop demo more portable and works well for `goblin-assistant` style
    // single-project demos.
    if let Ok(root) = env::var("GOBLIN_PROJECT_ROOT") {
        let candidate = PathBuf::from(root).join("goblins.yaml");
        if candidate.exists() {
            return Ok(candidate);
        }
    }

    // If env var is set explicitly, prefer it (legacy behavior)
    if let Ok(cfg) = env::var("GOBLINOS_CONFIG") {
        let p = PathBuf::from(cfg);
        if p.exists() {
            return Ok(p);
        }
    }

    // NOTE: We have checked GOBLIN_PROJECT_ROOT above. For completeness
    // we'll also continue to walk upward from the current working directory
    // and exe path as before.

    // Check current working dir and walk upwards
    if let Ok(mut dir) = env::current_dir() {
        loop {
            let try_path = dir.join("goblins.yaml");
            if try_path.exists() {
                return Ok(try_path);
            }

            if !dir.pop() {
                break;
            }
        }
    }

    // Check exe location (in packaged apps we may be in different working dir)
    if let Ok(mut exe_dir) = env::current_exe().map(|p| p.parent().map(|p| p.to_path_buf()).unwrap_or_default()) {
        loop {
            let try_path = exe_dir.join("goblins.yaml");
            if try_path.exists() {
                return Ok(try_path);
            }
            if !exe_dir.pop() {
                break;
            }
        }
    }

    Err("goblins.yaml not found in current project; set GOBLINOS_CONFIG to a path to your project's goblins.yaml".to_string())
}
