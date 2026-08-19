#!/usr/bin/env python3
"""Filter is_anomaly=true rows from a prediction TSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write rows with is_anomaly=true to a new TSV file."
    )
    parser.add_argument("--input", required=True, help="Prediction TSV path")
    parser.add_argument("--output", required=True, help="Filtered TSV output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Prediction TSV not found: {input_path}")
    if output_path == input_path:
        raise ValueError("Output path must differ from input path")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_count = 0
    anomaly_count = 0

    with input_path.open("r", encoding="utf-8", newline="") as input_handle:
        reader = csv.DictReader(input_handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"TSV has no header: {input_path}")
        fieldnames = list(reader.fieldnames)
        if "is_anomaly" not in fieldnames:
            raise ValueError(f"TSV is missing 'is_anomaly' column: {input_path}")

        with output_path.open("w", encoding="utf-8", newline="") as output_handle:
            writer = csv.DictWriter(
                output_handle,
                fieldnames=fieldnames,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()

            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(
                        f"Malformed TSV row at line {line_number}: {input_path}"
                    )
                total_count += 1
                flag = row["is_anomaly"].strip().lower()
                if flag not in {"true", "false"}:
                    raise ValueError(
                        f"Invalid is_anomaly value at line {line_number}: "
                        f"{row['is_anomaly']!r}"
                    )
                if flag == "true":
                    writer.writerow(row)
                    anomaly_count += 1

    print(f"Read {total_count} rows")
    print(f"Selected {anomaly_count} rows with is_anomaly=true")
    print(f"Wrote filtered TSV to {output_path}")


if __name__ == "__main__":
    main()
