"""
ProjectScanner — Analyse any Python project for trading strategy patterns.
"""
import ast
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = __import__("logging").getLogger(__name__)

# Keywords that indicate trading logic
TRADING_KEYWORDS = [
    "backtest", "strategy", "signal", "entry", "exit", "stoploss", "sl",
    "target", "takeprofit", "tp", "pnl", "profit", "loss", "win_rate",
    "lot_size", "position", "trade", "buy", "sell", "call", "put",
    "strike", "atm", "iv", "premium", "rsi", "ema", "sma", "macd",
    "bollinger", "adx", "atr", "vwap", "nifty", "banknifty",
]

# File patterns that usually contain strategy logic
STRATEGY_FILE_PATTERNS = [
    "backtest", "strategy", "trade", "signal", "algo",
    "main", "bot", "engine", "core",
]


class ProjectScanner:
    """Scans a project directory and identifies potential strategy files."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.py_files: List[Path] = []
        self.strategy_files: List[Dict[str, Any]] = []
        self.findings: Dict[str, Any] = {
            "project_name": self.project_path.name,
            "total_py_files": 0,
            "strategy_candidates": [],
            "imports": set(),
            "constants": {},
            "functions": [],
            "classes": [],
        }

    def scan(self) -> Dict[str, Any]:
        """Full scan: find all .py files, rank by strategy relevance."""
        self._find_python_files()
        self._analyse_files()
        self.findings["total_py_files"] = len(self.py_files)
        self.findings["strategy_candidates"] = self.strategy_files
        return self.findings

    def _find_python_files(self):
        """Collect all .py files recursively."""
        self.py_files = sorted(self.project_path.rglob("*.py"))

    def _analyse_files(self):
        """Parse each file with AST and score strategy relevance."""
        for py_file in self.py_files:
            try:
                score, details = self._score_file(py_file)
                if score > 0:
                    self.strategy_files.append({
                        "path": str(py_file.relative_to(self.project_path)),
                        "score": score,
                        "details": details,
                    })
            except SyntaxError:
                continue
            except Exception as e:
                logger.warning("Failed to parse %s: %s", py_file, e)

        # Sort by score descending
        self.strategy_files.sort(key=lambda x: x["score"], reverse=True)

    def _score_file(self, file_path: Path) -> tuple:
        """Score a file's likelihood of containing strategy logic (0-100)."""
        score = 0
        details = {
            "imports": [],
            "constants": {},
            "functions": [],
            "classes": [],
            "trading_terms": 0,
        }

        source = file_path.read_text(encoding="utf-8", errors="ignore")

        # 1. Filename bonus
        name_lower = file_path.stem.lower()
        for pattern in STRATEGY_FILE_PATTERNS:
            if pattern in name_lower:
                score += 10

        # 2. AST parse
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return 0, details

        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    details["imports"].append(alias.name)
                    self.findings["imports"].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                details["imports"].append(module)
                self.findings["imports"].add(module)

            # Constants (top-level assignments with numbers/strings)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # Check if value is a number
                        if isinstance(node.value, (ast.Num, ast.Constant)):
                            val = node.value.n if isinstance(node.value, ast.Num) else node.value.value
                            if isinstance(val, (int, float)):
                                details["constants"][name] = val
                                self.findings["constants"][name] = val
                                # Bonus for capital/lot/SL constants
                                if any(k in name.lower() for k in ["capital", "lot", "sl", "stop", "target", "premium"]):
                                    score += 5

            # Functions
            elif isinstance(node, ast.FunctionDef):
                details["functions"].append(node.name)
                if any(k in node.name.lower() for k in ["backtest", "strategy", "signal", "entry", "exit", "trade"]):
                    score += 8

            # Classes
            elif isinstance(node, ast.ClassDef):
                details["classes"].append(node.name)
                if any(k in node.name.lower() for k in ["strategy", "algo", "bot", "trader"]):
                    score += 5

        # 3. Raw text keyword matching
        source_lower = source.lower()
        term_count = 0
        for term in TRADING_KEYWORDS:
            count = source_lower.count(term)
            if count > 0:
                term_count += count
                score += min(count, 5)  # cap per term

        details["trading_terms"] = term_count

        # Cap score at 100
        score = min(score, 100)
        return score, details

    def get_top_candidate(self) -> Optional[str]:
        """Return path of highest-scoring strategy file."""
        if self.strategy_files:
            return str(self.project_path / self.strategy_files[0]["path"])
        return None

    def print_summary(self):
        """Print scan results to console."""
        print(f"\n{'='*60}")
        print(f"Project: {self.findings['project_name']}")
        print(f"Python files found: {self.findings['total_py_files']}")
        print(f"Strategy candidates: {len(self.findings['strategy_candidates'])}")
        print(f"\nTop candidates:")
        for i, cand in enumerate(self.findings['strategy_candidates'][:5], 1):
            print(f"  {i}. {cand['path']} (score: {cand['score']})")
        print(f"\nConstants detected: {list(self.findings['constants'].keys())[:10]}")
        print(f"{'='*60}")
