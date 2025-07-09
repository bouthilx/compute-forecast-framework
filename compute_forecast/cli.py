"""Command-line interface for compute-forecast."""

import argparse
import sys
from compute_forecast import __version__


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compute Forecast - ML Research Computational Requirements Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  compute-forecast --version
  compute-forecast collect --venue NeurIPS --year 2024
  compute-forecast analyze --input papers.json
  compute-forecast report --output forecast.pdf
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"compute-forecast {__version__}"
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Collect command
    collect_parser = subparsers.add_parser("collect", help="Collect research papers")
    collect_parser.add_argument(
        "--venue", help="Conference venue (e.g., NeurIPS, ICML)"
    )
    collect_parser.add_argument("--year", type=int, help="Publication year")
    collect_parser.add_argument(
        "--limit", type=int, default=100, help="Maximum papers to collect"
    )

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze computational requirements"
    )
    analyze_parser.add_argument(
        "--input", required=True, help="Input JSON file with papers"
    )
    analyze_parser.add_argument("--output", help="Output file for analysis results")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate forecast report")
    report_parser.add_argument("--input", help="Analysis results file")
    report_parser.add_argument(
        "--output", default="forecast.pdf", help="Output report file"
    )

    args = parser.parse_args()

    if args.command == "collect":
        print(f"Collecting papers from {args.venue} {args.year} (limit: {args.limit})")
        print("Note: This is a placeholder. Full implementation coming soon.")
    elif args.command == "analyze":
        print(f"Analyzing papers from {args.input}")
        print("Note: This is a placeholder. Full implementation coming soon.")
    elif args.command == "report":
        print(f"Generating report to {args.output}")
        print("Note: This is a placeholder. Full implementation coming soon.")
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
