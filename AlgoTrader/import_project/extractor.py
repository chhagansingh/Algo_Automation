"""
StrategyExtractor — Extract entry/exit/SL logic from Python source code.
"""
import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = __import__("logging").getLogger(__name__)


class StrategyExtractor:
    """
    Reads a strategy file and extracts structured information:
    - Entry conditions (when to open a trade)
    - Exit conditions (when to close a trade)
    - Stop loss / target levels
    - Position sizing / lot size
    - Constants / parameters
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text(encoding="utf-8", errors="ignore")
        self.tree = None
        try:
            self.tree = ast.parse(self.source)
        except SyntaxError as e:
            logger.error("Syntax error in %s: %s", file_path, e)

        self.extracted: Dict[str, Any] = {
            "file": str(self.file_path),
            "constants": {},
            "entry_logic": [],
            "exit_logic": [],
            "stop_loss": None,
            "target": None,
            "position_sizing": None,
            "indicators_used": [],
            "timeframe": "1d",  # default
            "strategy_type": "unknown",
        }

    def extract(self) -> Dict[str, Any]:
        """Run full extraction."""
        if self.tree is None:
            return self.extracted

        self._extract_constants()
        self._detect_strategy_type()
        self._extract_conditions()
        self._extract_functions()
        return self.extracted

    def _extract_constants(self):
        """Pull all top-level numeric/string constants."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if isinstance(node.value, (ast.Num, ast.Constant)):
                            val = node.value.n if isinstance(node.value, ast.Num) else node.value.value
                            self.extracted["constants"][name] = val

    def _detect_strategy_type(self):
        """Guess if strategy is straddle, directional, IC, etc."""
        src_lower = self.source.lower()
        scores = {
            "short_straddle": src_lower.count("straddle") + src_lower.count("sell ce") + src_lower.count("sell pe"),
            "directional_buy": src_lower.count("buy ce") + src_lower.count("buy pe") + src_lower.count("directional"),
            "iron_condor": src_lower.count("iron condor") + src_lower.count("condor"),
            "ema_crossover": src_lower.count("ema") + src_lower.count("crossover"),
            "rsi_based": src_lower.count("rsi") + src_lower.count("overbought") + src_lower.count("oversold"),
            "range_based": src_lower.count("daily range") + src_lower.count("range") + src_lower.count("threshold"),
        }
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            self.extracted["strategy_type"] = best

        # Detect indicators
        indicators = []
        for ind in ["ema", "sma", "rsi", "macd", "adx", "atr", "bollinger", "vwap", "volume"]:
            if ind in src_lower:
                indicators.append(ind.upper())
        self.extracted["indicators_used"] = indicators

    def _extract_conditions(self):
        """Find if/elif conditions that likely control entry/exit."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.If):
                # Convert if-condition to string
                cond_str = ast.unparse(node) if hasattr(ast, "unparse") else ""
                if not cond_str:
                    continue

                cond_lower = cond_str.lower()
                # Entry conditions
                if any(k in cond_lower for k in ["entry", "signal", "buy", "sell", "eligible", "trade"]):
                    self.extracted["entry_logic"].append(cond_str[:200])

                # Exit conditions
                if any(k in cond_lower for k in ["exit", "close", "stop", "target", "sl_hit"]):
                    self.extracted["exit_logic"].append(cond_str[:200])

    def _extract_functions(self):
        """Look for key functions like get_signal, backtest, etc."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                name_lower = node.name.lower()
                if "stop" in name_lower or "sl" in name_lower:
                    # Try to extract SL value from function body
                    self._extract_sl_from_func(node)
                if "target" in name_lower:
                    self._extract_target_from_func(node)
                if "lot" in name_lower or "size" in name_lower or "capital" in name_lower:
                    self._extract_sizing_from_func(node)

    def _extract_sl_from_func(self, func_node: ast.FunctionDef):
        """Try to find a numeric stop loss in a function."""
        for child in ast.walk(func_node):
            if isinstance(child, ast.Num):
                val = child.n
                if 10 < val < 5000:  # plausible SL range in points or rupees
                    self.extracted["stop_loss"] = val
                    break
            elif isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                val = child.value
                if 10 < val < 5000:
                    self.extracted["stop_loss"] = val
                    break

    def _extract_target_from_func(self, func_node: ast.FunctionDef):
        """Try to find target value."""
        for child in ast.walk(func_node):
            if isinstance(child, ast.Num):
                val = child.n
                if 10 < val < 10000:
                    self.extracted["target"] = val
                    break
            elif isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                val = child.value
                if 10 < val < 10000:
                    self.extracted["target"] = val
                    break

    def _extract_sizing_from_func(self, func_node: ast.FunctionDef):
        """Try to find lot size or capital."""
        for child in ast.walk(func_node):
            if isinstance(child, ast.Num):
                val = child.n
                if val in [25, 50, 75, 100, 15, 30]:  # common lot sizes
                    self.extracted["position_sizing"] = val
                    break
            elif isinstance(child, ast.Constant) and isinstance(child.value, int):
                val = child.value
                if val in [25, 50, 75, 100, 15, 30]:
                    self.extracted["position_sizing"] = val
                    break

    def print_summary(self):
        """Print extraction results."""
        e = self.extracted
        print(f"\n{'='*60}")
        print(f"Extracted from: {e['file']}")
        print(f"Strategy type: {e['strategy_type']}")
        print(f"Indicators: {', '.join(e['indicators_used']) or 'None'}")
        print(f"Constants: {e['constants']}")
        print(f"Stop Loss: {e['stop_loss']}")
        print(f"Target: {e['target']}")
        print(f"Position Size: {e['position_sizing']}")
        print(f"Entry conditions found: {len(e['entry_logic'])}")
        print(f"Exit conditions found: {len(e['exit_logic'])}")
        print(f"{'='*60}")
