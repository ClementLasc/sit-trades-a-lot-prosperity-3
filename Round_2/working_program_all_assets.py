from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List,Dict
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
    JAM = "JAM"
    PICNIC_BASKET1 = "PICNIC_BASKET1"
    PICNIC_BASKET2 = "PICNIC_BASKET2"

PARAMS = {
    Product.RAINFOREST_RESIN: {
        "position_limit": 50,
        "fair_value_method": "sma",
        "sma_lookback": 8,         
        "sma_default_price": 10000,
        # --- Market Taking Params ---
        "take_enabled": True,
        "take_width": 0,            #0
        # --- Market Making Params ---
        "make_enabled": True,      
        "quote_volume": 15,      #15    
        "disregard_edge": 1,   # 1    
        "join_edge": 0,           #0
        "default_edge": 0,          #0
       
    }, # Best amoutnt :2049
    Product.KELP: {
        "position_limit": 50,
        "fair_value_method": "vwap_ema",
        "vwap_default_price": 2023, 
        "ema_alpha": 0.15,          #0.15
        # --- Market Taking Params ---s
        "take_enabled": True, #True
        "take_width": 0, # 0
        # --- Market Making Params ---
        "make_enabled": True,
        "quote_volume": 15,#15
        "disregard_edge": 1,# 1 
        "join_edge": 1,# 1
        "default_edge": 0, # 0
    }, # Best = 521
    Product.SQUID_INK: {
        "position_limit": 50,   
    } ,
    Product.DJEMBES:{
        "position_limit":60,   
    } ,
    Product.CROISSANTS: {
        "position_limit": 250,   
    } ,
    Product.JAM : {
        "position_limit": 350,   
    } ,
    Product.PICNIC_BASKET1 : {
        "position_limit": 60,   
    } ,
    Product.PICNIC_BASKET2: {
        "position_limit": 100,   
    } 
    
}

class Trader:

    def __init__(self, params=None):
        self.params = params if params is not None else PARAMS
        self.traderObject = {
            "historical_prices": {},
            "ema_state": {},
            "djembe_spread_position": 0,
            "djembe_spread_history": [],

        }


    # --- State Management ---
    def load_state(self, state: TradingState):
        if state.traderData != None and state.traderData != "":
            try:
                self.traderObject = jsonpickle.decode(state.traderData)
                
                self.traderObject.setdefault("historical_prices", {})
                self.traderObject.setdefault("ema_state", {})
                self.traderObject.setdefault("djembe_spread_position", 0)
                self.traderObject.setdefault("djembe_spread_history", [])
            except Exception as e:
                print(f"Error loading traderData: {e}")
                # Initialize with default if loading fails
                self.traderObject = {
                    "historical_prices": {},
                    "ema_state": {},
                    "djembe_spread_position": 0,
                    "djembe_spread_history": [],
                 }

    def save_state(self) -> str:
        state_to_save = {
            "historical_prices": self.traderObject["historical_prices"],
            "ema_state": self.traderObject["ema_state"],
            "djembe_spread_position": self.traderObject["djembe_spread_position"],

        }
        return jsonpickle.encode(state_to_save)

    def update_trader_state(self, product: str, order_depth: OrderDepth):
        
        params = self.params[product]
    
        if "historical_prices" not in self.traderObject:
            self.traderObject["historical_prices"] = {}
        
        
        hist_prices = self.traderObject["historical_prices"].setdefault(product, [])
       
        if 'djembe_spread_history' not in self.traderObject:
            self.traderObject['djembe_spread_history'] = []
     
        buy_prices = list(order_depth.buy_orders.keys()) if order_depth.buy_orders else []
        sell_prices = list(order_depth.sell_orders.keys()) if order_depth.sell_orders else []
      
        if buy_prices and sell_prices:
            mid_price = (max(buy_prices) + min(sell_prices)) / 2
            hist_prices.append(mid_price)

            max_history = 50
            if len(hist_prices) > max_history:
                self.traderObject["historical_prices"][product] = hist_prices[-max_history:]
                djembe_price = self.traderObject["historical_prices"]["DJEMBES"][-1]
                basket1_price = self.traderObject["historical_prices"]["PICNIC_BASKET1"][-1]
                basket2_price = self.traderObject["historical_prices"]["PICNIC_BASKET2"][-1]
                
                current_spread_value = 2 * djembe_price - 2 * basket1_price + 3 * basket2_price
                self.traderObject['djembe_spread_history'].append(current_spread_value)
                
                if len(self.traderObject['djembe_spread_history']) > max_history:
                    self.traderObject['djembe_spread_history'] = self.traderObject['djembe_spread_history'][-max_history:]





    def calculate_fair_value(self, product: str, order_depth: OrderDepth) -> float | None:
        """Dispatcher function to call the correct fair value method."""
        params = self.params[product]
        method = params["fair_value_method"]
        if method == "sma":
            return self._fair_value_sma(product, params)
        elif method == "vwap_ema":
            return self._fair_value_vwap_ema(product, order_depth, params)
        elif method == "vwap":
            return self._fair_value_vwap(product, order_depth, params)
        else:
            print(f"Warning: Unknown fair_value_method '{method}' for {product}")
            return None 

    def _calculate_vwap(self,product : str, order_depth: OrderDepth, min_volume_threshold: int = 3) -> float | None:
        """
        Helper to calculate VWAP-like metric from order book,
        optionally filtering levels by minimum volume.
        """
      
        filtered_bids = {price: vol for price, vol in order_depth.buy_orders.items() if vol >= min_volume_threshold}
        total_bid_value = sum(price * vol for price, vol in filtered_bids.items())
        total_bid_vol = sum(filtered_bids.values())

        filtered_asks = {price: vol for price, vol in order_depth.sell_orders.items() if abs(vol) >= min_volume_threshold}
        total_ask_value = sum(price * abs(vol) for price, vol in filtered_asks.items())
        total_ask_vol = sum(abs(vol) for vol in filtered_asks.values())

        base_vwap = (total_bid_value + total_ask_value) / (total_bid_vol + total_ask_vol)

        bid_pressure = sum(vol for vol in order_depth.buy_orders.values())
        ask_pressure = sum(abs(vol) for vol in order_depth.sell_orders.values())
        
        total_volume = bid_pressure + ask_pressure
        imbalance = (bid_pressure - ask_pressure) / total_volume
        
        if total_volume == 0 or product == "KELP":
            
            typical_move = 2
            adjustment = typical_move * (2 / (1 + math.exp(-5 * imbalance)) - 1)
            return base_vwap + adjustment
        
        """ elif product == "SQUID_INK":
            
            adjustment_factor = .6 # Best is .6 yet
            
           
            weighted_bid_pressure = sum(price * vol for price, vol in order_depth.buy_orders.items())
            weighted_ask_pressure = sum(price * abs(vol) for price, vol in order_depth.sell_orders.items())
            
            
            if weighted_bid_pressure + weighted_ask_pressure > 0:
                weighted_imbalance = (weighted_bid_pressure - weighted_ask_pressure) / (weighted_bid_pressure + weighted_ask_pressure)
                
                
                combined_imbalance = 0.2 * imbalance + 0.8 * weighted_imbalance # best is .2/.8
            else:
                combined_imbalance = imbalance
            
            
            adjusted_price = base_vwap * (1 + adjustment_factor * combined_imbalance)
            
           
            max_adjustment = 0.05 * base_vwap  
            actual_adjustment = adjusted_price - base_vwap
            
            if abs(actual_adjustment) > max_adjustment:
                adjusted_price = base_vwap + (max_adjustment if actual_adjustment > 0 else -max_adjustment)
            
            return adjusted_price  """
    def _fair_value_sma(self, product: str, params: Dict[str, Any]) -> float | None:
        lookback = params["sma_lookback"]
        hist_prices = self.traderObject["historical_prices"].get(product, [])

        if len(hist_prices) >= lookback:
            recent_prices = hist_prices[-lookback:]
            return mean(recent_prices)
        else:

            return params.get("sma_default_price") # Return default if history is short

    def _fair_value_vwap_ema(self, product: str, order_depth: OrderDepth, params: Dict[str, Any]) -> float | None:
        """Calculate fair value using EMA of VWAP."""
        current_vwap = self._calculate_vwap(product,order_depth)
        last_ema = self.traderObject["ema_state"].get(product)
        alpha = params["ema_alpha"]
        default_price = params["vwap_default_price"]
        

        if current_vwap is None:
            
             return last_ema if last_ema is not None else default_price

        if last_ema is None:

            new_ema = current_vwap
        else:
            new_ema = alpha * current_vwap + (1 - alpha) * last_ema

        self.traderObject["ema_state"][product] = new_ema # Store updated EMA
        return new_ema

    def _fair_value_vwap(self, product: str, order_depth: OrderDepth, params: Dict[str, Any]) -> float | None:
        """Calculate fair value using raw VWAP."""
        current_vwap = self._calculate_vwap(product,order_depth)
        if current_vwap is not None:
            return current_vwap
        else:
            # Fallback if VWAP calculation fails
            return params["vwap_default_price"]

    # --- Order Generation Logic ---


    def generate_take_orders(
        self,
        product: str,
        order_depth: OrderDepth,
        fair_value: float,
        position: int,
    ) -> List[Order]:
        """Generates aggressive market taking orders."""
        orders: List[Order] = []
        params = self.params[product]
        position_limit = params["position_limit"]
        take_width = params["take_width"]
        taker_volume_override = params.get("taker_volume")

        # --- Buy Logic (Hitting the Ask) ---
        if order_depth.sell_orders:
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_volume = abs(order_depth.sell_orders[best_ask])

            if best_ask <= fair_value - take_width:
                max_can_buy = position_limit - position
                if max_can_buy > 0:
                    # Apply volume override if specified, otherwise use available volume
                    vol_to_buy = taker_volume_override if taker_volume_override is not None else best_ask_volume
                    if product=="SQUID_INK":
                        quantity = 1
                    else :
                        quantity = int(min(vol_to_buy, max_can_buy))

                    if quantity > 0:
                        print(f"TAKE BUY {product}: {quantity}x {best_ask}")
                        orders.append(Order(product, best_ask, quantity))
                        
        # --- Sell Logic (Hitting the Bid) ---
        if order_depth.buy_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_volume = order_depth.buy_orders[best_bid]

            if best_bid >= fair_value + take_width:
             
                max_can_sell = position - (-position_limit) # position + position_limit
                if max_can_sell > 0:
                    vol_to_sell = taker_volume_override if taker_volume_override is not None else best_bid_volume
                    
                    quantity = int(min(vol_to_sell, max_can_sell))

                    if quantity > 0:
                        print(f"TAKE SELL {product}: {quantity}x {best_bid}")
                        orders.append(Order(product, best_bid, -quantity))
                        # Note: We DO NOT modify order_depth here anymore

        return orders


    def generate_make_orders(
         self,
         product: str,
         order_depth: OrderDepth,
         fair_value: float,
         position: int,
     ) -> List[Order]:
        """Generates passive market making orders."""
        orders: List[Order] = []
        params = self.params[product]
        position_limit = params["position_limit"]
        quote_volume = params["quote_volume"]
        disregard_edge = params["disregard_edge"]
        join_edge = params["join_edge"]
        default_edge = params["default_edge"]
        

        best_market_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else float('inf')
        best_market_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else 0

        # --- Determine ideal Bid/Ask Prices (Pennying/Joining/Default) ---
        asks_above_fair = [p for p in order_depth.sell_orders if p > fair_value + disregard_edge]
        bids_below_fair = [p for p in order_depth.buy_orders if p < fair_value - disregard_edge]

        best_ask_above_fair = min(asks_above_fair) if asks_above_fair else None
        best_bid_below_fair = max(bids_below_fair) if bids_below_fair else None

        my_ask_price = round(fair_value + default_edge)
        if best_ask_above_fair is not None:
            if abs(best_ask_above_fair - fair_value) <= join_edge:
                my_ask_price = best_ask_above_fair  # Join
            else:
                my_ask_price = best_ask_above_fair - 1  # Penny

        my_bid_price = round(fair_value - default_edge)
        if best_bid_below_fair is not None:
            if abs(fair_value - best_bid_below_fair) <= join_edge:
                my_bid_price = best_bid_below_fair # Join
            else:
                my_bid_price = best_bid_below_fair + 1 # Penny

        
        
        my_bid_price = int(math.floor(my_bid_price))
        my_ask_price = int(math.ceil(my_ask_price))

        # Ensure bid < ask
        if my_bid_price >= my_ask_price:
             print(f"MAKE {product}: Skipping, calculated bid {my_bid_price} >= ask {my_ask_price}")
             return orders 


        # --- Place Orders ---
        # Place Bid
        max_can_buy = position_limit - position
        bid_quantity = int(min(quote_volume, max_can_buy))
        # Only place if we have room and price is valid (doesn't cross market)
        if bid_quantity > 0 and my_bid_price < best_market_ask:
            print(f"MAKE BID {product}: {bid_quantity}x {my_bid_price}")
            orders.append(Order(product, my_bid_price, bid_quantity))

        # Place Ask
        max_can_sell = position - (-position_limit) # position + position_limit
        ask_quantity = int(min(quote_volume, max_can_sell))
         # Only place if we have room and price is valid (doesn't cross market)
        if ask_quantity > 0 and my_ask_price > best_market_bid:
            print(f"MAKE ASK {product}: {ask_quantity}x {my_ask_price}")
            orders.append(Order(product, my_ask_price, -ask_quantity)) # Sell orders have negative volume

        return orders
    
    # --- Utils Function ---
    def _get_mid_price(self, product: str, state: TradingState) -> float | None:
       
        if product not in state.order_depths:
            return None
        order_depth = state.order_depths[product]
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            if best_ask > best_bid:
                 return (best_bid + best_ask) / 2.0
            else:
                 return float(best_bid) 
        return None

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
    

    def _handle_DJEMBES_spread_strategy(self, state: TradingState) -> List[Order]:
        
        orders: List[Order] = []
        product_djembe = "DJEMBES"
        product_basket1 = "PICNIC_BASKET1"
        product_basket2 = "PICNIC_BASKET2"
        products = [product_djembe, product_basket1, product_basket2]


        window = 5
        smoothing_window = 5
        k_threshold = 1.2
        k_close_threshold = 0.8
        max_spread_pos = 30

       
        if not all(p in state.order_depths for p in products): return orders
        mid_prices, best_asks, best_bids, prices_ok = {}, {}, {}, True
        for p in products:
            mid, ask, bid = self._get_mid_price(p, state), self._get_best_ask(p, state), self._get_best_bid(p, state)
            mid_prices[p], best_asks[p], best_bids[p] = mid, ask, bid
            if mid is None or ask is None or bid is None: prices_ok = False
        if not prices_ok: return orders

        mid_djembe = mid_prices[product_djembe]
        mid_basket1 = mid_prices[product_basket1]
        mid_basket2 = mid_prices[product_basket2]


        current_spread_value = 2 * mid_djembe - 2 * mid_basket1 + 3 * mid_basket2

       
        hist_djembe = self.traderObject.get("historical_prices", {}).get(product_djembe, [])
        hist_basket1 = self.traderObject.get("historical_prices", {}).get(product_basket1, [])
        hist_basket2 = self.traderObject.get("historical_prices", {}).get(product_basket2, [])

        spread_history = self.traderObject['djembe_spread_history']

        min_observations = window
        min_len = min(len(hist_djembe), len(hist_basket1), len(hist_basket2))
        if min_len < min_observations:
            return orders

        # Calculer toutes les valeurs de spread historiques en une seule fois
        spread_history = [
            2 * hist_djembe[i] - 2 * hist_basket1[i] + 3 * hist_basket2[i]
            for i in range(min_len)
        ]

        if not spread_history:
            return orders

       
        recent_spreads = spread_history[-window:]
        rolling_mean = -26
        variance = sum((s - rolling_mean) ** 2 for s in recent_spreads) / window
        rolling_std_dev =  150

        # Calculer la valeur lissée du spread actuel
        if len(spread_history) >= smoothing_window - 1:
            smoothing_values = spread_history[-(smoothing_window - 1):] + [current_spread_value]
            smoothed_spread_value = sum(smoothing_values) / smoothing_window
        else:
            smoothed_spread_value = current_spread_value
        buy_threshold_level = rolling_mean - k_threshold * rolling_std_dev
        sell_threshold_level = rolling_mean + k_threshold * rolling_std_dev
        close_buy_threshold = rolling_mean - k_close_threshold * rolling_std_dev
        close_sell_threshold = rolling_mean + k_close_threshold * rolling_std_dev

        
        current_spread_pos = self.traderObject.get('djembe_spread_position', 0)
        
        trade_unit = 1
        closed_this_tick = False

        
        if current_spread_pos > 0 and smoothed_spread_value >= close_sell_threshold:
            vol_to_close = min(trade_unit, abs(current_spread_pos))
            orders.append(Order(product_djembe, best_bids[product_djembe], -vol_to_close * 2))
            orders.append(Order(product_basket1, best_asks[product_basket1], vol_to_close * 2))
            orders.append(Order(product_basket2, best_bids[product_basket2], -vol_to_close * 3))
            self.traderObject['djembe_spread_position'] -= vol_to_close
            closed_this_tick = True

        elif current_spread_pos < 0 and smoothed_spread_value <= close_buy_threshold:
            vol_to_close = min(trade_unit, abs(current_spread_pos))
            orders.append(Order(product_djembe, best_asks[product_djembe], vol_to_close * 2))
            orders.append(Order(product_basket1, best_bids[product_basket1], -vol_to_close * 2))
            orders.append(Order(product_basket2, best_asks[product_basket2], vol_to_close * 3))
            self.traderObject['djembe_spread_position'] += vol_to_close
            closed_this_tick = True

        if not closed_this_tick:
            if smoothed_spread_value < buy_threshold_level and current_spread_pos < max_spread_pos:
                vol_to_trade = min(trade_unit, max_spread_pos - current_spread_pos)
                orders.append(Order(product_djembe, best_asks[product_djembe], vol_to_trade * 2))
                orders.append(Order(product_basket1, best_bids[product_basket1], -vol_to_trade * 2))
                orders.append(Order(product_basket2, best_asks[product_basket2], vol_to_trade * 3))
                self.traderObject['djembe_spread_position'] += vol_to_trade
            
            elif smoothed_spread_value > sell_threshold_level and current_spread_pos > -max_spread_pos:
                vol_to_trade = min(trade_unit, current_spread_pos - (-max_spread_pos))
                orders.append(Order(product_djembe, best_bids[product_djembe], -vol_to_trade * 2))
                orders.append(Order(product_basket1, best_asks[product_basket1], vol_to_trade * 2))
                orders.append(Order(product_basket2, best_bids[product_basket2], -vol_to_trade * 3))
                self.traderObject['djembe_spread_position'] -= vol_to_trade

        return orders
    

    def _check_indiv_limits_before_trade(self, state: TradingState, vol_to_trade: int, direction: str) -> bool:
        """ Vérifie si trader vol_to_trade unités de spread respecte les limites individuelles """
        pos = state.position
        if direction == "BUY": 
            new_pos_d = pos.get("DJEMBES", 0) + vol_to_trade * 2
            new_pos_b1 = pos.get("PICNIC_BASKET1", 0) - vol_to_trade * 2
            new_pos_b2 = pos.get("PICNIC_BASKET2", 0) + vol_to_trade * 3
        elif direction == "SELL": 
            new_pos_d = pos.get("DJEMBES", 0) - vol_to_trade * 2
            new_pos_b1 = pos.get("PICNIC_BASKET1", 0) + vol_to_trade * 2
            new_pos_b2 = pos.get("PICNIC_BASKET2", 0) - vol_to_trade * 3
        else:
            return False
        
        if abs(new_pos_d) <= self.params["DJEMBES"]["position_limit"] and \
           abs(new_pos_b1) <= self.params["PICNIC_BASKET1"]["position_limit"] and \
           abs(new_pos_b2) <= self.params["PICNIC_BASKET2"]["position_limit"]:
            return True
        else:
           
            return False

    # --- Main Execution Logic ---
    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self.load_state(state)
        result: Dict[str, List[Order]] = {}
        conversions = 0 # Not used currently


        spread_products = ["DJEMBES", "PICNIC_BASKET1", "PICNIC_BASKET2"]
        for product in spread_products:
            if product in state.order_depths.keys():
                self.update_trader_state(product, state.order_depths[product])
                

        
        # --- Handle DJEMBES Spread Strategy ---
        DJEMBES_spread_orders = self._handle_DJEMBES_spread_strategy(state)
        for order in DJEMBES_spread_orders:
            result.setdefault(order.symbol, []).append(order)
        
        # ---Others ---

        other_products = [p for p in state.order_depths.keys() if p not in ["DJEMBES", "PICNIC_BASKET1", "PICNIC_BASKET2"]]
        for product in other_products:
            if product not in self.params:
                print(f"Avertissement: Pas de paramètres trouvés pour le produit {product}. Saut.")
                continue

            order_depth: OrderDepth = state.order_depths[product]
           
            current_position = state.position.get(product, 0)
            params = self.params[product]
            product_orders_this_tick: List[Order] = []

            """ if product == "SQUID_INK":
                # If no buy or sell orders available, skip
                if not order_depth.buy_orders or not order_depth.sell_orders:
                    result[product] = []
                    continue

                # Calculate best bid & best ask, then mid-price
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
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

            elif product == "KELP" or product =="RAINFOREST_RESIN":

                fair_value = self.calculate_fair_value(product, order_depth)

                if fair_value is None:
                    print(f"Impossible to calculate the fair value for {product}.")
                    result[product] = []

                print(f"--- {product} --- Pos: {current_position}, Fair Value: {fair_value:.2f}")

            
                if params.get("take_enabled", True):
                    
                    take_orders = self.generate_take_orders(
                        product, order_depth, fair_value, current_position
                    )
                    product_orders_this_tick.extend(take_orders)

                
                if params.get("make_enabled", True):    
                    make_orders = self.generate_make_orders(
                        product, order_depth, fair_value, current_position
                    )
                    product_orders_this_tick.extend(make_orders) """

            
            

           
            result[product] = product_orders_this_tick

           
            self.update_trader_state(product, order_depth)

       
        traderData = self.save_state() 
        conversions = 0  
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData