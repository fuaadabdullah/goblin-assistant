fn main() {
    // Run the tauri build-time helper to prepare the app context.
    // This will set up OUT_DIR and other generated assets used by
    // `tauri::generate_context!()` in the application.
    tauri_build::build()
}
