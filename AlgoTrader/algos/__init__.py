from .base import AlgoBase
from .algo1_rd_straddle import Algo1RDStraddle
from .algo2_ntb_scenb import Algo2NTBScenB
from .algo3_niftybot_ema import Algo3NiftyBotEMA
from .algo4_flow_nifty import Algo4FlowNifty
from .algo5_vix_reversion import Algo5VIXReversion
from .algo6_supertrend_spread import Algo6SuperTrendSpread
from .algo7_dual_thrust import Algo7DualThrust
from .algo8_cpma_scalper import Algo8CPMAScalper
from .algo9_bullish_scanner import Algo9BullishScanner
from .algo10_awesome_oscillator import Algo10AwesomeOscillator
from .algo11_gamma_scalping import Algo11GammaScalping
from .algo12_dip_recovery import Algo12DipRecovery
from .algo13_signal_rolling import Algo13SignalRolling
from .algo14_ml_rf import Algo14MLRF
from .algo15_aggregate_score import Algo15AggregateScore
from .algo16_nifty_scalper_4of5 import Algo16NiftyScalper45
from .algo17_nifty_scalper_3of5 import Algo17NiftyScalper35

ALGO_MAP = {
    "algo1": Algo1RDStraddle,
    "algo2": Algo2NTBScenB,
    "algo3": Algo3NiftyBotEMA,
    "algo4": Algo4FlowNifty,
    "algo5": Algo5VIXReversion,
    "algo6": Algo6SuperTrendSpread,
    "algo7": Algo7DualThrust,
    "algo8": Algo8CPMAScalper,
    "algo9": Algo9BullishScanner,
    "algo10": Algo10AwesomeOscillator,
    "algo11": Algo11GammaScalping,
    "algo12": Algo12DipRecovery,
    "algo13": Algo13SignalRolling,
    "algo14": Algo14MLRF,
    "algo15": Algo15AggregateScore,
    "algo16": Algo16NiftyScalper45,
    "algo17": Algo17NiftyScalper35,
}

def get_algo(algo_id: str) -> AlgoBase:
    cls = ALGO_MAP.get(algo_id)
    if not cls:
        raise ValueError(f"Unknown algo_id: {algo_id}")
    return cls()
