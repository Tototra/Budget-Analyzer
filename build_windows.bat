@echo off
echo === Budget Analyzer — Build Windows ===
echo.

python -m venv venv
call venv\Scripts\activate.bat

pip install -q -r requirements.txt pyinstaller

pyinstaller ^
    --name BudgetAnalyzer ^
    --windowed ^
    --add-data "static;static" ^
    --add-data "rules.py;." ^
    --add-data "ollama_classify.py;." ^
    --add-data "parsers.py;." ^
    --add-data "excel_export.py;." ^
    --hidden-import flask ^
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --hidden-import openpyxl.chart ^
    --hidden-import openpyxl.chart.label ^
    --hidden-import openpyxl.chart.marker ^
    --hidden-import openpyxl.chart.shapes ^
    --hidden-import openpyxl.styles ^
    --hidden-import openpyxl.utils ^
    --hidden-import pdfplumber ^
    --hidden-import requests ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module streamlit ^
    --exclude-module plotly ^
    --distpath dist ^
    --clean -y ^
    server.py

echo.
echo Build termine. L'executable est dans dist\BudgetAnalyzer\
pause
