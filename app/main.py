"""Ponto de entrada da aplicação.

Execute com:  uvicorn app.main:app --reload --host 0.0.0.0
"""

from app.factory import create_app

app = create_app()
