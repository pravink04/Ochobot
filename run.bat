@echo off
REM Launches the app with the cyberpunk theme applied explicitly (works even if .streamlit\config.toml is not picked up).
python -m streamlit run app.py ^
  --theme.base dark ^
  --theme.primaryColor "#19e3ff" ^
  --theme.backgroundColor "#030712" ^
  --theme.secondaryBackgroundColor "#07142b" ^
  --theme.textColor "#d6f4ff" ^
  --client.toolbarMode minimal