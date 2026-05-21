from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List, Dict, Any
from statistics import mean
import json
from typing import Any
import jsonpickle
import math

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
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

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
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

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
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

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])
        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]
        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
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

    def compress_observations(self, observations: Observation) -> list[Any]:
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

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
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

class Product:
    RAINFOREST_RESIN = "RAINFOREST_RESIN"
    KELP = "KELP"
    SQUID_INK = "SQUID_INK"
    DJEMBES = "DJEMBES"
    CROISSANTS= "CROISSANTS"
    JAMS = "JAMS"
    PICNIC_BASKET1 = "PICNIC_BASKET1"
    PICNIC_BASKET2 = "PICNIC_BASKET2"

PARAMS = {
    Product.RAINFOREST_RESIN: {
        "position_limit": 50,
        "fair_value_method": "sma",
        "sma_lookback": 10,         
        "sma_default_price": 10000,
        "take_enabled": True,
        "take_width": 0,
        "make_enabled": True,
        "quote_volume": 10,
        "disregard_edge": 1,
        "join_edge": 0,
        "default_edge": 0,
    },
    Product.KELP: {
        "position_limit": 50,
        "fair_value_method": "vwap_ema",
        "vwap_default_price": 2023, 
        "ema_alpha": 0.22,
        "take_enabled": True,
        "take_width": 0,
        "make_enabled": True,
        "quote_volume": 15,
        "disregard_edge": 1,
        "join_edge": 0,
        "default_edge": 1,
    },
    Product.SQUID_INK: {
        "position_limit": 50,
        "fair_value_method": "sma",
        "vwap_default_price": 1974,
        "sma_lookback": 5,
        "sma_default_price": 1974,
        "take_enabled": False,
        "take_width": 5,
        "make_enabled": True,
        "quote_volume": 3,
        "disregard_edge": 1,
        "join_edge": 0,
        "default_edge": 3,
    },
    Product.DJEMBES: {
        "position_limit": 60,
        "fair_value_method": "vwap",
        "sma_lookback": 8,
        "sma_default_price": 10000,
        "vwap_default_price": 10000,
        "take_enabled": False,
        "take_width": 0,
        "make_enabled": False,
        "quote_volume": 10,
        "disregard_edge": 1,
        "join_edge": 0,
        "default_edge": 0,
    },
    Product.CROISSANTS: {
        "position_limit": 250,
    },
    Product.JAMS : {
        "position_limit": 350,
    },
    Product.PICNIC_BASKET1 : {
        "position_limit": 60,
        "fair_value_method": "vwap",
        "vwap_default_price": 3000,
        "take_enabled": True,
        "take_width": 0,
        "make_enabled": True,
        "quote_volume": 10,
        "disregard_edge": 1,
        "join_edge": 0,
        "default_edge": 0,
    },
    Product.PICNIC_BASKET2: {
        "position_limit": 100,
        "fair_value_method": "vwap",
        "vwap_default_price": 10000,
    }
}

class Trader:
    def __init__(self, params=None):
        self.params = params if params is not None else PARAMS
        self.traderObject = {
            "historical_prices": {},
            "ema_state": {},
        }
        # Pivot table for DJEMBES (existing)
        self.djembe_pivot_table = {
            (-0.50, -0.40): -8.06e-06,
            (-0.40, -0.30): 4.29e-06,
            (-0.30, -0.20): 3.85e-06,
            (-0.20, -0.10): 2.23e-06,
            (-0.10,  0.00): 3.90e-06,
            ( 0.00,  0.10): -2.00e-06,
            ( 0.10,  0.20): 5.64e-06,
            ( 0.20,  0.30): 1.00e-06,
        }
        self.pb1_pivot_table = {
            (-5.57, -4.57): -0.000196426,
            (-4.57, -3.57): -2.51055e-06,
            (-3.57, -2.57): -0.00124109,
            (-2.57, -1.57): 0.00766911,
            (-1.57, -0.57): 0.00375929,
            (-0.57,  0.57): -0.00298311,
            ( 0.57,  1.57): 0.00030627,
            ( 1.57,  2.57): 0.00099022,
            ( 2.57,  3.57): -0.00345678,
            ( 3.57,  4.57): 0.00123456,
        }
        self.return_threshold = 1e-6


    def load_state(self, state: TradingState):
        if state.traderData != None and state.traderData != "":
            try:
                self.traderObject = jsonpickle.decode(state.traderData)
                self.traderObject.setdefault("historical_prices", {})
                self.traderObject.setdefault("ema_state", {})
            except Exception as e:
                print(f"Error loading traderData: {e}")
                self.traderObject = {
                    "historical_prices": {},
                    "ema_state": {},
                }

    def save_state(self) -> str:
        state_to_save = {
            "historical_prices": self.traderObject["historical_prices"],
            "ema_state": self.traderObject["ema_state"],
        }
        return jsonpickle.encode(state_to_save)

    def update_trader_state(self, product: str, order_depth: OrderDepth):
        params = self.params[product]
        if params["fair_value_method"] == "sma":
            hist_prices = self.traderObject["historical_prices"].setdefault(product, [])
            if order_depth.buy_orders and order_depth.sell_orders:
                mid_price = (max(order_depth.buy_orders.keys()) + min(order_depth.sell_orders.keys())) / 2
                hist_prices.append(mid_price)
                max_history = params.get("sma_lookback", 10) + 5
                self.traderObject["historical_prices"][product] = hist_prices[-max_history:]

    #
    # --- Pivot Helpers ---
    #
    def get_pivot_bin(self, diff: float, pivot_table: Dict) -> Any:
        for (low, high), avg_ret in pivot_table.items():
            if low <= diff < high:
                return (low, high, avg_ret)
        return None

    def _get_mid_price(self, product: str, state: TradingState) -> float | None:
        if product not in state.order_depths:
            return None
        od = state.order_depths[product]
        if od.buy_orders and od.sell_orders:
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            if best_ask > best_bid:
                return (best_bid + best_ask) / 2.0
            else:
                return float(best_bid)
        return None

    def _calculate_vwap(self, product: str, od: OrderDepth, min_volume_threshold: int = 3) -> float | None:
        filtered_bids = {p: v for p, v in od.buy_orders.items() if v >= min_volume_threshold}
        filtered_asks = {p: v for p, v in od.sell_orders.items() if abs(v) >= min_volume_threshold}
        total_bid_val = sum(price * vol for price, vol in filtered_bids.items())
        total_bid_vol = sum(filtered_bids.values())
        total_ask_val = sum(price * abs(vol) for price, vol in filtered_asks.items())
        total_ask_vol = sum(abs(vol) for vol in filtered_asks.values())
        total_vol = total_bid_vol + total_ask_vol
        if total_vol == 0:
            return None
        return (total_bid_val + total_ask_val) / total_vol

    def _fair_value_vwap(self, product: str, order_depth: OrderDepth, params: Dict[str, Any]) -> float | None:
        vwap = self._calculate_vwap(product, order_depth)
        if vwap is not None:
            return vwap
        return params.get("vwap_default_price", 1000)

    def calculate_fair_value(self, product: str, order_depth: OrderDepth) -> float | None:
        params = self.params[product]
        method = params["fair_value_method"]
        if method == "sma":
            lookback = params["sma_lookback"]
            hist_prices = self.traderObject["historical_prices"].get(product, [])
            if len(hist_prices) >= lookback:
                return mean(hist_prices[-lookback:])
            else:
                return params.get("sma_default_price")
        elif method == "vwap_ema":
            return self._fair_value_vwap_ema(product, order_depth, params)
        elif method == "vwap":
            return self._fair_value_vwap(product, order_depth, params)
        else:
            print(f"Warning: Unknown fair_value_method '{method}' for {product}")
            return None

    def _fair_value_vwap_ema(self, product: str, order_depth: OrderDepth, params: Dict[str, Any]) -> float | None:
        current_vwap = self._calculate_vwap(product, order_depth)
        last_ema = self.traderObject.setdefault("ema_state", {}).get(product)
        alpha = params["ema_alpha"]
        default_price = params["vwap_default_price"]
        if current_vwap is None:
            return last_ema if last_ema is not None else default_price
        if last_ema is None:
            new_ema = current_vwap
        else:
            new_ema = alpha * current_vwap + (1 - alpha) * last_ema
        self.traderObject.setdefault("ema_state", {})[product] = new_ema
        return new_ema

    def trade_djembe_pivot(self, state: TradingState) -> List[Order]:
        orders: List[Order] = []
        product = Product.DJEMBES
        if product not in state.order_depths:
            logger.print("Order depth for DJEMBES not found.")
            return orders
        od = state.order_depths[product]
        self.update_trader_state(product, od)
        mid_price = self._get_mid_price(product, state)
        vwap = self._fair_value_vwap(product, od, self.params[product])
        if mid_price is None or vwap is None:
            logger.print("Insufficient price data for DJEMBES.")
            return orders
        diff = mid_price - vwap
        pivot = self.get_pivot_bin(diff, self.djembe_pivot_table)
        if pivot is None:
            logger.print(f"DJEMBES: diff {diff:.4f} not in any pivot bin.")
            return orders
        (bin_low, bin_high, avg_return) = pivot
        logger.print(f"[DJEMBES] mid: {mid_price:.2f}, vwap: {vwap:.2f}, diff: {diff:.4f}, bin: ({bin_low}, {bin_high}), avg_ret: {avg_return:.6f}")
        current_position = state.position.get(product, 0)
        pos_limit = self.params[product]["position_limit"]
        threshold = self.return_threshold
        trade_size = 10
        if avg_return > threshold and current_position < pos_limit:
            logger.print(f"Signal: Go LONG {product}.")
            orders.append(Order(product, int(mid_price), trade_size))
        elif avg_return < -threshold and current_position > -pos_limit:
            logger.print(f"Signal: Go SHORT {product}.")
            orders.append(Order(product, int(mid_price), -trade_size))
        else:
            logger.print(f"DJEMBES no trade: pivot_val={avg_return:.6f} / threshold={threshold:.6f}")
        return orders

    #
    # --- Pivot Trading Logic for PICNIC_BASKET1 (Appended) ---
    #
    def trade_pb1_pivot(self, state: TradingState) -> List[Order]:
        orders: List[Order] = []
        product = Product.PICNIC_BASKET1
        if product not in state.order_depths:
            logger.print("Order depth for PICNIC_BASKET1 not found.")
            return orders
        od = state.order_depths[product]
        self.update_trader_state(product, od)
        mid_price = self._get_mid_price(product, state)
        vwap = self._fair_value_vwap(product, od, self.params[product])
        if mid_price is None or vwap is None:
            logger.print("Insufficient price data for PICNIC_BASKET1.")
            return orders
        diff = mid_price - vwap
        pivot = self.get_pivot_bin(diff, self.pb1_pivot_table)
        if pivot is None:
            logger.print(f"PICNIC_BASKET1: diff {diff:.4f} not in any pivot bin.")
            return orders
        (bin_low, bin_high, avg_return) = pivot
        logger.print(f"[PB1] mid: {mid_price:.2f}, vwap: {vwap:.2f}, diff: {diff:.4f}, bin: ({bin_low}, {bin_high}), avg_ret: {avg_return:.6f}")
        current_position = state.position.get(product, 0)
        pos_limit = self.params[product]["position_limit"]
        threshold = self.return_threshold
        trade_size = 10
        if avg_return > threshold and current_position < pos_limit:
            logger.print("PB1 Signal: Go LONG.")
            orders.append(Order(product, int(mid_price), trade_size))
        elif avg_return < -threshold and current_position > -pos_limit:
            logger.print("PB1 Signal: Go SHORT.")
            orders.append(Order(product, int(mid_price), -trade_size))
        else:
            logger.print(f"PB1 no trade: pivot_val={avg_return:.6f} / threshold={threshold:.6f}")
        return orders

    #
    # --- (Optional) Market-Taking / Market-Making Logic ---
    #
    def generate_take_orders(self, product: str, od: OrderDepth, fair_value: float, position: int) -> List[Order]:
        orders: List[Order] = []
        params = self.params[product]
        pos_limit = params["position_limit"]
        take_width = params["take_width"]
        taker_volume_override = params.get("taker_volume")
        if od.sell_orders:
            best_ask = min(od.sell_orders.keys())
            best_ask_volume = abs(od.sell_orders[best_ask])
            if best_ask <= fair_value - take_width:
                max_can_buy = pos_limit - position
                if max_can_buy > 0:
                    vol_to_buy = taker_volume_override if taker_volume_override is not None else best_ask_volume
                    if product=="SQUID_INK":
                        quantity = 1
                    else:
                        quantity = int(min(vol_to_buy, max_can_buy))
                    if quantity > 0:
                        print(f"TAKE BUY {product}: {quantity}x {best_ask}")
                        orders.append(Order(product, best_ask, quantity))
        if od.buy_orders:
            best_bid = max(od.buy_orders.keys())
            best_bid_volume = od.buy_orders[best_bid]
            if best_bid >= fair_value + take_width:
                max_can_sell = position - (-pos_limit)
                if max_can_sell > 0:
                    vol_to_sell = taker_volume_override if taker_volume_override is not None else best_bid_volume
                    quantity = int(min(vol_to_sell, max_can_sell))
                    if quantity > 0:
                        print(f"TAKE SELL {product}: {quantity}x {best_bid}")
                        orders.append(Order(product, best_bid, -quantity))
        return orders

    def generate_make_orders(self, product: str, od: OrderDepth, fair_value: float, position: int) -> List[Order]:
        orders: List[Order] = []
        params = self.params[product]
        pos_limit = params["position_limit"]
        quote_volume = params["quote_volume"]
        disregard_edge = params["disregard_edge"]
        join_edge = params["join_edge"]
        default_edge = params["default_edge"]
        best_market_ask = min(od.sell_orders.keys()) if od.sell_orders else float('inf')
        best_market_bid = max(od.buy_orders.keys()) if od.buy_orders else 0
        asks_above_fair = [p for p in od.sell_orders if p > fair_value + disregard_edge]
        bids_below_fair = [p for p in od.buy_orders if p < fair_value - disregard_edge]
        best_ask_above_fair = min(asks_above_fair) if asks_above_fair else None
        best_bid_below_fair = max(bids_below_fair) if bids_below_fair else None
        my_ask_price = round(fair_value + default_edge)
        if best_ask_above_fair is not None:
            if abs(best_ask_above_fair - fair_value) <= join_edge:
                my_ask_price = best_ask_above_fair
            else:
                my_ask_price = best_ask_above_fair - 1
        my_bid_price = round(fair_value - default_edge)
        if best_bid_below_fair is not None:
            if abs(fair_value - best_bid_below_fair) <= join_edge:
                my_bid_price = best_bid_below_fair
            else:
                my_bid_price = best_bid_below_fair + 1
        my_bid_price = int(math.floor(my_bid_price))
        my_ask_price = int(math.ceil(my_ask_price))
        if my_bid_price >= my_ask_price:
            print(f"MAKE {product}: Skipping, calculated bid {my_bid_price} >= ask {my_ask_price}")
            return orders
        max_can_buy = pos_limit - position
        bid_quantity = int(min(quote_volume, max_can_buy))
        if bid_quantity > 0 and my_bid_price < best_market_ask:
            print(f"MAKE BID {product}: {bid_quantity}x {my_bid_price}")
            orders.append(Order(product, my_bid_price, bid_quantity))
        max_can_sell = position - (-pos_limit)
        ask_quantity = int(min(quote_volume, max_can_sell))
        if ask_quantity > 0 and my_ask_price > best_market_bid:
            print(f"MAKE ASK {product}: {ask_quantity}x {my_ask_price}")
            orders.append(Order(product, my_ask_price, -ask_quantity))
        return orders
    
    def _get_best_ask(self, product: str, state: TradingState) -> int | None:
         if product not in state.order_depths: return None
         order_depth = state.order_depths[product]
         if order_depth.sell_orders:
             return min(order_depth.sell_orders.keys())
         return None

    def _get_best_bid(self, product: str, state: TradingState) -> int | None:
         if product not in state.order_depths: return None
         order_depth = state.order_depths[product]
         if order_depth.buy_orders:
             return max(order_depth.buy_orders.keys())
         return None
    

    def trade_pb2_arbitrage_strategy(self, state: TradingState) -> List[Order]:
        
        orders: List[Order] = []
        pb2 = "PICNIC_BASKET2"
        croissant = "CROISSANTS"
        jam = "JAMS"
        pb2_pos_limit = self.params[pb2]["position_limit"]
        pb2_quote_volume = 2
        pb2_martingale_multiplier=1
        pb2_history_length=25
        pb2_spread_levels=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        pb2_exit_threshold = 1
        entry_threshold = 0

        # --- 1. Get Data & Parameters ---
        if pb2 not in state.order_depths or croissant not in state.order_depths or jam not in state.order_depths:
            logger.print("PB2 Arbitrage: Missing order depth for one or more products.")
            return orders


        mid_prices, best_asks, best_bids, prices_ok = {}, {}, {}, True
        for p in [pb2,croissant,jam]:
            mid, ask, bid = self._get_mid_price(p, state), self._get_best_ask(p, state), self._get_best_bid(p, state)
            mid_prices[p], best_asks[p], best_bids[p] = mid, ask, bid
            if mid is None or ask is None or bid is None: prices_ok = False
        
        
        croissant_price = mid_prices[croissant]
        jam_price = mid_prices[jam]
        pb2_price = self.calculate_fair_value(pb2, state.order_depths[pb2])


        bid_b2 = best_bids[pb2]
        jam_bid = best_bids[jam]
        croissant_bid = best_bids[croissant]

        ask_b2 = best_asks[pb2]
        jam_ask = best_asks[jam]
        croissant_ask = best_asks[croissant]

        



        if pb2_price is None or croissant_price is None or jam_price is None:
            logger.print("PB2 Arbitrage: Missing fair price for one or more products.")
            return orders


        # --- 2. Calculate Spread and Mean ---

        def _calculate_spread(p_pb2, p_croissant, p_jam):
            synthetic_basket_price = (4 * p_croissant) + (2 * p_jam)
            return p_pb2 - synthetic_basket_price

        current_spread = _calculate_spread(pb2_price, croissant_price, jam_price)

        if not hasattr(self, "pb2_historical_spreads") and not hasattr(self, "pb2_spread_position") and not hasattr(self, "pb2_short_entry_prices") and not hasattr(self, "pb2_long_entry_prices"):
                    self.pb2_historical_spreads= []
                    self.pb2_spread_position = 0
                    self.pb2_short_entry_prices = []
                    self.pb2_long_entry_prices = []
        self.pb2_historical_spreads.append(current_spread)
        if len(self.pb2_historical_spreads) > pb2_history_length:
            self.pb2_historical_spreads.pop(0) 
        
    

        logger.print(f"[PB2 Arb] Spread: {current_spread:.2f}, Position: {self.pb2_spread_position}")

       
        trade_executed_this_tick = False

       
        if current_spread > entry_threshold and self.pb2_spread_position >= 0: 
            for level in sorted(pb2_spread_levels, reverse=True):
                if current_spread > entry_threshold + level:
                    

                    target_short_pos_at_level = - (pb2_spread_levels.index(level) + 1) * pb2_quote_volume * pb2_martingale_multiplier
                    
                    # Check if we should increase short position
                    if self.pb2_spread_position > target_short_pos_at_level:
                        
                        qty_to_short = pb2_quote_volume * pb2_martingale_multiplier
                        
                        
                        if self.pb2_spread_position - qty_to_short >= -pb2_pos_limit:
                            logger.print(f"[PB2 Arb] Signal: Enter/Increase SHORT at spread {current_spread:.2f} (Level > {level:.2f})")
                            orders.append(Order(pb2, int(bid_b2), -qty_to_short))
                            orders.append(Order(croissant, int(croissant_ask), 4 * qty_to_short))
                            orders.append(Order(jam, int(jam_ask), 2 * qty_to_short))

                            
                            self.pb2_spread_position -= qty_to_short
                            self.pb2_short_entry_prices.append(current_spread) 
                            trade_executed_this_tick = True
                            break 
                    else:
                        
                         break 

        
        elif current_spread < -entry_threshold and self.pb2_spread_position <= 0: 
             
             for level in sorted(pb2_spread_levels):
                  if current_spread < -entry_threshold - level:
                      
                      target_long_pos_at_level = (pb2_spread_levels.index(level) + 1) * pb2_quote_volume * pb2_martingale_multiplier

                     
                      if self.pb2_spread_position < target_long_pos_at_level:
                          
                          qty_to_long = pb2_quote_volume * pb2_martingale_multiplier 
                          
                         
                          if self.pb2_spread_position + qty_to_long <= pb2_pos_limit:
                              logger.print(f"[PB2 Arb] Signal: Enter/Increase LONG at spread {current_spread:.2f} (Level < -{level:.2f})")
                              orders.append(Order(pb2, int(ask_b2), qty_to_long))
                              orders.append(Order(croissant, int(croissant_bid), -4 * qty_to_long))
                              orders.append(Order(jam, int(jam_bid), -2 * qty_to_long))

                              # Update persistent state
                              self.pb2_spread_position += qty_to_long
                              self.pb2_long_entry_prices.append(current_spread) # Track entry
                              trade_executed_this_tick = True
                              break 
                      else:
                          
                           break

        # --- 4. Exit Logic ---
       
        if not trade_executed_this_tick and abs(current_spread - entry_threshold) < pb2_exit_threshold:
            if self.pb2_spread_position > 0: 
                logger.print(f"[PB2 Arb] Signal: CLOSE LONG position ({self.pb2_spread_position}) at spread {current_spread:.2f}")
                orders.append(Order(pb2, int(bid_b2), -self.pb2_spread_position))
                orders.append(Order(croissant, int(croissant_ask), 4 * self.pb2_spread_position))
                orders.append(Order(jam, int(jam_ask), 2 * self.pb2_spread_position))
                # Reset state
                self.pb2_spread_position = 0
                self.pb2_long_entry_prices = []
                self.pb2_short_entry_prices = [] 

            elif self.pb2_spread_position < 0: 
                logger.print(f"[PB2 Arb] Signal: CLOSE SHORT position ({self.pb2_spread_position}) at spread {current_spread:.2f}")
                orders.append(Order(pb2, int(bid_b2), -self.pb2_spread_position))
                orders.append(Order(croissant, int(croissant_ask), 4 * self.pb2_spread_position)) 
                orders.append(Order(jam, int(jam_ask), 2 * self.pb2_spread_position)) 
                
                self.pb2_spread_position = 0
                self.pb2_long_entry_prices = []
                self.pb2_short_entry_prices = []

        # --- 5. Return Orders ---
        # Filter out zero quantity orders just in case
        final_orders = [o for o in orders if o.quantity != 0]
        return final_orders

    #
    # --- Main Execution Logic ---
    #
    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self.load_state(state)
        result: Dict[str, List[Order]] = {}
        conversions = 0
        traded_products = [
            Product.RAINFOREST_RESIN,
            Product.KELP,
            Product.SQUID_INK,
            Product.DJEMBES,
            Product.PICNIC_BASKET1
        ]
        arb_products = [
            Product.PICNIC_BASKET2,
            Product.CROISSANTS,
            Product.JAMS
        ]

        for product in arb_products:
            if product not in state.order_depths:
                print(f"No order depth for {product}, skipping.")
                continue
            if product not in self.params:
                print(f"No parameters found for {product}, skipping.")
                continue
            od: OrderDepth = state.order_depths[product]
            current_position = state.position.get(product, 0)
            params = self.params[product]
            product_orders_this_tick: List[Order] = []
            orders = self.trade_pb2_arbitrage_strategy(state)
            product_orders_this_tick.extend(orders)
            result[product] = product_orders_this_tick


        """ for product in traded_products:
            if product not in state.order_depths:
                print(f"No order depth for {product}, skipping.")
                continue
            if product not in self.params:
                print(f"No parameters found for {product}, skipping.")
                continue
            od: OrderDepth = state.order_depths[product]
            current_position = state.position.get(product, 0)
            params = self.params[product]
            product_orders_this_tick: List[Order] = []
            if product == "SQUID_INK":
                if not od.buy_orders or not od.sell_orders:
                    result[product] = []
                    continue

                # Calculate best bid & best ask, then mid-price
                best_bid = max(od.buy_orders.keys())
                best_ask = min(od.sell_orders.keys())
                mid_price = (best_bid + best_ask) / 2

                window = 20

                if not hasattr(self, "price_history"):
                    self.price_history = {}
                if product not in self.price_history:
                    self.price_history[product] = []
                self.price_history[product].append(mid_price)
                if len(self.price_history[product]) > window:  
                    self.price_history[product].pop(0)

                buy_z_threshold = 1.3
                sell_z_threshold = 1.7
                trade_volume = 7
                max_position = 50

                
                product_orders_this_tick = []
               
                
                if len(self.price_history[product]) >= window:
                    history = self.price_history[product]
                    mean_price = sum(history) / len(history)
                    variance = sum((p - mean_price) ** 2 for p in history) / len(history)
                    std_dev = variance ** 0.5 if variance > 0 else 1e-6  

                    z_score = (mid_price - mean_price) / std_dev
                    print(f"[Z-SCORE] {product} | z: {z_score:.2f} | Mid: {mid_price:.2f}, Mean: {mean_price:.2f}, Std: {std_dev:.2f}, Pos: {current_position}")

                    
                    if z_score < -buy_z_threshold and current_position < max_position:
                        volume = min(trade_volume, max_position - current_position)
                        if current_position < 0: #
                            buy_price = int(mid_price) 
                            print(f"AGGRESSIVE BUY to close short {volume} @ {buy_price} (z: {z_score:.2f})")
                        else: 
                            buy_price = int(best_bid+.7
                                            ) 
                            print(f"PASSIVE BUY {volume} @ {buy_price} (z: {z_score:.2f})")

                        product_orders_this_tick.append(Order(product, buy_price, volume))

                    
                    elif z_score > sell_z_threshold and current_position > -max_position:
                        sell_price = int(best_ask-.5)
                        max_sell_abs_qty = current_position - (-max_position)
                        actual_sell_volume = min(trade_volume, max_sell_abs_qty)
                        volume = min(actual_sell_volume, current_position + max_position)
                        print(f"SELL {volume} @ {sell_price} (z: {z_score:.2f})")
                        product_orders_this_tick.append(Order(product, sell_price, -volume))

                    else:
                        print("No trade: z-score within threshold or position limit hit.")

                else:
                    print(f"Not enough data for z-score on {product}")
                pass
            elif product == "DJEMBES":
                orders = self.trade_djembe_pivot(state)
                product_orders_this_tick.extend(orders)
            elif product == "PICNIC_BASKET1":
                orders = self.trade_pb1_pivot(state)
                product_orders_this_tick.extend(orders)
            elif product in ["KELP", "RAINFOREST_RESIN"]:
                fair_value = self.calculate_fair_value(product, od)
                if fair_value is None:
                    print(f"Cannot calculate fair value for {product}.")
                    result[product] = []
                    continue
                print(f"--- {product} --- Pos: {current_position}, FV: {fair_value:.2f}")
                if params.get("take_enabled", True):
                    take_orders = self.generate_take_orders(product, od, fair_value, current_position)
                    product_orders_this_tick.extend(take_orders)
                if params.get("make_enabled", True):
                    make_orders = self.generate_make_orders(product, od, fair_value, current_position)
                    product_orders_this_tick.extend(make_orders) 
            result[product] = product_orders_this_tick
            self.update_trader_state(product, od) """
        traderData = self.save_state()
        conversions = 0
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData
