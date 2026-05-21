# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 22:23:06 2025

Stepwise Conversion Strategy Without Flattening.
Positions are maintained as determined by a stepwise function of the mispricing delta.
The target position for each basket (and the corresponding component targets) are computed,
and orders are issued to move the current position toward the target.

Products and fixed conversion ratios:
  PICNIC_BASKET1: 6 CROISSANTS, 3 JAMS, 1 DJEMBES.
  PICNIC_BASKET2: 4 CROISSANTS, 2 JAMS.

Thresholds:
  PICNIC_BASKET1: 20 points.
  PICNIC_BASKET2: 12 points.

Position limits:
  CROISSANTS: 250, JAMS: 350, DJEMBES: 60,
  PICNIC_BASKET1: 60, PICNIC_BASKET2: 100.

Conversion observation data is used to compute an effective mid price.
Positions are not flattened to 0—they are maintained as per the stepwise targets,
and orders adjust only the delta when the mispricing changes.

@author: spodd
"""

import math
from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List, Dict, Any
import jsonpickle
import json

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str=" ", end: str="\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: Dict[Symbol, List[Order]], 
              conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders), conversions, "", ""
        ]))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders), conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length)
        ]))
        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> List[Any]:
        return [
            state.timestamp, trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations)
        ]

    def compress_listings(self, listings: Dict[Symbol, Listing]) -> List[List[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])
        return compressed

    def compress_order_depths(self, order_depths: Dict[Symbol, OrderDepth]) -> Dict[Symbol, List[Any]]:
        compressed = {}
        for symbol, od in order_depths.items():
            compressed[symbol] = [od.buy_orders, od.sell_orders]
        return compressed

    def compress_trades(self, trades: Dict[Symbol, List[Trade]]) -> List[List[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append([
                    trade.symbol, trade.price, trade.quantity,
                    trade.buyer, trade.seller, trade.timestamp
                ])
        return compressed

    def compress_observations(self, observations: Observation) -> List[Any]:
        conv_obs = {}
        for product, obs in observations.conversionObservations.items():
            conv_obs[product] = [
                obs.bidPrice, obs.askPrice, obs.transportFees,
                obs.exportTariff, obs.importTariff, obs.sugarPrice,
                obs.sunlightIndex
            ]
        return [observations.plainValueObservations, conv_obs]

    def compress_orders(self, orders: Dict[Symbol, List[Order]]) -> List[List[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])
        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value
        return value[:max_length - 3] + "..."

logger = Logger()

class Trader:
    def __init__(self):
        self.traderData = {}
        # Define products, position limits, and thresholds.
        self.params = {
            "CROISSANTS":      { "position_limit": 250 },
            "JAMS":            { "position_limit": 350 },
            "DJEMBES":         { "position_limit": 60 },
            "PICNIC_BASKET1":  { "position_limit": 60,  "conv_threshold": 10 },
            "PICNIC_BASKET2":  { "position_limit": 100, "conv_threshold": 5 }
        }

    def get_mid_price(self, od: OrderDepth) -> float:
        if od.buy_orders and od.sell_orders:
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            return (best_bid + best_ask) / 2
        return None

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders: Dict[str, List[Order]] = {}
        

        

        # --- Compute Target for PICNIC_BASKET1 ---
        target_basket1 = 0
        if ("PICNIC_BASKET1" in state.order_depths and
            "CROISSANTS" in state.order_depths and
            "JAMS" in state.order_depths and
            "DJEMBES" in state.order_depths):
            od_b1 = state.order_depths["PICNIC_BASKET1"]
            od_c = state.order_depths["CROISSANTS"]
            od_j = state.order_depths["JAMS"]
            od_d = state.order_depths["DJEMBES"]
            mid_b1 = self.get_mid_price(od_b1)
            mid_c = self.get_mid_price(od_c)
            mid_j = self.get_mid_price(od_j)
            mid_d = self.get_mid_price(od_d)
            if mid_b1 is not None and mid_c is not None and mid_j is not None and mid_d is not None:
                synthetic_b1 = 6 * mid_c + 3 * mid_j + 1 * mid_d
                diff_b1 = synthetic_b1 - mid_b1
                thresh_b1 = self.params["PICNIC_BASKET1"]["conv_threshold"]
                if diff_b1 > thresh_b1:
                    steps = math.floor(diff_b1 / (thresh_b1/4))
                    target_basket1 = min(steps, self.params["PICNIC_BASKET1"]["position_limit"])
                elif diff_b1 < -thresh_b1:
                    steps = math.floor(abs(diff_b1) / (thresh_b1/4))
                    target_basket1 = -min(steps, self.params["PICNIC_BASKET1"]["position_limit"])
                else:
                    target_basket1 = 0

        # --- Compute Target for PICNIC_BASKET2 ---
        target_basket2 = 0
        if ("PICNIC_BASKET2" in state.order_depths and
            "CROISSANTS" in state.order_depths and
            "JAMS" in state.order_depths):
            od_b2 = state.order_depths["PICNIC_BASKET2"]
            od_c = state.order_depths["CROISSANTS"]
            od_j = state.order_depths["JAMS"]
            mid_b2 = self.get_mid_price(od_b2)
            mid_c = self.get_mid_price(od_c)
            mid_j = self.get_mid_price(od_j)
            if mid_b2 is not None and mid_c is not None and mid_j is not None:
                synthetic_b2 = 4 * mid_c + 2 * mid_j
                diff_b2 = synthetic_b2 - mid_b2
                thresh_b2 = self.params["PICNIC_BASKET2"]["conv_threshold"]
                if diff_b2 > thresh_b2:
                    steps = math.floor(diff_b2 / (thresh_b2/4))
                    target_basket2 = min(steps, self.params["PICNIC_BASKET2"]["position_limit"])
                elif diff_b2 < -thresh_b2:
                    steps = math.floor(abs(diff_b2) / (thresh_b2/4))
                    target_basket2 = -min(steps, self.params["PICNIC_BASKET2"]["position_limit"])
                else:
                    target_basket2 = 0

        
        target_croissants = (-6 * target_basket1) + (-4 * target_basket2)
        target_jams       = (-3 * target_basket1) + (-2 * target_basket2)
        target_djembes    = -1 * target_basket1  
        assets_targets = {
            "PICNIC_BASKET1": target_basket1,
            "PICNIC_BASKET2": target_basket2,
            "CROISSANTS":      target_croissants,
            "JAMS":            target_jams,
            "DJEMBES":         target_djembes
        }

        for asset, target in assets_targets.items():
            if asset in state.order_depths:
                current = state.position.get(asset, 0)
                delta = target - current
                if delta != 0:
                    od = state.order_depths[asset]
                    price = self.get_mid_price(od)
                    orders.setdefault(asset, [])
                    print(Order(asset, int(price), delta))
                    orders[asset].append(Order(asset, int(price), delta))
        
       
        trader_data_out = jsonpickle.encode(self.traderData)
        logger.flush(state, orders, 0, trader_data_out)
        return orders, 0, trader_data_out
