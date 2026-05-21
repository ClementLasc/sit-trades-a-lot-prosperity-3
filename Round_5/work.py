# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 01:00:42 2025

@author: spodd
"""


import math
from datamodel import ConversionObservation, OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder, UserId
from typing import List, Dict, Any, Optional, Tuple
import json
import jsonpickle
import bisect

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(
        self,
        state: TradingState,
        orders: Dict[Symbol, List[Order]],
        conversions: int,
        trader_data: str
    ) -> None:
        base_length = len(
            self.to_json([
                self.compress_state(state, ""),
                self.compress_orders(orders),
                conversions,
                "",
                ""
            ])
        )
        max_item_length = (self.max_log_length - base_length) // 3
        print(
            self.to_json([
                self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                self.compress_orders(orders),
                conversions,
                self.truncate(trader_data, max_item_length),
                self.truncate(self.logs, max_item_length)
            ])
        )
        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> List[Any]:
        return [
            state.timestamp,
            trader_data,
            [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
            {sym: [od.buy_orders, od.sell_orders] for sym, od in state.order_depths.items()},
            [], [],
            state.position,
            self.compress_observations(state.observations)
        ]

    def compress_observations(self, observations: Observation) -> List[Any]:
        convs = {
            prod: [obs.bidPrice, obs.askPrice, obs.transportFees,
                   obs.exportTariff, obs.importTariff,
                   obs.sugarPrice, obs.sunlightIndex]
            for prod, obs in observations.conversionObservations.items()
        }
        return [observations.plainValueObservations, convs]

    def compress_orders(self, orders: Dict[Symbol, List[Order]]) -> List[List[Any]]:
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",",":"))

    def truncate(self, value: str, max_length: int) -> str:
        return value if len(value) <= max_length else value[:max_length-3] + "..."

logger = Logger()

class OwnTrade:
    def __init__(self, symbol: Symbol, price: int, quantity: int, counter_party: UserId = None) -> None:
        self.symbol = symbol
        self.price: int = price
        self.quantity: int = quantity
        self.counter_party = counter_party
class Trader:
    def __init__(self) -> None:
        # Market data history (still useful for underlying price)
        self.last_mid: Dict[Symbol, float] = {}
        self.last_trade_price: Dict[Symbol, int] = {}
        # Config
        self.POSITION_LIMIT = 200
        self.ORDER_SIZE = 15
        
        self.INTRINSIC_SPREAD_WIDTH = 1
       

    VOUCHERS = [
        "VOLCANIC_ROCK_VOUCHER_9500", "VOLCANIC_ROCK_VOUCHER_9750",
        "VOLCANIC_ROCK_VOUCHER_10000", "VOLCANIC_ROCK_VOUCHER_10250",
        "VOLCANIC_ROCK_VOUCHER_10500",
    ]
    UNDERLYING = "VOLCANIC_ROCK"

    # --- Market Data Helpers ---
    @staticmethod
    def _get_best_bid(od: OrderDepth) -> Optional[int]: return max(od.buy_orders.keys()) if od.buy_orders else None
    @staticmethod
    def _get_best_ask(od: OrderDepth) -> Optional[int]: return min(od.sell_orders.keys()) if od.sell_orders else None
    @staticmethod
    def _get_mid_price(od: OrderDepth) -> Optional[float]:
        b = Trader._get_best_bid(od); a = Trader._get_best_ask(od)
        # Let's return mid even if spread is wide, for underlying estimation
        if b is not None and a is not None: return (b + a) / 2.0
        if b is not None: return float(b) # Fallback to bid
        if a is not None: return float(a) # Fallback to ask
        return None

    def _update_market_data(self, state: TradingState):
        """Update history for relevant symbols."""
        symbols_to_update = self.VOUCHERS + [self.UNDERLYING]
        for sym in symbols_to_update:
            od = state.order_depths.get(sym)
            if od:
                 # Update last mid price if calculable
                 mid = self._get_mid_price(od)
                 if mid is not None: self.last_mid[sym] = mid
            # Update last trade price
            market_trades_for_sym = state.market_trades.get(sym, [])
            if market_trades_for_sym:
                self.last_trade_price[sym] = market_trades_for_sym[-1].price

    def _get_underlying_price(self, state: TradingState) -> Optional[float]:
        """Gets the best estimate for the underlying price."""
        sym = self.UNDERLYING
        od = state.order_depths.get(sym)
        if od:
            mid = self._get_mid_price(od)
            if mid is not None: return mid
        # Fallback logic
        if sym in self.last_mid: return self.last_mid[sym]
        if sym in self.last_trade_price: return float(self.last_trade_price[sym])
        logger.print(f"WARN: No reliable underlying price found for {sym}")
        return None

    # --- Intrinsic Value Calculation ---
    def _calculate_intrinsic_value(
        self, S: float, K: int
    ) -> float:
        
        return max(0.0, S - K)
        
     

    # --- run Method using Intrinsic Value ---
    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        orders_to_submit: Dict[Symbol, List[Order]] = {}
        conversions = 0

        # 1. Update market data (especially Underlying)
        self._update_market_data(state)

        # 2. Get current underlying price
        underlying_price = self._get_underlying_price(state)
        if underlying_price is None:
            logger.print("WARN: Cannot get underlying price. Sending no orders.")
            # Return empty orders, effectively cancelling everything
            for sym in self.VOUCHERS: orders_to_submit[sym] = []
            logger.flush(state, orders_to_submit, conversions, jsonpickle.encode({}))
            return orders_to_submit, conversions, jsonpickle.encode({})

        logger.print(f"Underlying Price Estimate: {underlying_price:.2f}")

        # 3. Determine target orders based on intrinsic value
        for sym in self.VOUCHERS:
            target_orders_for_sym: List[Order] = []
            current_pos = state.position.get(sym, 0)

            try:
                strike_price = int(sym.split('_')[-1])
            except ValueError:
                logger.print(f"WARN: Cannot parse strike from symbol {sym}")
                orders_to_submit[sym] = []
                continue # Skip this symbol

            # Calculate intrinsic value (assuming zero time value)
            intrinsic_value = self._calculate_intrinsic_value(
                underlying_price, strike_price
            )
            logger.print(f"Symbol: {sym}, Strike: {strike_price}, Intrinsic Value : {intrinsic_value:.2f}")

           
            target_bid_price = math.floor(intrinsic_value - self.INTRINSIC_SPREAD_WIDTH)
            target_ask_price = math.ceil(intrinsic_value + self.INTRINSIC_SPREAD_WIDTH)

            # Ensure bid price is not negative
            target_bid_price = max(0, target_bid_price)
            
            if target_ask_price <= target_bid_price:
                 target_ask_price = target_bid_price + 1 # Minimum 1 tick spread

            # Place Bid
            can_buy_qty = self.POSITION_LIMIT - current_pos
            order_qty_bid = min(self.ORDER_SIZE, can_buy_qty)
            if order_qty_bid > 0:
                 logger.print(f"Intrinsic MM BID: {sym} {order_qty_bid} @ {target_bid_price}")
                 target_orders_for_sym.append(Order(sym, target_bid_price, order_qty_bid))

            # Place Ask
            can_sell_qty = self.POSITION_LIMIT + current_pos
            order_qty_ask = min(self.ORDER_SIZE, can_sell_qty)
            if order_qty_ask > 0:
                 logger.print(f"Intrinsic MM ASK: {sym} {-order_qty_ask} @ {target_ask_price}")
                 target_orders_for_sym.append(Order(sym, target_ask_price, -order_qty_ask))

           

            orders_to_submit[sym] = target_orders_for_sym

        # 4. Return orders
        trader_data = jsonpickle.encode({})
        logger.flush(state, orders_to_submit, conversions, trader_data)
        return orders_to_submit, conversions, trader_data