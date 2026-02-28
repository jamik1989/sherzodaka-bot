param(
  [int]$Port = 8000
)
$env:PYTHONUNBUFFERED="1"
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt

# API (webhook) + bot runner birga bo'lsa keyin sozlaymiz.
# Hozircha FastAPI ni ishga tushiramiz:
uvicorn app.main:app --host 0.0.0.0 --port $Port --reload
