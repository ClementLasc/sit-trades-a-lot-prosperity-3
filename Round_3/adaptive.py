# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 22:23:06 2025

@author: spodd
"""

from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List, Dict, Any
import jsonpickle
import json

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: Dict[Symbol, List[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )
        max_item_length = (self.max_log_length - base_length) // 3
        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )
        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> List[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: Dict[Symbol, Listing]) -> List[List[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])
        return compressed

    def compress_order_depths(self, order_depths: Dict[Symbol, OrderDepth]) -> Dict[Symbol, List[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]
        return compressed

    def compress_trades(self, trades: Dict[Symbol, List[Trade]]) -> List[List[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )
        return compressed

    def compress_observations(self, observations: Observation) -> List[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]
        return [observations.plainValueObservations, conversion_observations]

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
        return value[: max_length - 3] + "..."

logger = Logger()

class Trader:
    def __init__(self):
        self.traderData = {}
        # Only trade JAMS with a position limit of 350.
        self.params = {
            "DJEMBES": {
                "position_limit": 60  # Maximum absolute position.
            }
        }

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders: Dict[str, List[Order]] = {}
        conversions = 0
        product = "DJEMBES"

        if product not in state.order_depths:
            return orders, conversions, jsonpickle.encode(self.traderData)
            
        od = state.order_depths[product]
        if not od.buy_orders or not od.sell_orders:
            return orders, conversions, jsonpickle.encode(self.traderData)
        
        # Retrieve best bid and best ask prices.
        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        
        # Calculate the VWAP using both sides of the book.
        total_volume = 0
        total_value = 0
        for price, volume in od.buy_orders.items():
            total_volume += volume
            total_value += price * volume
        for price, volume in od.sell_orders.items():
            total_volume += volume
            total_value += price * volume

        if total_volume == 0:
            current_vwap = (best_bid + best_ask) / 2
        else:
            current_vwap = total_value / total_volume

        # --- Adaptive Price Statistics for the Last 100 Prices ---
        history_key = product + "_vwap_history"
        if history_key not in self.traderData:
            self.traderData[history_key] = []
        
        vwap_history = self.traderData[history_key]
        vwap_history.append(current_vwap)
        # Keep only the last 100 prices.
        if len(vwap_history) > 200:
            vwap_history = vwap_history[-200:]
        self.traderData[history_key] = vwap_history

        # Compute the average, maximum, and minimum from the last 100 VWAP values.
        avg_price = sum(vwap_history) / len(vwap_history)
        max_price = max(vwap_history)
        min_price = min(vwap_history)
        price_range = max_price - min_price

        # Determine target position based on adaptive price statistics.
        if price_range == 0:
            target_position = 0  # Hold position if no variation.
        else:
            half_range = price_range / 2
            lower_bound = avg_price - half_range   # Fully long when current_vwap <= lower_bound.
            upper_bound = avg_price + half_range   # Fully short when current_vwap >= upper_bound.
            position_limit = self.params[product]["position_limit"]

            # Use a step function with 10 steps between fully long and fully short.
            Nsteps = 10

            if current_vwap <= lower_bound:
                target_position = position_limit
            elif current_vwap >= upper_bound:
                target_position = -position_limit
            else:
                step_size_price = (upper_bound - lower_bound) / (Nsteps - 1)
                step = int((current_vwap - lower_bound) // step_size_price)
                target_position = position_limit - ((2 * position_limit) * step / (Nsteps - 1))
                target_position = int(round(target_position))

        # Get the current position and compute the required change.
        current_position = state.position.get(product, 0)
        delta = target_position - current_position

        orders[product] = []
        if delta != 0:
            if delta > 0:
                # Increase long position by buying at the best bid.
                orders[product].append(Order(product, int(best_bid), delta))
            else:
                # Increase short position by selling at the best ask.
                orders[product].append(Order(product, int(best_ask), delta))
        
        trader_data_out = jsonpickle.encode(self.traderData)
        logger.flush(state, orders, conversions, trader_data_out)
        return orders, conversions, trader_data_out
