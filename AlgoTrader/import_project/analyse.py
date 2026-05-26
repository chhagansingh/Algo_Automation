"""
CLI entry point: python -m import_project.analyse <project_folder>
Example: python -m import_project.analyse /Users/com/Desktop/R&D/my_new_bot
"""
import sys
import argparse
from pathlib import Path

from .scanner import ProjectScanner
from .extractor import StrategyExtractor
from .normalizer import AlgoNormalizer


def main():
    parser = argparse.ArgumentParser(description="Analyse a trading project and import into AlgoTrader")
    parser.add_argument("project_folder", help="Path to the project folder to analyse")
    parser.add_argument("--compare", action="store_true", help="Run backtest comparison after import")
    parser.add_argument("--days", type=int, default=365, help="Backtest period in days (default: 365)")
    args = parser.parse_args()

    project_path = Path(args.project_folder).resolve()
    if not project_path.exists():
        print(f"ERROR: Folder not found: {project_path}")
        sys.exit(1)

    print(f"\n🔍 Scanning project: {project_path.name}")
    scanner = ProjectScanner(project_path)
    findings = scanner.scan()
    scanner.print_summary()

    top_file = scanner.get_top_candidate()
    if not top_file:
        print("\n⚠️ No strategy candidate found. Exiting.")
        sys.exit(1)

    print(f"\n📋 Extracting strategy from: {top_file}")
    extractor = StrategyExtractor(top_file)
    extracted = extractor.extract()
    extractor.print_summary()

    print(f"\n📝 Generating AlgoBase class...")
    normalizer = AlgoNormalizer(extracted, project_path.name)
    output_file = normalizer.save("imported_algos")
    print(f"   Saved to: {output_file}")
    normalizer.print_next_steps()

    if args.compare:
        print(f"\n📊 Running backtest comparison...")
        from datetime import datetime, timedelta
        from .backtest_wrapper import compare_imported
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        compare_imported(normalizer.algo_id, start, end, interval="1d")


if __name__ == "__main__":
    main()
