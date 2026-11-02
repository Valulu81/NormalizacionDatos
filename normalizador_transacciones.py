"""Sistema inicial de normalización y exploración interactiva de transacciones."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NoReturn, Sequence


@dataclass(frozen=True)
class Transaction:
    id: str
    amount: Decimal
    currency: str
    timestamp: str
    status: str
    source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "amount": float(self.amount),
            "currency": self.currency,
            "timestamp": self.timestamp,
            "status": self.status,
            "source": self.source,
        }


@dataclass(frozen=True)
class InvalidTransaction:
    position: int
    source: str | None
    original: object
    errors: tuple[str, ...]


@dataclass(frozen=True)
class NormalizationReport:
    processed: int
    valid: tuple[Transaction, ...]
    invalid: tuple[InvalidTransaction, ...]


SOURCE_KEYS: dict[str, tuple[str, str, str, str, str]] = {
    "source_a": ("id", "amount", "currency", "timestamp", "status"),
    "source_b": (
        "transaction_id",
        "total",
        "currency_code",
        "created_at",
        "state",
    ),
    "source_c": ("ref", "amount", "currency", "date", "result"),
}

STATUS_MAP = {
    "completed": "SUCCESS",
    "success": "SUCCESS",
    "ok": "SUCCESS",
    "failed": "FAILED",
    "error": "FAILED",
    "declined": "FAILED",
    "pending": "PENDING",
    "processing": "PENDING",
    "created": "PENDING",
}

CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP"}


def _reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"Constante JSON no estándar: {value}")


def load_records(path: Path) -> list[object]:
    with path.open("r", encoding="utf-8") as file:
        content = file.read()
    return parse_records(content)


def parse_records(content: str) -> list[object]:
    payload: object = json.loads(
        content, parse_float=Decimal, parse_constant=_reject_json_constant
    )
    if not isinstance(payload, list):
        raise ValueError("La raíz del archivo JSON debe ser un arreglo de transacciones.")
    return payload


def detect_source(record: dict[str, object]) -> str | None:
    if any(key in record for key in ("transaction_id", "total", "created_at", "state")):
        return "source_b"
    if any(key in record for key in ("ref", "date", "result")):
        return "source_c"
    if any(key in record for key in ("id", "amount", "currency", "timestamp", "status")):
        return "source_a"
    return None


def _parse_amount(value: object, *, minor_units: bool = False) -> tuple[Decimal, str | None]:
    inferred_currency: str | None = None
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("el monto debe ser texto o un número")

    raw = str(value).strip()
    if not raw:
        raise ValueError("el monto está vacío")

    for symbol, currency in CURRENCY_SYMBOLS.items():
        if symbol in raw:
            if inferred_currency is not None and inferred_currency != currency:
                raise ValueError("el monto contiene símbolos de moneda incompatibles")
            inferred_currency = currency
            raw = raw.replace(symbol, "")
    raw = raw.replace(" ", "")

    if isinstance(value, str):
        if raw.count(",") > 1 and "." not in raw:
            raise ValueError("el formato del monto es ambiguo")
        if "," in raw and "." in raw:
            decimal_separator = "," if raw.rfind(",") > raw.rfind(".") else "."
            grouping_separator = "." if decimal_separator == "," else ","
            raw = raw.replace(grouping_separator, "")
            if decimal_separator == ",":
                raw = raw.replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")

    try:
        amount = Decimal(raw)
    except InvalidOperation as error:
        raise ValueError("el monto no tiene un formato numérico válido") from error

    if not amount.is_finite():
        raise ValueError("el monto debe ser finito")
    if minor_units:
        amount /= Decimal("100")
    if amount <= 0:
        raise ValueError("el monto debe ser mayor que cero")
    return amount, inferred_currency


def _normalize_currency(value: object, inferred: str | None) -> str:
    if value is None or value == "":
        if inferred is None:
            raise ValueError("falta la moneda y no se puede inferir del monto")
        return inferred
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z]{3}", value.strip()) is None:
        raise ValueError("la moneda debe ser un código de tres letras")
    currency = value.strip().upper()
    if inferred is not None and inferred != currency:
        raise ValueError("el símbolo del monto no coincide con la moneda declarada")
    return currency


def _normalize_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("la fecha debe ser un texto no vacío")
    raw = value.strip()
    if raw.endswith(("Z", "z")):
        raw = f"{raw[:-1]}+00:00"

    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        for date_format in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw, date_format)
                break
            except ValueError:
                continue
    if parsed is None:
        raise ValueError("la fecha no tiene un formato admitido o no existe")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat(timespec="auto").replace("+00:00", "Z")


def _normalize_status(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("el estado debe ser texto")
    status = STATUS_MAP.get(value.strip().lower())
    if status is None:
        raise ValueError("el estado no está reconocido")
    return status


def _normalize_id(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("el identificador debe ser texto o entero")
    identifier = str(value).strip()
    if not identifier:
        raise ValueError("el identificador está vacío")
    return identifier


def normalize_record(record: object, position: int) -> Transaction | InvalidTransaction:
    if not isinstance(record, dict):
        return InvalidTransaction(position, None, record, ("el registro debe ser un objeto JSON",))

    source = detect_source(record)
    if source is None:
        return InvalidTransaction(
            position, None, record, ("no se pudo identificar la fuente del registro",)
        )

    id_key, amount_key, currency_key, timestamp_key, status_key = SOURCE_KEYS[source]
    errors: list[str] = []
    normalized_id: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    timestamp: str | None = None
    status: str | None = None

    try:
        normalized_id = _normalize_id(record.get(id_key))
    except ValueError as error:
        errors.append(f"{id_key}: {error}")

    try:
        amount, inferred_currency = _parse_amount(
            record.get(amount_key), minor_units=(source == "source_b")
        )
    except ValueError as error:
        inferred_currency = None
        errors.append(f"{amount_key}: {error}")

    try:
        currency = _normalize_currency(record.get(currency_key), inferred_currency)
    except ValueError as error:
        errors.append(f"{currency_key}: {error}")

    try:
        timestamp = _normalize_timestamp(record.get(timestamp_key))
    except ValueError as error:
        errors.append(f"{timestamp_key}: {error}")

    try:
        status = _normalize_status(record.get(status_key))
    except ValueError as error:
        errors.append(f"{status_key}: {error}")

    if errors:
        return InvalidTransaction(position, source, record, tuple(errors))

    if normalized_id is None or amount is None or currency is None or timestamp is None or status is None:
        raise RuntimeError("La validación no produjo los valores esperados.")
    return Transaction(normalized_id, amount, currency, timestamp, status, source)


def normalize_records(records: Sequence[object]) -> NormalizationReport:
    valid: list[Transaction] = []
    invalid: list[InvalidTransaction] = []
    for position, record in enumerate(records, start=1):
        result = normalize_record(record, position)
        if isinstance(result, Transaction):
            valid.append(result)
        else:
            invalid.append(result)
    return NormalizationReport(len(records), tuple(valid), tuple(invalid))


def calculate_metrics(report: NormalizationReport) -> dict[str, object]:
    status_counts = Counter(transaction.status for transaction in report.valid)
    currency_totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    for transaction in report.valid:
        currency_totals[transaction.currency] += transaction.amount

    return {
        "processed": report.processed,
        "valid": len(report.valid),
        "invalid": len(report.invalid),
        "by_status": {status: status_counts[status] for status in ("SUCCESS", "FAILED", "PENDING")},
        "totals_by_currency": dict(sorted(currency_totals.items())),
    }


def _display_transactions(transactions: Sequence[Transaction]) -> None:
    if not transactions:
        print("No hay transacciones para mostrar.")
        return
    for transaction in transactions:
        print(
            f"{transaction.id} | {transaction.amount:.2f} {transaction.currency} | "
            f"{transaction.timestamp} | {transaction.status} | {transaction.source}"
        )


def _show_metrics(report: NormalizationReport) -> None:
    metrics = calculate_metrics(report)
    print(f"\nProcesadas: {metrics['processed']}")
    print(f"Válidas: {metrics['valid']}")
    print(f"Inválidas: {metrics['invalid']}")
    print("Conteo por estado:")
    for status, count in metrics["by_status"].items():
        print(f"  {status}: {count}")
    print("Totales por moneda:")
    if metrics["totals_by_currency"]:
        for currency, total in metrics["totals_by_currency"].items():
            print(f"  {currency}: {total:.2f}")
    else:
        print("  Sin transacciones válidas.")


def _show_invalid(report: NormalizationReport) -> None:
    if not report.invalid:
        print("No hay registros inválidos.")
        return
    for invalid in report.invalid:
        source = invalid.source or "desconocida"
        reasons = "; ".join(invalid.errors)
        print(f"\nRegistro {invalid.position} (fuente: {source}): {reasons}")
        print(json.dumps(invalid.original, ensure_ascii=False, default=str))


def _filter_transactions(report: NormalizationReport) -> None:
    status_filter = input("Estado (SUCCESS/FAILED/PENDING o Enter para omitir): ").strip().upper()
    currency_filter = input("Moneda o Enter para omitir: ").strip().upper()
    source_filter = input("Fuente (source_a/source_b/source_c o Enter para omitir): ").strip().lower()

    filtered = tuple(
        transaction
        for transaction in report.valid
        if (not status_filter or transaction.status == status_filter)
        and (not currency_filter or transaction.currency == currency_filter)
        and (not source_filter or transaction.source == source_filter)
    )
    _display_transactions(filtered)


def _export_transactions(report: NormalizationReport) -> None:
    name = input("Nombre del archivo de salida [transacciones_normalizadas.json]: ").strip()
    output_path = Path(name or "transacciones_normalizadas.json")
    if output_path.suffix.lower() != ".json":
        output_path = output_path.with_suffix(".json")
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            [transaction.to_dict() for transaction in report.valid],
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")
    print(f"Se exportaron {len(report.valid)} transacciones válidas a {output_path}.")


def run_menu(report: NormalizationReport) -> None:
    while True:
        print(
            "\n=== Explorador de transacciones ===\n"
            "1. Listar transacciones válidas\n"
            "2. Filtrar transacciones\n"
            "3. Consultar métricas\n"
            "4. Inspeccionar registros inválidos\n"
            "5. Exportar transacciones válidas a JSON\n"
            "0. Salir"
        )
        choice = input("Selecciona una opción: ").strip()
        if choice == "1":
            _display_transactions(report.valid)
        elif choice == "2":
            _filter_transactions(report)
        elif choice == "3":
            _show_metrics(report)
        elif choice == "4":
            _show_invalid(report)
        elif choice == "5":
            _export_transactions(report)
        elif choice == "0":
            print("Hasta luego.")
            return
        else:
            print("Opción no válida; selecciona una opción del menú.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normaliza transacciones desde un archivo JSON.")
    parser.add_argument("archivo", nargs="?", help="ruta del archivo JSON de entrada")
    args = parser.parse_args(argv)

    try:
        input_name = args.archivo or input("Ruta del archivo JSON: ").strip()
        if not input_name:
            print("Debes indicar la ruta de un archivo JSON.", file=sys.stderr)
            return 2
        records = load_records(Path(input_name))
        report = normalize_records(records)
    except EOFError:
        print("\nEntrada cancelada.", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        print(f"No se pudo cargar el archivo: {error}", file=sys.stderr)
        return 1

    print(
        f"Archivo cargado: {report.processed} registros; "
        f"{len(report.valid)} válidos y {len(report.invalid)} inválidos."
    )
    try:
        run_menu(report)
    except EOFError:
        print("\nFin de la entrada; se cierra la interfaz.")
    except OSError as error:
        print(f"Error al exportar el archivo: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
