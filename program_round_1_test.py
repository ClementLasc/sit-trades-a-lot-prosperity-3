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
PARAMS = {
    Product.RAINFOREST_RESIN: {
        "position_limit": 50,
        "fair_value_method": "sma",
        "sma_lookback": 10,         
        "sma_default_price": 10000,
        # --- Market Taking Params ---
        "take_enabled": True,
        "take_width": 0,            #0
        # --- Market Making Params ---
        "make_enabled": True,      
        "quote_volume": 10,      #10    
        "disregard_edge": 1,   # 1    
        "join_edge": 2,           #2  
        "default_edge": 2,          #2
        "manage_position": False,     #False
        "soft_position_limit": 10,  #10
    },
    Product.KELP: {
        "position_limit": 50,
        "fair_value_method": "vwap_ema",
        "vwap_default_price": 2023, 
        "ema_alpha": 0.3,          #0.3
        # --- Market Taking Params ---
        "take_enabled": True,
        "take_width": 0, # 0
        # --- Market Making Params ---
        "make_enabled": True,
        "quote_volume": 5,
        "disregard_edge": 1,# 1 
        "join_edge": 3,# 3
        "default_edge": 5, # 5
        "manage_position": False,  
        "soft_position_limit": 10,
    },
    Product.SQUID_INK: {
        "position_limit": 50,
        "fair_value_method": "vwap",
        "vwap_default_price": 1973, # Fallback price
        # --- Market Taking Params ---
        "take_enabled": True,
        "take_width": 1,       # 1    
        "taker_volume": 1,     #1     
        # --- Market Making Params ---
        "make_enabled": True,      
        "quote_volume": 5,          
        "disregard_edge": 1, # 1
        "join_edge": 1, # 1
        "default_edge": 3,  # 3
        "manage_position": False,
        "soft_position_limit": 10,
    },
}

class Trader:

    def __init__(self, params=None):
        self.params = params if params is not None else PARAMS
        
        self.traderObject = {
            "historical_prices": {}, 
            "ema_state": {},        
        }

    # --- State Management ---
    def load_state(self, state: TradingState):
        if state.traderData != None and state.traderData != "":
            try:
                self.traderObject = jsonpickle.decode(state.traderData)
                # Ensure keys exist if loading older state
                self.traderObject.setdefault("historical_prices", {})
                self.traderObject.setdefault("ema_state", {})
            except Exception as e:
                print(f"Error loading traderData: {e}")
                # Initialize with default if loading fails
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
            buy_prices = list(order_depth.buy_orders.keys()) if order_depth.buy_orders else []
            sell_prices = list(order_depth.sell_orders.keys()) if order_depth.sell_orders else []

            if buy_prices and sell_prices:
                mid_price = (max(buy_prices) + min(sell_prices)) / 2
                hist_prices.append(mid_price)
               
                max_history = params.get("sma_lookback", 50) + 5
                self.traderObject["historical_prices"][product] = hist_prices[-max_history:]


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

    def _calculate_vwap(self, order_depth: OrderDepth) -> float | None:
        total_bid_value = sum(price * vol for price, vol in order_depth.buy_orders.items())
        total_ask_value = sum(price * abs(vol) for price, vol in order_depth.sell_orders.items())
        total_bid_vol = sum(order_depth.buy_orders.values())
        total_ask_vol = sum(abs(v) for v in order_depth.sell_orders.values())

        if total_bid_vol + total_ask_vol > 0:
            return (total_bid_value + total_ask_value) / (total_bid_vol + total_ask_vol)
        else:
            return None 

    def _fair_value_sma(self, product: str, params: Dict[str, Any]) -> float | None:
        lookback = params["sma_lookback"]
        hist_prices = self.traderObject["historical_prices"].get(product, [])

        if len(hist_prices) >= lookback:
            recent_prices = hist_prices[-lookback:]
            return mean(recent_prices)
        else:
            # Not enough history, return default or None
            return params.get("sma_default_price") # Return default if history is short

    def _fair_value_vwap_ema(self, product: str, order_depth: OrderDepth, params: Dict[str, Any]) -> float | None:
        """Calculate fair value using EMA of VWAP."""
        current_vwap = self._calculate_vwap(order_depth)
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
        current_vwap = self._calculate_vwap(order_depth)
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
                    if product == "SQUID_INK" :
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
        manage_position = params.get("manage_position", False)
        soft_limit = params.get("soft_position_limit", 0)

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

        # --- Inventory Skewing ---
        if manage_position:
            if position > soft_limit:
                my_ask_price -= 1 # Make selling more attractive
                my_bid_price -= 1 # Make buying less attractive
            elif position < -soft_limit:
                my_bid_price += 1 # Make buying more attractive
                my_ask_price += 1 # Make selling less attractive

        # Ensure integer prices if needed by platform
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

    # --- Main Execution Logic ---
    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self.load_state(state)
        result: Dict[str, List[Order]] = {}
        conversions = 0 # Not used currently

        for product in state.order_depths.keys():
            if product not in self.params:
                print(f"Warning: No parameters found for product {product}. Skipping.")
                continue

            order_depth: OrderDepth = state.order_depths[product]
            current_position = state.position.get(product, 0)
            params = self.params[product]
            product_orders: List[Order] = []

            # 1. Calculate Fair Value
            fair_value = self.calculate_fair_value(product, order_depth)

            if fair_value is None:
                print(f"Warning: Could not calculate fair value for {product}. Skipping orders.")
                result[product] = []
                continue # Skip order generation if fair value is unknown

            print(f"--- {product} --- Pos: {current_position}, Fair Value: {fair_value:.2f}")


            # 2. Generate Taking Orders (if enabled)
            if params.get("take_enabled", False):
                take_orders = self.generate_take_orders(
                    product, order_depth, fair_value, current_position
                )
                product_orders.extend(take_orders)

            if params.get("make_enabled", False):
                 make_orders = self.generate_make_orders(
                     product, order_depth, fair_value, current_position
                 )
                 product_orders.extend(make_orders)


            result[product] = product_orders

            self.update_trader_state(product, order_depth)


       
        traderData = self.save_state()

        logger.flush(state, result, conversions, traderData) 
        return result, conversions, traderData