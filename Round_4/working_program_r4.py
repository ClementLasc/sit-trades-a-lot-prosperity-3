from datamodel import ConversionObservation, OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List, Dict, Any, Tuple
from statistics import mean
import json
from typing import Any
import numpy as np
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
    VOLCANIC_ROCK_VOUCHER_9750 = "VOLCANIC_ROCK_VOUCHER_9500"
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
    },
    Product.VOLCANIC_ROCK_VOUCHER_9750 :{
        "position_limit": 200,
    },
    Product.VOLCANIC_ROCK_VOUCHER_10000 :{
        "position_limit": 200,
    },
    Product.VOLCANIC_ROCK_VOUCHER_10000 :{
        "position_limit": 200,
    },
    Product.VOLCANIC_ROCK_VOUCHER_10000 :{
        "position_limit": 200,
    },
    Product.MAGNIFICENT_MACARONS:{
        "position_limit": 75,
        "conversion_limit":10,
        "step_size": 15,
        "base_unit": 5,
        "long_min_diff": 20
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
        self.feature_order = [
            'transportFees', 'exportTariff',
            'importTariff', 'sugarPrice',
            'sunlightIndex'
        ]
        
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
    

    def handle_options_strategy(self,state: TradingState) -> List[Order]:
        orders:List[Order] = []
      
        replication_coef=1
        self.voucher_strikes = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }

        if "VOLCANIC_ROCK" not in state.order_depths:
            logger.print("WARN: No order depth found for VOLCANIC_ROCK")
            return []
        
        od_rock = state.order_depths["VOLCANIC_ROCK"]
        if not od_rock.buy_orders or not od_rock.sell_orders:
            logger.print("WARN: Incomplete order depth for VOLCANIC_ROCK")
            return []
        
        best_bid_rock = max(od_rock.buy_orders.keys())
        best_ask_rock = min(od_rock.sell_orders.keys())
        rock_mid_price = (best_bid_rock + best_ask_rock) / 2


        for voucher_symbol, strike_price in self.voucher_strikes.items():
            

            if voucher_symbol not in state.order_depths:
                continue
            od_voucher = state.order_depths[voucher_symbol]
            if not od_voucher.buy_orders or not od_voucher.sell_orders:
                continue

           
            diff = rock_mid_price - strike_price
            steps = int(diff // 25)
            target_position_voucher = -10 * steps
            limit_voucher = self.position_limit.get(voucher_symbol, 200)
            target_position_voucher = max(-limit_voucher, min(limit_voucher, target_position_voucher))
            current_position_voucher = state.position.get(voucher_symbol, 0)
            delta_position_voucher = target_position_voucher - current_position_voucher

            if delta_position_voucher == 0:
                continue # Pas d'ordre à passer

            
            best_bid_vouch = max(od_voucher.buy_orders.keys())
            best_ask_vouch = min(od_voucher.sell_orders.keys())
            mid_vouch = (best_bid_vouch+best_ask_vouch)/2

            if delta_position_voucher > 0: 
             
                orders.append(Order(voucher_symbol, int(mid_vouch), delta_position_voucher))
            else: 
                
                orders.append(Order(voucher_symbol, int(mid_vouch), delta_position_voucher))

        total_current_delta = 0
        
        for symbol, position in state.position.items():
            if symbol in self.voucher_strikes:
                strike = self.voucher_strikes[symbol]
               
                option_delta = self.calculate_delta_approx(rock_mid_price, strike)
                
                total_current_delta += position * option_delta

        
        target_replication_position = 1 * total_current_delta * replication_coef
        target_replication_position = int(round(target_replication_position))

        limit_underlying = self.position_limit.get('VOLCANIC_ROCK', 400)
        target_replication_position = max(-limit_underlying, min(limit_underlying, target_replication_position))
 
        current_position_underlying = state.position.get("VOLCANIC_ROCK", 0)
        delta_position_underlying = target_replication_position - current_position_underlying

        if delta_position_underlying != 0:
           
            if delta_position_underlying > 0: 
                price = int(rock_mid_price)
                orders.append(Order("VOLCANIC_ROCK", int(price), delta_position_underlying))
            else: 
                price = rock_mid_price
                orders.append(Order("VOLCANIC_ROCK", int(price), delta_position_underlying))
            logger.print(f"HEDGING: Total Option Delta={total_current_delta:.2f}, Target Hedge Pos={target_replication_position}, Current Hedge Pos={current_position_underlying}, Order Hedge Qty={delta_position_underlying}")
        else:
            logger.print(f"HEDGING: Total Option Delta={total_current_delta:.2f}, Target Hedge Pos={target_replication_position}, Current Hedge Pos={current_position_underlying}. No Hedge Order Needed.")
 
        return orders
    

    def _handle_squid_ink_strat(self, state:TradingState)-> List[Order]:
        orders_for_product: List[Order] = []
        products = ['SQUID_INK']

        for product in products:
            if product not in state.order_depths:
            
                return orders_for_product 

            od = state.order_depths[product]
            # Vérifie s'il y a des ordres d'achat ET de vente pour calculer le spread/prix
            if not od.buy_orders or not od.sell_orders:
                # Pas assez de liquidité ou carnet d'ordres vide d'un côté
                return orders_for_product # Retourne liste vide

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
                return orders_for_product 

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
                    price_to_use = best_bid 
                
                    orders_for_product.append(Order(product, price_to_use, delta))
                else:
                    price_to_use = best_ask
                    orders_for_product.append(Order(product, price_to_use, delta))

            
        return orders_for_product
    
    
    def _predict(self, features: np.ndarray) -> float:
        scaled = (features - self.means) / self.scales
        return float(np.dot(scaled, self.coeffs) + self.intercept)
          


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

        bid = self._get_best_bid(prod,state)
        ask = self._get_best_ask(prod,state)
        mid = (bid + ask) / 2.0
        diff = mid - fair_value

        if -cfg['long_min_diff']<diff<0 :
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




    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self.load_state(state)
        result: Dict[str, List[Order]] = {}


        
        
        
       
        # -------------- Macarons Arbitrage Strategy --------------#

        macarons_orders,self.conversions = self._handle_macarons_stat_arb(state)
        for order in macarons_orders:
            result.setdefault(order.symbol,[]).append(order)


        # -------------- Arbitrage Strategy --------------#

        """arbitrage_strat_orders = self.handle_arbitrages(state)
        for order in arbitrage_strat_orders :
            result.setdefault(order.symbol,[]).append(order)
        
        
        

        # -------------- Options + underlying Strategy --------------#
        options_strat = self.handle_options_strategy(state)
        for order in options_strat:
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




            order_depth: OrderDepth = state.order_depths[product]
           
            current_position = state.position.get(product, 0)
            params = self.params[product]
            product_orders_this_tick: List[Order] = []"""



        traderData = self.save_state() 
        
        logger.flush(state, result, self.conversions, traderData)
        return result, self.conversions, traderData