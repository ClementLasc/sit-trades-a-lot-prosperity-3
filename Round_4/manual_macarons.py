import json
import math
import jsonpickle
from typing import Any, Dict, List, Tuple

import numpy as np
from datamodel import (
    ConversionObservation,
    OrderDepth,
    Order,
    ProsperityEncoder,
    TradingState,
)

# ----------------
# Logger
# ----------------
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(
        self,
        state: TradingState,
        orders: Dict[str, List[Order]],
        conversions: int,
        trader_data: str,
    ) -> None:
        payload = [
            state.timestamp,
            self.compress_state(state),
            self.compress_orders(orders),
            conversions,
            self.truncate(self.logs, self.max_log_length)
        ]
        print(json.dumps(payload, cls=ProsperityEncoder, separators=(",",":")))
        self.logs = ""

    def compress_state(self, state: TradingState) -> list:
        return [
            state.timestamp,
            state.traderData or "",
            [],
            {s: [od.buy_orders, od.sell_orders] for s, od in state.order_depths.items()},
            [], [], state.position, []
        ]

    def compress_orders(self, orders: Dict[str, List[Order]]) -> list:
        out = []
        for arr in orders.values():
            for o in arr:
                out.append([o.symbol, o.price, o.quantity])
        return out

    def truncate(self, v: str, n: int) -> str:
        return v if len(v) <= n else v[:n-3] + "..."

logger = Logger()

# ----------------
# Product & Params
# ----------------
class Product:
    MAGNIFICENT_MACARONS = "MAGNIFICENT_MACARONS"

# execution hyperparameters
PARAMS = {
    Product.MAGNIFICENT_MACARONS: {
        "position_limit": 75,
        "step_size": 50,
        "base_unit": 25,
        "min_diff": 0
    }
}

# ----------------
# Trader using numpy-only model
# ----------------
class Trader:
    def __init__(self, params: Dict[str, Dict[str,int]] = None):
        self.params = params or PARAMS
        # precomputed model parameters (from offline fit)
        self.feature_order = [
            'transportFees', 'exportTariff',
            'importTariff', 'sugarPrice',
            'sunlightIndex'
        ]
        # means and scales from training data
        self.means = np.array([  1.57758667,  10.1648    ,  -3.67778333,
                                 202.20190148,  55.16741833])
        self.scales = np.array([  0.37497508,   0.68696746,   1.11103619,
                                   6.70773034,  10.32694038])
        self.coeffs = np.array([ 23.23821456, -42.95540902, -58.1737163 ,
                                 33.57696841, -33.99760245])
        self.intercept = 663.7679588950559

    def _get_features(self, obs: ConversionObservation) -> np.ndarray:
        return np.array([
            obs.transportFees,
            obs.exportTariff,
            obs.importTariff,
            obs.sugarPrice,
            obs.sunlightIndex
        ], dtype=float)

    def _predict(self, features: np.ndarray) -> float:
        scaled = (features - self.means) / self.scales
        return float(np.dot(scaled, self.coeffs) + self.intercept)

    def _get_best_bid(self, od: OrderDepth) -> float:
        return max(od.buy_orders.keys()) if od.buy_orders else 0.0

    def _get_best_ask(self, od: OrderDepth) -> float:
        return min(od.sell_orders.keys()) if od.sell_orders else float('inf')

    def _handle_macarons_stat_arb(
        self,
        state: TradingState
    ) -> Tuple[List[Order], int]:
        prod = Product.MAGNIFICENT_MACARONS
        od   = state.order_depths.get(prod)
        obs  = state.observations.conversionObservations.get(prod)
        if not od or not obs or not od.buy_orders or not od.sell_orders:
            return [], 0

        cfg = self.params[prod]
        feats = self._get_features(obs)
        fair_value = self._predict(feats)

        bid = self._get_best_bid(od)
        ask = self._get_best_ask(od)
        mid = (bid + ask) / 2.0
        diff = mid - fair_value

        # apply min_diff
        if abs(diff) < cfg['min_diff']:
            return [], 0

        # sizing
        curr_pos = state.position.get(prod, 0)
        steps    = math.floor(abs(diff) / cfg['step_size'])
        direction = -1 if diff > 0 else 1
        target   = direction * min((steps+1)*cfg['base_unit'], cfg['position_limit'])
        delta    = target - curr_pos
        if delta == 0:
            return [], 0

        # price for execution
        price = int(bid + 1 if delta > 0 else ask - 1)
        logger.print(f"[MAC] fv={fair_value:.1f} mid={mid:.1f} diff={diff:.1f} tgt={target} curr={curr_pos}")
        return [Order(prod, price, int(delta))], 0

    def run(
        self,
        state: TradingState
    ) -> Tuple[Dict[str, List[Order]], int, str]:
        orders, conv = {}, 0
        mac_orders, conv = self._handle_macarons_stat_arb(state)
        for o in mac_orders:
            orders.setdefault(o.symbol, []).append(o)
        data = jsonpickle.encode({}, unpicklable=False)
        logger.flush(state, orders, conv, data)
        traderData = self.save_state() 
        
        logger.flush(state, result, self.conversions, traderData)
        return result, self.conversions, traderData

