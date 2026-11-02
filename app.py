"""Interfaz web para normalizar y explorar transacciones."""

from __future__ import annotations

import json

from flask import Flask, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from normalizador_transacciones import (
    NormalizationReport,
    Transaction,
    calculate_metrics,
    normalize_records,
    parse_records,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def _render_page(
    *,
    report: NormalizationReport | None = None,
    filename: str = "",
    error: str | None = None,
    status_code: int = 200,
) -> tuple[str, int]:
    transactions: tuple[Transaction, ...] = report.valid if report else ()
    invalid_rows: list[dict[str, object]] = []
    metrics: dict[str, object] = {
        "processed": 0,
        "valid": 0,
        "invalid": 0,
        "by_status": {"SUCCESS": 0, "FAILED": 0, "PENDING": 0},
        "totals_by_currency": {},
    }

    if report:
        metrics = calculate_metrics(report)
        invalid_rows = [
            {
                "position": record.position,
                "source": record.source or "desconocida",
                "original": json.dumps(record.original, ensure_ascii=False, default=str),
                "errors": record.errors,
            }
            for record in report.invalid
        ]

    response = render_template(
        "index.html",
        report=report,
        transactions=transactions,
        invalid_rows=invalid_rows,
        metrics=metrics,
        export_transactions=[transaction.to_dict() for transaction in transactions],
        filename=filename,
        error=error,
        currencies=sorted({transaction.currency for transaction in transactions}),
    )
    return response, status_code


@app.get("/")
def index():
    return _render_page()


@app.post("/")
def upload():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return _render_page(error="Selecciona un archivo JSON.")
    if not uploaded_file.filename.lower().endswith(".json"):
        return _render_page(error="El archivo debe tener la extensión .json.")

    try:
        content = uploaded_file.read().decode("utf-8")
        records = parse_records(content)
    except UnicodeDecodeError:
        return _render_page(error="El archivo no contiene texto UTF-8 válido.")
    except (json.JSONDecodeError, ValueError) as error:
        return _render_page(error=f"No se pudo interpretar el archivo JSON: {error}")

    report = normalize_records(records)
    return _render_page(report=report, filename=uploaded_file.filename)


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error: RequestEntityTooLarge):
    return _render_page(error="El archivo supera el límite de 10 MB.", status_code=413)


if __name__ == "__main__":
    app.run()
