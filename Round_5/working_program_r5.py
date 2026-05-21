import collections
import statistics
from datamodel import ConversionObservation, OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List, Dict, Any, Optional, Tuple
from statistics import mean
import json
from typing import Any
import numpy as np
import jsonpickle
import math
from math import log, sqrt, exp, erf, pi



DAYS_LEFT = 2
class MarketData:
    end_pos: Dict[str, int] = {}
    buy_sum: Dict[str, int] = {}
    sell_sum: Dict[str, int] = {}
    bid_prices: Dict[str, List[float]] = {}
    bid_volumes: Dict[str, List[int]] = {}
    ask_prices: Dict[str, List[float]] = {}
    ask_volumes: Dict[str, List[int]] = {}
    fair: Dict[str, float] = {}

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
            [],
            [],
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
    VOLCANIC_ROCK = "VOLCANIC_ROCK"
    VOLCANIC_ROCK_VOUCHER_9500 = "VOLCANIC_ROCK_VOUCHER_9500"
    VOLCANIC_ROCK_VOUCHER_9750 = "VOLCANIC_ROCK_VOUCHER_9750"
    VOLCANIC_ROCK_VOUCHER_10000 = "VOLCANIC_ROCK_VOUCHER_10000"
    VOLCANIC_ROCK_VOUCHER_10250 = "VOLCANIC_ROCK_VOUCHER_10250"
    VOLCANIC_ROCK_VOUCHER_10500 = "VOLCANIC_ROCK_VOUCHER_10500"
    MAGNIFICENT_MACARONS = "MAGNIFICENT_MACARONS"


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
        "fair_value_method": "vwap",
        "vwap_default_price": 1974,
        "sma_lookback": 5,
        "sma_default_price": 1974,
        "take_enabled": False,
        "take_width": 5,
        "make_enabled": False,
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
        "conv_threshold": 10,
        "vwap_default_price": 55000
        
    },
    Product.PICNIC_BASKET2: {
        "position_limit": 100,
        "fair_value_method": "vwap",
        "vwap_default_price": 10000,
        "conv_threshold": 5     },

    Product.VOLCANIC_ROCK :{
        "position_limit": 400,
    },
    Product.VOLCANIC_ROCK_VOUCHER_9500 :{
        "position_limit": 200,
        "quote_volume": 20,  
        "disregard_edge": 2,
        "join_edge": 1,
        "default_edge": 1,   
    },
    Product.VOLCANIC_ROCK_VOUCHER_9750 :{
        "position_limit": 200,
        "quote_volume": 20,  
        "disregard_edge": 2,
        "join_edge": 1,
        "default_edge": 1,   
    },
    Product.VOLCANIC_ROCK_VOUCHER_10000 :{
        "position_limit": 200,
        "quote_volume": 20,  
        "disregard_edge": 2,
        "join_edge": 1,
        "default_edge": 1, 
    },
    Product.VOLCANIC_ROCK_VOUCHER_10250 :{
        "position_limit": 200,
        "quote_volume": 20,  
        "disregard_edge": 2,
        "join_edge": 1,
        "default_edge": 1, 
    },
    Product.VOLCANIC_ROCK_VOUCHER_10500 :{
        "position_limit": 200,
        "make_enabled": True,
        "take_enabled": False,
        "fair_value_method": "vwap",
        "vwap_default_price": 2,
        "quote_volume": 5,
        "disregard_edge": 0,
        "join_edge": 0,
        "default_edge": 0
    },
    Product.MAGNIFICENT_MACARONS: {
        "position_limit": 75,
        "quote_volume": 20,  
        "disregard_edge": 2,
        "join_edge": 1,
        "default_edge": 1,    
        "take_width": 4,
        "taker_volume":5
            }
    }

class Trader:
    def __init__(self, params=None):
        self.params = params if params is not None else PARAMS
        self.conversions=0
        self.traderObject = {
            "historical_prices": {},
            "ema_state": {},
        }
        self.traderData = {
            "delta_history": []
        }
        self.position_limit = {
            "JAMS": 350,
            "CROISSANTS": 250,
            "PICNIC_BASKET2": 100,
            "VOLCANIC_ROCK_VOUCHER_9500": 200,
            "VOLCANIC_ROCK_VOUCHER_9750": 200,
            "VOLCANIC_ROCK_VOUCHER_10000": 200,
            "VOLCANIC_ROCK_VOUCHER_10250": 200,
            "VOLCANIC_ROCK_VOUCHER_10500": 200,
            "VOLCANIC_ROCK" : 400
        }
        self.voucher_strikes = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }
   



    def load_state(self, state: TradingState):
        if state.traderData != None and state.traderData != "":
            try:
                self.traderObject = jsonpickle.decode(state.traderData)
                self.traderObject.setdefault("historical_prices", {})
                self.traderObject.setdefault("ema_state", {})
            except Exception as e:
                logger.print(f"Error loading traderData: {e}")
                self.traderObject = {
                    "historical_prices": {},
                    "ema_state": {},
                }



    def update_trader_state(self, product: str, order_depth: OrderDepth):
        params = self.params[product]
        if params["fair_value_method"] == "sma":
            hist_prices = self.traderObject["historical_prices"].setdefault(product, [])
            if order_depth.buy_orders and order_depth.sell_orders:
                mid_price = (max(order_depth.buy_orders.keys()) + min(order_depth.sell_orders.keys())) / 2
                hist_prices.append(mid_price)
                max_history = params.get("sma_lookback", 10) + 5
                self.traderObject["historical_prices"][product] = hist_prices[-max_history:]


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
            logger.print(f"Warning: Unknown fair_value_method '{method}' for {product}")
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

    

   
    # ---  Market-Taking / Market-Making Logic ---
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
                        logger.print(f"TAKE BUY {product}: {quantity}x {best_ask}")
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
                        logger.print(f"TAKE SELL {product}: {quantity}x {best_bid}")
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
            logger.print(f"MAKE {product}: Skipping, calculated bid {my_bid_price} >= ask {my_ask_price}")
            return orders
        max_can_buy = pos_limit - position
        bid_quantity = int(min(quote_volume, max_can_buy))
        if bid_quantity > 0 and my_bid_price < best_market_ask:
            logger.print(f"MAKE BID {product}: {bid_quantity}x {my_bid_price}")
            orders.append(Order(product, my_bid_price, bid_quantity))
        max_can_sell = position - (-pos_limit)
        ask_quantity = int(min(quote_volume, max_can_sell))
        if ask_quantity > 0 and my_ask_price > best_market_bid:
            logger.print(f"MAKE ASK {product}: {ask_quantity}x {my_ask_price}")
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
    
    def get_mid_price(self, od: OrderDepth) -> float:
        if od.buy_orders and od.sell_orders:
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            return (best_bid + best_ask) / 2
        return None
    

    
    def handle_arbitrages(self,state: TradingState) -> List[Order]:
        orders: List[Order] = []
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
                    orders.append(Order(asset, int(price), delta))
        return orders
        
    
    
    def calculate_delta_approx(self, underlying_price: float, strike_price: float) -> float:
        
        diff = underlying_price - strike_price
        itm_threshold = 20.0 #20
        otm_threshold = -50.0 #-50

        if diff >= itm_threshold:
            return 1.0 # Deep ITM
        elif diff <= otm_threshold:
            return 0.0 # Deep OTM
        else:
            return (diff - otm_threshold) / (itm_threshold - otm_threshold)
    

    

    def _handle_squid_ink_strat(self, state:TradingState)-> List[Order]:
        orders_for_product: List[Order] = []
        products = ['SQUID_INK',"VOLCANIC_ROCK"]

        for product in products:
            
            if product not in state.order_depths:
            
                continue 

            od = state.order_depths[product]

            if not od.buy_orders or not od.sell_orders:
                
                continue

            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())

            total_volume = 0
            total_value = 0
            for price, volume in od.buy_orders.items():
                vol = abs(volume)
                total_volume += vol
                total_value += price * vol
            for price, volume in od.sell_orders.items():
                vol = abs(volume)
                total_volume += vol
                total_value += price * vol

            if total_volume == 0:
                current_vwap = (best_bid + best_ask) / 2
            else:
                current_vwap = total_value / total_volume

           
            history_key = product + "_vwap_history"
            if history_key not in self.traderData:
                self.traderData[history_key] = [] 

          
            vwap_history: List[float] = self.traderData[history_key]
            vwap_history.append(current_vwap)

            max_history_length = 200
            if len(vwap_history) > max_history_length:
            
                self.traderData[history_key] = vwap_history[-max_history_length:]
                
                vwap_history = self.traderData[history_key]

        
            if not vwap_history:
                continue 

            avg_price = sum(vwap_history) / len(vwap_history)
            max_price = max(vwap_history)
            min_price = min(vwap_history)
            price_range = max_price - min_price


            position_limit = self.params[product]["position_limit"]
            target_position = 0 

            if price_range == 0:
                target_position = 0
            else:
                half_range = price_range / 2
                
                lower_bound = avg_price - half_range 
                upper_bound = avg_price + half_range
                Nsteps = 10 
                if current_vwap <= lower_bound:
                    target_position = position_limit # Acheter au max
                elif current_vwap >= upper_bound:
                    target_position = -position_limit # Vendre au max
                else:
                    # Calcul de la position intermédiaire basée sur des paliers
                    if Nsteps > 1 and upper_bound > lower_bound : # Évite division par zéro
                        step_size_price = (upper_bound - lower_bound) / (Nsteps - 1)
                        if step_size_price > 0: 
                            step = int((current_vwap - lower_bound) // step_size_price)
                        
                            step = max(0, min(step, Nsteps - 1))
                        
                            target_position = position_limit - ((2 * position_limit) * step / (Nsteps - 1))
                            target_position = int(round(target_position))
                        else:
                            
                            target_position = 0 if current_vwap == avg_price else (position_limit if current_vwap < avg_price else -position_limit)
                    else:
                        target_position = 0 if current_vwap == avg_price else (position_limit if current_vwap < avg_price else -position_limit)


            # --- Calcul du delta et génération des ordres ---
            current_position = state.position.get(product, 0) 
            delta = target_position - current_position 

            if delta != 0:

                price_to_use = 0
                if delta > 0: 
                    price_to_use = (best_bid)
                
                    orders_for_product.append(Order(product, price_to_use, delta))
                else:
                    price_to_use = best_ask
                    orders_for_product.append(Order(product, price_to_use, delta))

            
        return orders_for_product
    
    # ----------------------------------- UTILS -----------------------------------
    def norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def black_scholes_call(self, S: float, K: float, T_days: float, r: float, sigma: float) -> float:
        """Black-Scholes price of a European call option."""
        T = T_days / 365.0
        if T <= 0 or sigma <= 0:
            return max(S - K, 0.0)

        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return S * self.norm_cdf(d1) - K * math.exp(-r * T) * self.norm_cdf(d2)

    def implied_vol_call(self, market_price, S, K, T_days, r, tol=0.00000000000001, max_iter=175):

        sigma_low = 0.01
        sigma_high = 0.35

        for _ in range(max_iter):
            sigma_mid = (sigma_low + sigma_high) / 2
            price = self.black_scholes_call(S, K, T_days, r, sigma_mid)

            if abs(price - market_price) < tol:
                return sigma_mid

            if price > market_price:
                sigma_high = sigma_mid
            else:
                sigma_low = sigma_mid

        return (sigma_low + sigma_high) / 2  

    def call_delta(self, S: float, K: float, T: float, sigma: float) -> float:
        r = 0
        T = T / 365
        if T == 0 or sigma == 0:
            return 1.0 if S > K else 0.0

        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        return 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
    

    # ----------------------------------- Options Strat -----------------------------------

    def trade_10500(self, state, market_data, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_10500"
        delta_sum = 0
        orders  : List[Order]=[]

        fair = market_data.fair[product]
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1_000_000
        v_t = self.implied_vol_call(fair, underlying_fair, 10500, dte, 0)
        
        delta = self.call_delta(fair, underlying_fair, dte, v_t)
        
        m_t = np.log(10500 / underlying_fair) / np.sqrt(dte / 365)
        
        base_coef = 0.264416  
        linear_coef = 0.010031  
        squared_coef = 0.147604  
        fair_iv = base_coef + linear_coef * m_t + squared_coef * (m_t ** 2)

        diff = v_t - fair_iv
        if "prices_10500" not in traderObject:
            traderObject["prices_10500"] = [diff]
        else:
            traderObject["prices_10500"].append(diff)
        # print(diff)
        if len(traderObject["prices_10500"]) > 13:
            diff -= np.mean(traderObject["prices_10500"])
            traderObject["prices_10500"].pop(0)
        threshold = 0.000
        if diff > threshold:  # short vol so sell option, buy und
            amount = min(market_data.buy_sum["VOLCANIC_ROCK"], market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_10500"])
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10500"]))
            option_amount = amount
            if np.mean(traderObject["prices_10500"]) > 0:
                rock_amount = amount
            else:
                rock_amount = amount // 2

            

            for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_10500"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10500"][i], option_amount)
                delta_sum -= delta * fill
                if fill != 0:
                    orders.append(Order("VOLCANIC_ROCK_VOUCHER_10500",
                                                                       market_data.bid_prices[
                                                                           "VOLCANIC_ROCK_VOUCHER_10500"][i],
                                                                       -fill))
                    market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_10500"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_10500"] -= fill
                    option_amount -= fill

        elif diff < -threshold:  # long vol
            # print("LONG")
            # print("----")
            amount = min(market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_10500"], market_data.sell_sum["VOLCANIC_ROCK"])
            # print(amount)
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_10500"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK"]))
            # print(amount)
            option_amount = amount
            if np.mean(traderObject["prices_10500"]) < 0:
                rock_amount = amount
            else:
                rock_amount = amount // 2
                raise Exception(state.timestamp, option_amount)
            # print(f"{rock_amount} rocks")
            for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK_VOUCHER_10500"])):
                fill = min(-market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_10500"][i], option_amount)
                delta_sum += delta * fill
                if fill != 0:
                    orders.append(Order("VOLCANIC_ROCK_VOUCHER_10500",
                                                                       market_data.ask_prices[
                                                                           "VOLCANIC_ROCK_VOUCHER_10500"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_10500"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_10500"] += fill
                    option_amount -= fill

            
        return  orders

    def trade_10000(self, state : TradingState, market_data : MarketData, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_10000"
        delta_sum = 0
        orders = []
        fair = market_data.fair[product]
        logger.print(f"{fair}")
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1000000
        v_t = self.implied_vol_call(fair, underlying_fair, 10000, dte, 0)
        delta = self.call_delta(fair, underlying_fair, dte, v_t)
        m_t = np.log(10000 / underlying_fair) / np.sqrt(dte / 365)

        base_coef = 0.264416  
        linear_coef = 0.010031  
        squared_coef = 0.147604  
        fair_iv = base_coef + linear_coef * m_t + squared_coef * (m_t ** 2)
  
        diff = v_t - fair_iv
        if "prices_10000" not in traderObject:
            traderObject["prices_10000"] = [diff]
        else:
            traderObject["prices_10000"].append(diff)
        threshold = 0.0
        # print(diff)
        if len(traderObject["prices_10000"]) > 20:
            diff -= np.mean(traderObject["prices_10000"])
            traderObject["prices_10000"].pop(0)
            if diff > threshold:  # short vol so sell option, buy und
                amount = market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_10000"]
                amount = min(amount, sum(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10000"]))
                option_amount = amount
                for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_10000"])):
                    fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10000"][i], option_amount)
                    delta_sum -= delta * fill
                    if fill != 0:
                        orders.append(Order("VOLCANIC_ROCK_VOUCHER_10000",
                                                                           market_data.bid_prices[
                                                                               "VOLCANIC_ROCK_VOUCHER_10000"][i],
                                                                           -fill))
                        market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_10000"] -= fill
                        market_data.end_pos["VOLCANIC_ROCK_VOUCHER_10000"] -= fill
                        option_amount -= fill

            elif diff < -threshold:  # long vol
               
                amount = market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_10000"]
                
                amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_10000"]))
                # print(amount)
                option_amount = amount
              
                for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK_VOUCHER_10000"])):
                    fill = min(-market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_10000"][i], option_amount)
                    delta_sum += delta * fill
                    if fill != 0:
                        orders.append(Order("VOLCANIC_ROCK_VOUCHER_10000",
                                                                           market_data.ask_prices[
                                                                               "VOLCANIC_ROCK_VOUCHER_10000"][i], fill))
                        market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_10000"] -= fill
                        market_data.end_pos["VOLCANIC_ROCK_VOUCHER_10000"] += fill
                        option_amount -= fill

        return orders
    
    def trade_9750(self, state, market_data, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_9750"
        orders : List[Order] = []
        fair = market_data.fair[product]
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1_000_000

        v_t = self.implied_vol_call(fair, underlying_fair, 9750, dte, 0)
        m_t = np.log(9750 / underlying_fair) / np.sqrt(dte / 365)
        
        base_coef = 0.264416  
        linear_coef = 0.010031  
        squared_coef = 0.147604  
        fair_iv = base_coef + linear_coef * m_t + squared_coef * (m_t ** 2)
        diff = v_t - fair_iv
        if "prices_9750" not in traderObject:
            traderObject["prices_9750"] = [diff]
        else:

            traderObject["prices_9750"].append(diff)
        threshold = 0.0
        # print(diff)
        if len(traderObject["prices_9750"]) > 13:
            diff -= np.mean(traderObject["prices_9750"])
            traderObject["prices_9750"].pop(0)
        if diff > threshold:  
            amount = market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_9750"]
            amount = min(amount, sum(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_9750"]))
            option_amount = amount

           

            for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_9750"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_9750"][i], option_amount)
                if fill != 0:
                    orders.append(Order("VOLCANIC_ROCK_VOUCHER_9750",
                                                                      market_data.bid_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_9750"][i],
                                                                      -fill))
                    market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_9750"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_9750"] -= fill
                    option_amount -= fill

        elif diff < -threshold:  
            amount = market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_9750"]
           
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_9750"]))
            
            option_amount = amount
           
            # print(f"{rock_amount} rocks")
            for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK_VOUCHER_9750"])):
                fill = min(-market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_9750"][i], option_amount)
                if fill != 0:
                    orders.append(Order("VOLCANIC_ROCK_VOUCHER_9750",
                                                                      market_data.ask_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_9750"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_9750"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_9750"] += fill
                    option_amount -= fill

            
        return orders
    def trade_10250(self, state, market_data, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_10250"
        orders : List[Order] = []
        fair = market_data.fair[product]
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1_000_000
        v_t = self.implied_vol_call(fair, underlying_fair, 10250, dte, 0)
        m_t = np.log(10250 / underlying_fair) / np.sqrt(dte / 365)
        base_coef = 0.264416  
        linear_coef = 0.010031 
        squared_coef = 0.147604  
        fair_iv = base_coef + linear_coef * m_t + squared_coef * (m_t ** 2)
        

        diff = v_t - fair_iv
        if "prices_10250" not in traderObject:
            traderObject["prices_10250"] = [diff]
        else:
            traderObject["prices_10250"].append(diff)
        # print(diff)
        if len(traderObject["prices_10250"]) > 13:
            diff -= np.mean(traderObject["prices_10250"])
            traderObject["prices_10250"].pop(0)
        threshold = 0
        if diff > threshold:  
            amount = min(market_data.buy_sum["VOLCANIC_ROCK"], market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_10250"])
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10250"]))
            option_amount = amount
         
            
            for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_10250"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10250"][i], option_amount)
                if fill != 0:
                    orders.append(Order("VOLCANIC_ROCK_VOUCHER_10250",
                                                                      market_data.bid_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_10250"][i],
                                                                      -fill))
                    market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_10250"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_10250"] -= fill
                    option_amount -= fill

        elif diff < -threshold:  
            amount = min(market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_10250"], market_data.sell_sum["VOLCANIC_ROCK"])
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_10250"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK"]))
            option_amount = amount
       

            for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK_VOUCHER_10250"])):
                fill = min(-market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_10250"][i], option_amount)
                if fill != 0:
                    orders.append(Order("VOLCANIC_ROCK_VOUCHER_10250",
                                                                      market_data.ask_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_10250"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_10250"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_10250"] += fill
                    option_amount -= fill

        return  orders
    
    def trade_9500(self, state, market_data, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_9500"
        orders : List[Order] = []
        fair = market_data.fair[product]
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1_000_000
        v_t = self.implied_vol_call(fair, underlying_fair, 9500, dte, 0)
        m_t = np.log(9500 / underlying_fair) / np.sqrt(dte / 365)
        base_coef = 0.264416  
        linear_coef = 0.010031 
        squared_coef = 0.147604  
        fair_iv = base_coef + linear_coef * m_t + squared_coef * (m_t ** 2)
        

        diff = v_t - fair_iv
        if "prices_9500" not in traderObject:
            traderObject["prices_9500"] = [diff]
        else:
            traderObject["prices_9500"].append(diff)
        # print(diff)
        if len(traderObject["prices_9500"]) > 13:
            diff -= np.mean(traderObject["prices_9500"])
            traderObject["prices_9500"].pop(0)
        threshold = 0
        if diff > threshold:  
            amount = min(market_data.buy_sum["VOLCANIC_ROCK"], market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_9500"])
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_9500"]))
            option_amount = amount
            rock_amount = amount
            
            for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_9500"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_9500"][i], option_amount)
                if fill != 0:
                    orders.append(Order("VOLCANIC_ROCK_VOUCHER_9500",
                                                                      market_data.bid_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_9500"][i],
                                                                      -fill))
                    market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_9500"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_9500"] -= fill
                    option_amount -= fill

        elif diff < -threshold:  
            amount = min(market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_9500"], market_data.sell_sum["VOLCANIC_ROCK"])
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_9500"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK"]))
            option_amount = amount
       

            for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK_VOUCHER_9500"])):
                fill = min(-market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_9500"][i], option_amount)
                if fill != 0:
                    orders.append(Order("VOLCANIC_ROCK_VOUCHER_9500",
                                                                      market_data.ask_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_9500"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_9500"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_9500"] += fill
                    option_amount -= fill

        return  orders


    # ----------------------------------- Macarons Strat -----------------------------------

    def _handle_macarons_combined(
        self,
        state: TradingState
    ) -> Tuple[List[Order], int]:

        product = Product.MAGNIFICENT_MACARONS
        conversion_limit = 10
        final_orders: list[Order] = []

        current_position = state.position.get(product, 0)

     
        desired_conversion = -current_position
        actual_conversion = int(round(max(-conversion_limit, min(conversion_limit, desired_conversion))))

        # --- 2. Récupération Données ---
        conv_obs = state.observations.conversionObservations.get(product)
        order_depth = state.order_depths.get(product)

        if conv_obs is None or order_depth is None:
            return final_orders, actual_conversion


        bid_price_obs = conv_obs.bidPrice; ask_price_obs = conv_obs.askPrice; transport_fees_obs = conv_obs.transportFees; export_tariff_obs = conv_obs.exportTariff; import_tariff_obs = conv_obs.importTariff
        if not all([bid_price_obs, ask_price_obs, transport_fees_obs is not None, export_tariff_obs is not None, import_tariff_obs is not None]): return final_orders, actual_conversion

        import_cost = ask_price_obs + import_tariff_obs + transport_fees_obs
        export_revenue = bid_price_obs - export_tariff_obs - transport_fees_obs

       
        taker_orders: list[Order] = []
        maker_orders: list[Order] = []
        fair_value = 0
        can_use_cross_exchange_fv = False

        # Calculer fair_value si possible
        if export_revenue < import_cost:
            fair_value = (import_cost + export_revenue) / 2.0
            can_use_cross_exchange_fv = True

            # --- 3.a Générer Ordres Taker Potentiels ---
            taker_orders = self.generate_take_orders(product, order_depth, fair_value, current_position)

            # --- 3.b Générer Ordres Maker Standards Potentiels ---
            try:
                
                default_edge = self.params[product].get("default_edge", 2.0)
                maker_orders = self.generate_make_orders(product, order_depth, fair_value, current_position) 
            except KeyError: pass

        elif export_revenue >= import_cost:
             best_market_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else float('inf')
             best_market_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else 0
             if best_market_bid > 0 and best_market_ask < float('inf') and best_market_ask > best_market_bid:
                 my_bid_price = best_market_bid
                 my_ask_price = best_market_ask
                 if my_bid_price < my_ask_price:
                     try:

                         params = self.params[product]; pos_limit = params["position_limit"]; quote_volume = params["quote_volume"]
                         max_can_buy = pos_limit - current_position; bid_quantity = int(min(quote_volume, max(0, max_can_buy)))
                         max_can_sell = current_position + pos_limit; ask_quantity = int(min(quote_volume, max(0, max_can_sell)))
                         if bid_quantity > 0: maker_orders.append(Order(product, my_bid_price, bid_quantity))
                         if ask_quantity > 0: maker_orders.append(Order(product, my_ask_price, -ask_quantity))
                     except KeyError: pass


        taker_buy = next((o for o in taker_orders if o.quantity > 0), None)
        taker_sell = next((o for o in taker_orders if o.quantity < 0), None)
        maker_buy = next((o for o in maker_orders if o.quantity > 0), None)
        maker_sell = next((o for o in maker_orders if o.quantity < 0), None)

        
        if taker_buy:
            final_orders.append(taker_buy)
        elif maker_buy:
            final_orders.append(maker_buy)
        if taker_sell:
            final_orders.append(taker_sell)
        elif maker_sell:
            final_orders.append(maker_sell)

        return final_orders, actual_conversion
        


    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        traderObject = {}
        self.load_state(state)
        result: Dict[str, List[Order]] = {}
        conversions_result = 0
        market_data = MarketData()
        products = ["VOLCANIC_ROCK_VOUCHER_9500", "VOLCANIC_ROCK_VOUCHER_9750",
                    "VOLCANIC_ROCK_VOUCHER_10000", "VOLCANIC_ROCK_VOUCHER_10250",
                    "VOLCANIC_ROCK_VOUCHER_10500", "VOLCANIC_ROCK"]
        if state.traderData != None and state.traderData != "":
            traderObject = jsonpickle.decode(state.traderData)
        for product in products:
            position = state.position.get(product, 0)
            order_depth = state.order_depths[product]
            bids, asks = order_depth.buy_orders, order_depth.sell_orders
            if order_depth.buy_orders:
                mm_bid = max(bids.items(), key=lambda tup: tup[1])[0]
            if order_depth.sell_orders:
                mm_ask = min(asks.items(), key=lambda tup: tup[1])[0]
            if order_depth.sell_orders and order_depth.buy_orders:
                fair_price = (mm_ask + mm_bid) / 2
            elif order_depth.sell_orders:
                fair_price = mm_ask
            elif order_depth.buy_orders:
                fair_price = mm_bid
            else:
                fair_price = traderObject[f"prev_fair_{product}"]
            traderObject[f"prev_fair_{product}"] = fair_price

            market_data.end_pos[product] = position
            market_data.buy_sum[product] = self.position_limit[product] - position
            market_data.sell_sum[product] = self.position_limit[product] + position
            market_data.bid_prices[product] = list(bids.keys())
            market_data.bid_volumes[product] = list(bids.values())
            market_data.ask_prices[product] = list(asks.keys())
            market_data.ask_volumes[product] = list(asks.values())
            market_data.fair[product] = fair_price
        

        orders_10000 = self.trade_10000(state,market_data,traderObject)
        for order in orders_10000:
            result.setdefault(order.symbol,[]).append(order)

        orders_9750 = self.trade_9750(state,market_data,traderObject)
        for order in orders_9750:
            result.setdefault(order.symbol,[]).append(order) 

        

        """orders_10250 = self.trade_10250(state,market_data,traderObject) ### Don't work
        for order in orders_10250:
            result.setdefault(order.symbol,[]).append(order)
        
        orders_10500 = self.trade_10500(state,market_data,traderObject) ### Don't work
        for order in orders_10500:
            result.setdefault(order.symbol,[]).append(order)
        orders_9500 = self.trade_9500(state,market_data,traderObject) ### Don't work
        for order in orders_9500:
            result.setdefault(order.symbol,[]).append(order)"""

     


        

        macarons_orders,conversions = self._handle_macarons_combined(state)
        conversions_result+=conversions
        for order in macarons_orders :
            result.setdefault(order.symbol,[]).append(order)

       


        # -------------- Arbitrage Strategy --------------#

        arbitrage_strat_orders = self.handle_arbitrages(state)
        for order in arbitrage_strat_orders :
            result.setdefault(order.symbol,[]).append(order)
        
        
    
        
        # -------------- SQUID_INK --------------#

        squid_ink_orders = self._handle_squid_ink_strat(state)
        for order in squid_ink_orders:
            result.setdefault(order.symbol,[]).append(order)
 
        # -------------- KELP + RESIN Strategy --------------#

        other_products = [p for p in state.order_depths.keys() if p in [Product.RAINFOREST_RESIN,Product.KELP]]
        for product in other_products:
            if product not in self.params:
                continue
            order_depth: OrderDepth = state.order_depths[product]
           
            current_position = state.position.get(product, 0)
            params = self.params[product]
            product_orders_this_tick: List[Order] = []

            if product=="RAINFOREST_RESIN" or product == "KELP":

                fair_value = self.calculate_fair_value(product, order_depth)

                if fair_value is None:
                    logger.print(f"Impossible to calculate the fair value for {product}.")
                    result[product] = []

                logger.print(f"--- {product} --- Pos: {current_position}, Fair Value: {fair_value:.2f}")

            
                if params.get("take_enabled", True):
                    
                    take_orders = self.generate_take_orders(
                        product, order_depth, fair_value, current_position
                    )
                    product_orders_this_tick.extend(take_orders)

                
                if params.get("make_enabled", True):    
                    make_orders = self.generate_make_orders(
                        product, order_depth, fair_value, current_position
                    )
                    product_orders_this_tick.extend(make_orders)
 
           
            result[product] = product_orders_this_tick

           
            self.update_trader_state(product, order_depth)




            
            



        traderData = jsonpickle.encode(traderObject)
        
        logger.flush(state, result, conversions_result, traderData)
        return result, conversions_result, traderData