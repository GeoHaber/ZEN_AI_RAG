
# 📦 ZenAI Installation Guide

## 1. Prerequisites
- Python 3.10+ installed.
- Internet connection (for first-time setup only).

## 2. Setup (Virgin Install)
1.  Unzip `ZenAI_Dist.zip` to a folder (e.g., `C:\ZenAI`).
2.  Open a terminal inside that folder.
3.  Create a virtual environment (Optional but Recommended):
    ```powershell
    python -m venv .venv
    .venv\Scripts\activate
    ```
4.  Install dependencies:
    ```powershell
    pip install -r requirements.txt
    ```

## 3. Run
Launch the Assistant:
```powershell
python zena.py
```
- The interface will open at http://localhost:8080.
- First run will download necessary AI models (~2GB).

## 4. Updates
To update, simply replace the `zena.py` and `ui/` folders from the new ZIP, keeping your `models/` directory intact.
