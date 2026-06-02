from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from aeris.config import AerisPaths


def _date(value: str) -> date:
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aeris scalable data and climate pipelines.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-dirs", help="Create the scalable dataset directory layout.")
    init_parser.add_argument("--dataset-root", type=Path, default=Path("datasets"))

    climate_parser = subparsers.add_parser("analyze-baixada", help="Run Baixada Santista historical climate analysis.")
    climate_parser.add_argument("--dataset-root", type=Path, default=Path("datasets"))
    climate_parser.add_argument("--output-root", type=Path, default=Path("outputs"))
    climate_parser.add_argument("--start-date", type=_date, default=date(1940, 1, 1))
    climate_parser.add_argument("--end-date", type=_date, default=date.today())
    climate_parser.add_argument("--baseline-start-year", type=int, default=1961)
    climate_parser.add_argument("--baseline-end-year", type=int, default=1990)
    climate_parser.add_argument("--source-model", default="era5")
    climate_parser.add_argument("--years-per-chunk", type=int, default=1)
    climate_parser.add_argument("--use-grid", action="store_true")
    climate_parser.add_argument("--grid-spacing-degrees", type=float, default=0.25)
    climate_parser.add_argument("--force-download", action="store_true")
    climate_parser.add_argument("--force-rebuild-outputs", action="store_true")
    climate_parser.add_argument("--json-logs", action="store_true")
    climate_parser.add_argument("--log-level", default="INFO")
    climate_parser.add_argument("--max-batches", type=int, default=None)
    climate_parser.add_argument("--request-delay-seconds", type=float, default=1.0)
    climate_parser.add_argument("--retry-attempts", type=int, default=8)
    climate_parser.add_argument("--retry-base-delay-seconds", type=float, default=5.0)
    climate_parser.add_argument("--retry-max-delay-seconds", type=float, default=300.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "init-dirs":
        paths = AerisPaths.from_root(args.dataset_root).ensure()
        print(paths.root)
        return
    if args.command == "analyze-baixada":
        from aeris.climate.pipeline import BaixadaSantistaAnalysisConfig, run_baixada_santista_analysis

        run_baixada_santista_analysis(
            BaixadaSantistaAnalysisConfig(
                dataset_root=args.dataset_root,
                output_root=args.output_root,
                start_date=args.start_date,
                end_date=args.end_date,
                baseline_start_year=args.baseline_start_year,
                baseline_end_year=args.baseline_end_year,
                source_model=args.source_model,
                years_per_chunk=args.years_per_chunk,
                use_grid=args.use_grid,
                grid_spacing_degrees=args.grid_spacing_degrees,
                force_download=args.force_download,
                force_rebuild_outputs=args.force_rebuild_outputs,
                json_logs=args.json_logs,
                log_level=args.log_level,
                max_batches=args.max_batches,
                request_delay_seconds=args.request_delay_seconds,
                retry_attempts=args.retry_attempts,
                retry_base_delay_seconds=args.retry_base_delay_seconds,
                retry_max_delay_seconds=args.retry_max_delay_seconds,
            ),
        )
        return
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
