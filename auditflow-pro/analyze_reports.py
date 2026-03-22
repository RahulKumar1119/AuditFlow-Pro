#!/usr/bin/env python3
"""
Report Analyzer - Analyzes and compares test reports
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class ReportAnalyzer:
    """Analyzes test reports and provides insights"""

    def __init__(self, report_dir: str = "test_reports"):
        self.report_dir = Path(report_dir)

    def get_latest_report(self) -> Dict:
        """Get the latest JSON report"""
        json_files = sorted(self.report_dir.glob("test_report_*.json"))
        if not json_files:
            print("No reports found")
            return None

        latest = json_files[-1]
        with open(latest) as f:
            return json.load(f)

    def get_all_reports(self) -> List[Dict]:
        """Get all JSON reports"""
        reports = []
        for json_file in sorted(self.report_dir.glob("test_report_*.json")):
            with open(json_file) as f:
                reports.append(json.load(f))
        return reports

    def print_summary(self, report: Dict):
        """Print report summary"""
        print(f"\n{'=' * 80}")
        print(f"  TEST REPORT SUMMARY")
        print(f"{'=' * 80}\n")

        print(f"Timestamp:  {report['timestamp']}")
        print(f"Total:      {report['total_tests']}")
        print(f"Passed:     {report['passed']} ✓")
        print(f"Failed:     {report['failed']} ✗")
        print(f"Skipped:    {report['skipped']} ⊘")
        print(f"Pass Rate:  {report['pass_rate']:.1f}%\n")

    def print_module_breakdown(self, report: Dict):
        """Print breakdown by module"""
        print(f"{'=' * 80}")
        print(f"  RESULTS BY MODULE")
        print(f"{'=' * 80}\n")

        modules: Dict[str, Dict] = {}
        for result in report["results"]:
            module = result["module"]
            if module not in modules:
                modules[module] = {"passed": 0, "failed": 0, "skipped": 0, "total": 0}

            modules[module]["total"] += 1
            if result["status"] == "passed":
                modules[module]["passed"] += 1
            elif result["status"] == "failed":
                modules[module]["failed"] += 1
            else:
                modules[module]["skipped"] += 1

        for module in sorted(modules.keys()):
            stats = modules[module]
            pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            status = "✓" if stats["failed"] == 0 else "✗"

            print(f"{status} {module:20} {stats['passed']:2}/{stats['total']:2} ({pass_rate:5.1f}%)")

        print()

    def print_slowest_tests(self, report: Dict, limit: int = 10):
        """Print slowest tests"""
        print(f"{'=' * 80}")
        print(f"  SLOWEST TESTS (Top {limit})")
        print(f"{'=' * 80}\n")

        sorted_tests = sorted(report["results"], key=lambda x: x["duration"], reverse=True)[:limit]

        for i, test in enumerate(sorted_tests, 1):
            print(f"{i:2}. {test['name']:50} {test['duration']:.3f}s ({test['module']})")

        print()

    def print_failed_tests(self, report: Dict):
        """Print failed tests"""
        failed = [r for r in report["results"] if r["status"] == "failed"]

        if not failed:
            print(f"\n{'=' * 80}")
            print(f"  ✓ NO FAILED TESTS")
            print(f"{'=' * 80}\n")
            return

        print(f"\n{'=' * 80}")
        print(f"  FAILED TESTS ({len(failed)})")
        print(f"{'=' * 80}\n")

        for test in failed:
            print(f"✗ {test['name']} ({test['module']})")
            print(f"  Duration: {test['duration']:.3f}s\n")

    def compare_reports(self, report1: Dict, report2: Dict):
        """Compare two reports"""
        print(f"\n{'=' * 80}")
        print(f"  REPORT COMPARISON")
        print(f"{'=' * 80}\n")

        print(f"Report 1: {report1['timestamp']}")
        print(f"  Total: {report1['total_tests']}, Passed: {report1['passed']}, Pass Rate: {report1['pass_rate']:.1f}%")

        print(f"\nReport 2: {report2['timestamp']}")
        print(f"  Total: {report2['total_tests']}, Passed: {report2['passed']}, Pass Rate: {report2['pass_rate']:.1f}%")

        # Calculate differences
        total_diff = report2["total_tests"] - report1["total_tests"]
        passed_diff = report2["passed"] - report1["passed"]
        failed_diff = report2["failed"] - report1["failed"]
        pass_rate_diff = report2["pass_rate"] - report1["pass_rate"]

        print(f"\nChanges:")
        print(f"  Total Tests:  {total_diff:+d}")
        print(f"  Passed:       {passed_diff:+d}")
        print(f"  Failed:       {failed_diff:+d}")
        print(f"  Pass Rate:    {pass_rate_diff:+.1f}%")

        if pass_rate_diff > 0:
            print(f"\n✓ Pass rate improved by {pass_rate_diff:.1f}%")
        elif pass_rate_diff < 0:
            print(f"\n✗ Pass rate decreased by {abs(pass_rate_diff):.1f}%")
        else:
            print(f"\n= Pass rate unchanged")

        print()

    def print_statistics(self, report: Dict):
        """Print detailed statistics"""
        print(f"\n{'=' * 80}")
        print(f"  STATISTICS")
        print(f"{'=' * 80}\n")

        durations = [r["duration"] for r in report["results"]]
        total_duration = sum(durations)
        avg_duration = total_duration / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        print(f"Execution Time:")
        print(f"  Total:   {total_duration:.2f}s")
        print(f"  Average: {avg_duration:.3f}s")
        print(f"  Min:     {min_duration:.3f}s")
        print(f"  Max:     {max_duration:.3f}s")

        # Module statistics
        modules: Dict[str, List[float]] = {}
        for result in report["results"]:
            module = result["module"]
            if module not in modules:
                modules[module] = []
            modules[module].append(result["duration"])

        print(f"\nModule Execution Times:")
        for module in sorted(modules.keys()):
            times = modules[module]
            total = sum(times)
            avg = total / len(times)
            print(f"  {module:20} {total:7.2f}s (avg: {avg:.3f}s, count: {len(times)})")

        print()

    def export_csv(self, report: Dict, filename: str = "test_report.csv"):
        """Export report to CSV"""
        import csv

        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Test Name", "Module", "Status", "Duration (s)"])

            for result in report["results"]:
                writer.writerow(
                    [result["name"], result["module"], result["status"], result["duration"]]
                )

        print(f"✓ Report exported to {filename}")


def main():
    """Main entry point"""
    analyzer = ReportAnalyzer()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "latest":
            report = analyzer.get_latest_report()
            if report:
                analyzer.print_summary(report)
                analyzer.print_module_breakdown(report)
                analyzer.print_slowest_tests(report)
                analyzer.print_statistics(report)

        elif command == "failed":
            report = analyzer.get_latest_report()
            if report:
                analyzer.print_failed_tests(report)

        elif command == "compare":
            reports = analyzer.get_all_reports()
            if len(reports) >= 2:
                analyzer.compare_reports(reports[-2], reports[-1])
            else:
                print("Need at least 2 reports to compare")

        elif command == "csv":
            report = analyzer.get_latest_report()
            if report:
                filename = sys.argv[2] if len(sys.argv) > 2 else "test_report.csv"
                analyzer.export_csv(report, filename)

        elif command == "list":
            reports = analyzer.get_all_reports()
            print(f"\n{'=' * 80}")
            print(f"  AVAILABLE REPORTS ({len(reports)})")
            print(f"{'=' * 80}\n")
            for i, report in enumerate(reports, 1):
                print(f"{i}. {report['timestamp']} - {report['passed']}/{report['total_tests']} passed")
            print()

        else:
            print_help()

    else:
        # Default: show latest report
        report = analyzer.get_latest_report()
        if report:
            analyzer.print_summary(report)
            analyzer.print_module_breakdown(report)
            analyzer.print_slowest_tests(report, limit=5)
            analyzer.print_statistics(report)


def print_help():
    """Print help message"""
    print("""
Test Report Analyzer

Usage: python3 analyze_reports.py [command]

Commands:
  latest      Show latest report summary (default)
  failed      Show failed tests
  compare     Compare last two reports
  csv         Export latest report to CSV
  list        List all available reports

Examples:
  python3 analyze_reports.py latest
  python3 analyze_reports.py failed
  python3 analyze_reports.py compare
  python3 analyze_reports.py csv results.csv
  python3 analyze_reports.py list
""")


if __name__ == "__main__":
    main()
