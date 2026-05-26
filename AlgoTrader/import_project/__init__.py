"""
AlgoTrader — Project Import & Analysis Module
Analyse any Nifty option trading project, extract strategy logic,
normalize to AlgoBase, and backtest/compare with existing algos.
"""
from .scanner import ProjectScanner
from .extractor import StrategyExtractor
from .normalizer import AlgoNormalizer
from .backtest_wrapper import compare_imported

__all__ = [
    "ProjectScanner",
    "StrategyExtractor",
    "AlgoNormalizer",
    "compare_imported",
]
