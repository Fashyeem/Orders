"""Starter file for the L1 AI-Assisted Coding assignment.

Complete only the marked TODOs and correct the seeded issues using an approved
AI coding assistant. The utility reads retail orders and creates small summary
outputs for a store operations analyst.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ROOT should point to the repository root (the directory containing this file).
# Path(__file__).resolve().parents[1] went one level too high when the script
# was executed from the repository; use .parent instead.
ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "retail_orders.csv"
OUTPUT_DIR = ROOT / "outputs"


def load_orders() -> list[dict[str, str]]:
    """Load order records from the provided CSV file."""
    with DATA_FILE.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def standardize_date(raw_date: str) -> str | None:
    """Return an ISO date value, or None when the input cannot be interpreted."""
    # Support common variations in the data: YYYY-MM-DD, DD/MM/YYYY and YYYY/MM/DD
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
        try:
            dt = datetime.strptime(raw_date.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue
    return None


def parse_number(raw_value: str, field_name: str, issues: list[str], order_id: str) -> float | None:
    """Convert a numeric string to float and record unusable values.

    Treat empty strings and common non-numeric tokens (N/A, na, null) as invalid
    and record a helpful issue message that includes the field name and value.
    """
    if raw_value is None:
        issues.append(f"{order_id}: invalid {field_name} '{raw_value}'")
        return None

    sval = raw_value.strip()
    if sval == "" or sval.upper() in {"N/A", "NA", "NULL"}:
        issues.append(f"{order_id}: invalid {field_name} '{raw_value}'")
        return None

    try:
        return float(sval)
    except ValueError:
        issues.append(f"{order_id}: invalid {field_name} '{raw_value}'")
        return None


def normalize_label(value: str) -> str:
    """Standardize spacing and capitalization for categorical labels."""
    return value.strip().title()


def clean_order(row: dict[str, str], issues: list[str]) -> dict[str, str | float] | None:
    """Clean one order row and calculate net sales for usable completed orders."""
    order_id = row["order_id"]
    cleaned_date = standardize_date(row["order_date"])
    if cleaned_date is None:
        issues.append(f"{order_id}: invalid order_date '{row['order_date']}'")
        return None

    units = parse_number(row["units_sold"], "units_sold", issues, order_id)
    price = parse_number(row["unit_price"], "unit_price", issues, order_id)
    discount = parse_number(row["discount_pct"], "discount_pct", issues, order_id)
    if units is None or price is None or discount is None:
        return None

    status = normalize_label(row["order_status"])
    if status != "Completed":
        return None

    # Discounts below 0 or above 100 should be logged and excluded.
    if discount < 0 or discount > 100:
        issues.append(f"{order_id}: invalid discount_pct '{discount}' (must be 0-100)")
        return None

    # discount_pct is stored as a percentage value, not a multiplier.
    # Convert percentage to decimal multiplier when computing net sales.
    gross_sales = units * price
    net_sales = gross_sales - (gross_sales * discount / 100)

    return {
        "order_id": order_id,
        "order_date": cleaned_date,
        "region": normalize_label(row["region"]),
        "product_category": normalize_label(row["product_category"]),
        "sales_channel": normalize_label(row["sales_channel"]),
        "units_sold": units,
        "unit_price": round(price, 2),
        "discount_pct": discount,
        "net_sales": round(net_sales, 2),
    }


def create_daily_summary(cleaned_orders: list[dict[str, str | float]]) -> list[dict[str, str | float]]:
    """Aggregate usable orders by date."""
    daily = defaultdict(lambda: {"order_count": 0, "total_net_sales": 0.0})

    for order in cleaned_orders:
        date = order["order_date"]
        daily[date]["order_count"] += 1
        daily[date]["total_net_sales"] += order["net_sales"]

    # Return rows sorted by date (ISO formatted date strings sort lexically)
    return sorted(
        [{"order_date": date, **metrics} for date, metrics in daily.items()],
        key=lambda x: x["order_date"],
    )


def write_csv(path: Path, rows: list[dict[str, str | float]], fieldnames: list[str]) -> None:
    """Write a list of dictionaries to a CSV output."""
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_summary() -> None:
    """Run the cleaning and summary workflow."""
    issues: list[str] = []
    raw_orders = load_orders()
    cleaned_orders = []
    for row in raw_orders:
        cleaned = clean_order(row, issues)
        if cleaned is not None:
            cleaned_orders.append(cleaned)

    summary = create_daily_summary(cleaned_orders)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(
        OUTPUT_DIR / "cleaned_completed_orders.csv",
        cleaned_orders,
        [
            "order_id",
            "order_date",
            "region",
            "product_category",
            "sales_channel",
            "units_sold",
            "unit_price",
            "discount_pct",
            "net_sales",
        ],
    )
    write_csv(
        OUTPUT_DIR / "daily_sales_summary.csv",
        summary,
        ["order_date", "order_count", "total_net_sales"],
    )
    (OUTPUT_DIR / "issue_log.txt").write_text("\n".join(issues), encoding="utf-8")

    print(f"Created outputs for {len(cleaned_orders)} cleaned completed orders.")
    print(f"Recorded {len(issues)} data issues.")


if __name__ == "__main__":
    run_summary()
