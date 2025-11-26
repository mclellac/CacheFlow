# Code Audit & Improvement Plan

This document tracks the findings of a comprehensive code audit and outlines the plan to address them.

## Initial Audit (2025-11-26)

### 1. Code Style & Conformance

*   **PEP8:** The codebase is largely compliant, but a full pass is needed to catch minor inconsistencies in spacing and line length.
*   **Docstrings:** Docstrings are present but do not consistently follow the Google Style Guide. Many are missing parameter descriptions and return value explanations.
*   **Inline Comments:** The project's `AGENTS.md` explicitly forbids inline comments, but some still exist. These need to be removed or converted into docstrings.

### 2. UI/UX Issues & Bugs

*   **[BUG] Analyze Button is not styled:**
    *   **File:** `src/ui/header_dialog.ui`
    *   **Issue:** The "Analyze" button is a standard `GtkButton`, not a styled Adwaita button. It does not use the system accent color, making it look out of place.
    *   **Resolution:** Convert the button to use the `.suggested-action` style class.

*   **[BUG] Analysis Feature is Incomplete:**
    *   **Files:** `src/header_dialog.py`, `src/window.py`, `src/analysis_dialog.py`
    *   **Issue:** The `HeaderDialog` correctly emits an `analyze-clicked` signal, but no handler is connected to it in the main window. The `HeaderAnalysisDialog`, which is fully capable of displaying the analysis, is never instantiated or presented to the user.
    *   **Resolution:** Implement the signal handler in `window.py` to create and show the `HeaderAnalysisDialog` when the button is clicked.

### 3. Architectural Improvements

*   **UI/Logic Separation:** While `AGENTS.md` mandates UI separation, there are instances of UI logic (e.g., Pango attribute manipulation in `header_dialog.py`) that could be further abstracted for clarity. This is a lower priority but should be noted for future refactoring.

## Action Plan

-   [ ] **Task 1:** Fix the "Analyze" button style in `header_dialog.ui`.
-   [ ] **Task 2:** Connect the `analyze-clicked` signal in `window.py` to launch the `HeaderAnalysisDialog`.
-   [ ] **Task 3:** Perform a full codebase scan for PEP8 violations and fix them.
-   [ ] **Task 4:** Review and update all major docstrings to conform to the Google Style Guide.
-   [ ] **Task 5:** Remove all inline comments.
