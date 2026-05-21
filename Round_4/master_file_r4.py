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
    HYDROGEL_PACK       = "HYDROGEL_PACK"
    VELVETFRUIT_EXTRACT = "VELVETFRUIT_EXTRACT"

# ── Options : vouchers call européens sur VELVETFRUIT_EXTRACT ──────────────
# Strikes disponibles, IV calibrée sur données historiques (jours 0-2).
# IV unifiée 0.243 — plus robuste que per-strike sur 3 jours de données.
# TTE = 5 jours au début du round 3 ; décroît à chaque tick.
# VEV_6000 / VEV_6500 : mid ~0.5 → quote_volume = 0 (pas d'edge).

VOUCHER_STRIKES: dict[str, int] = {
    "VEV_4000": 4000, "VEV_4500": 4500,
    "VEV_5000": 5000, "VEV_5100": 5100,
    "VEV_5200": 5200, "VEV_5300": 5300,
    "VEV_5400": 5400, "VEV_5500": 5500,
    "VEV_6000": 6000, "VEV_6500": 6500,
}
# ── Options : position cible basée sur la distance S-K ───────────────────
# Inspiré de la stratégie Prosperity Round 4 (année dernière) :
#   target = clamp( (S - K) // STEP * -STEP_QTY,  -limit, +limit )
# On vend les vouchers ITM proportionnellement à leur profondeur,
# et on reste flat sur les OTM.
# L'exécution se fait au mid du voucher (ordre agressif).
VOUCHER_STEP     = 25    # granularité de la distance S-K
VOUCHER_STEP_QTY = 10    # unités de position par step de 25
VOUCHER_LIMIT    = 300   # position limit pour tous les vouchers


PARAMS = {
    Product.HYDROGEL_PACK : {
        "position_limit": 200,
        "fair_value_method": "mean_reverting",
        "vwap_default_price": 10020, 
        "lookback": 20,
                
        # --- Market Taking Params ---
        "take_enabled": False,
        "take_width": 0,
        
        # --- Market Making Params ---
        "make_enabled": True,      
        "quote_volume": 20,
        "disregard_edge": 1,
        "join_edge": 1,
        "default_edge": 1       
    },

    # ── VELVETFRUIT_EXTRACT ───────────────────────────────────────────────
    # Mean reversion autour de 5250 (confirmé sur 3 jours d'historique).
    # VR(20) = 0.71, lag-1 ACF = -0.16  → signal mean-reverting clair.
    # Spread ~5 pts → même architecture que HYDROGEL, seuil plus serré.
    # Backtest 3 jours (pos limit 200) : ~77 k PnL.
    Product.VELVETFRUIT_EXTRACT: {
        "position_limit": 200,
        "fair_value_method": "mean_reverting",
        "mean_default_price": 5250,
        "lookback": 20,

        # --- Market Taking Params ---
        "take_enabled": False,
        "take_width": 0,

        # --- Market Making Params ---
        "make_enabled": True,
        "quote_volume": 20,
        "disregard_edge": 1,
        "join_edge": 1,
        "default_edge": 1,
    },

}

class Trader:
    


    def __init__(self, params=None):
        self.params = params if params is not None else PARAMS

        self.traderObject = {
            "historical_prices": {},
            "last_fair_value": {},
            
        }

    # --- State Management ---
    
    def load_state(self, state: TradingState):
        if state.traderData != None and state.traderData != "":
            try:
                self.traderObject = jsonpickle.decode(state.traderData)
                
                self.traderObject.setdefault("historical_prices", {})
                self.traderObject.setdefault("last_fair_value", {})
                
            except Exception as e:
                logger.print(f"Error loading traderData: {e}")
                # Initialize with default if loading fails
                self.traderObject = {
                    "historical_prices": {},
                    "last_fair_value": {},
                    "ramp_intercept": {},
                    "peak_price": {},
                    "stop_triggered": {},
                }

    def save_state(self) -> str:
        state_to_save = {
            "historical_prices": self.traderObject["historical_prices"],
            "last_fair_value": self.traderObject["last_fair_value"],
            
        }
        return jsonpickle.encode(state_to_save)

    def update_trader_state(self, product: str, order_depth: OrderDepth):
        params = self.params[product]
        
        hist_prices = self.traderObject["historical_prices"].setdefault(product, [])
        buy_prices = list(order_depth.buy_orders.keys()) if order_depth.buy_orders else []
        sell_prices = list(order_depth.sell_orders.keys()) if order_depth.sell_orders else []

        if buy_prices and sell_prices:
            mid_price = (max(buy_prices) + min(sell_prices)) / 2
            hist_prices.append(mid_price)
            
            max_history = params.get("lookback", 80) + 5
            self.traderObject["historical_prices"][product] = hist_prices[-max_history:]


    # --- Fair value calculation---

    def calculate_fair_value(self, product: str, order_depth: OrderDepth, timestamp: int) -> float | None:
        params = self.params[product]
        method = params["fair_value_method"]
        if method == "vwap_ema":
            return self._fair_value_vwap_ema(product, order_depth, params)
        elif method == "mean_reverting":
            return self.fair_value_mean_reverting(product)
        
        

        

        else:
            logger.print(f"Warning: Unknown fair_value_method '{method}' for {product}")
            return None
        
    def fair_value_mean_reverting(self, product: str):
        prices = self.traderObject["historical_prices"].get(product, [])
        lookback = self.params[product].get("lookback", 20)
        
        if len(prices) < lookback:
            return sum(prices) / len(prices) if prices else self.params[product].get("mean_default_price", 10020)

        window = prices[-lookback:]

        return sum(window) / len(window)
        
    def _calculate_vwap(self,product : str, order_depth: OrderDepth, min_volume_threshold: int = 2) -> float | None:
      
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
        if total_volume == 0:
            return base_vwap

        imbalance = (bid_pressure - ask_pressure) / total_volume

        typical_move = 2
        adjustment = typical_move * (2 / (1 + math.exp(-5 * imbalance)) - 1)

        return base_vwap + adjustment

        
    def _fair_value_vwap_ema(self, product: str, order_depth: OrderDepth, params: Dict[str, Any]) -> float | None:


        # --- Safe state access ---
        ema_state = self.traderObject.setdefault("ema_state", {})
        last_ema = ema_state.get(product)

        # --- Parameters ---
        alpha = max(0.0, min(1.0, params.get("ema_alpha", 0.2)))
        default_price = params.get("vwap_default_price", 0.0)
        max_deviation = params.get("max_vwap_deviation", None)

        # --- Current signal ---
        current_vwap = self._calculate_vwap(product, order_depth)

        # --- Handle missing VWAP ---
        if current_vwap is None:
            if last_ema is not None:
                # Optional slow decay toward default
                decay = params.get("ema_decay", 0.01)
                new_ema = (1 - decay) * last_ema + decay * default_price
                ema_state[product] = new_ema
                return new_ema
            return default_price

        # --- Optional outlier clipping ---
        if last_ema is not None and max_deviation is not None:
            deviation = current_vwap - last_ema
            if abs(deviation) > max_deviation:
                current_vwap = last_ema + math.copysign(max_deviation, deviation)

        # --- EMA update ---
        if last_ema is None:
            new_ema = current_vwap
        else:
            new_ema = alpha * current_vwap + (1 - alpha) * last_ema

        # --- Store state ---
        ema_state[product] = new_ema

        return new_ema


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
                    
                    quantity = int(min(vol_to_buy, max_can_buy))

                    if quantity > 0:
                        logger.print(f"TAKE BUY {product}: {quantity}x {best_ask}")
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
                        logger.print(f"TAKE SELL {product}: {quantity}x {best_bid}")
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
            logger.print(f"MAKE {product}: Skipping, calculated bid {my_bid_price} >= ask {my_ask_price}")
            return orders 


        # --- Place Orders ---
        # Place Bid
        max_can_buy = position_limit - position
        bid_quantity = int(min(quote_volume, max_can_buy))
        # Only place if we have room and price is valid (doesn't cross market)
        if bid_quantity > 0 and my_bid_price < best_market_ask:
            logger.print(f"MAKE BID {product}: {bid_quantity}x {my_bid_price}")
            orders.append(Order(product, my_bid_price, bid_quantity))

        # Place Ask
        max_can_sell = position - (-position_limit) # position + position_limit
        ask_quantity = int(min(quote_volume, max_can_sell))
         # Only place if we have room and price is valid (doesn't cross market)
        if ask_quantity > 0 and my_ask_price > best_market_bid:
            logger.print(f"MAKE ASK {product}: {ask_quantity}x {my_ask_price}")
            orders.append(Order(product, my_ask_price, -ask_quantity)) # Sell orders have negative volume

        return orders



    def generate_option_orders(
        self,
        symbol: str,
        order_depth: OrderDepth,
        position: int,
        S: float,
    ) -> List[Order]:
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        K      = VOUCHER_STRIKES[symbol]
        diff   = S - K
        steps  = int(diff // VOUCHER_STEP)
        target = -steps * VOUCHER_STEP_QTY
        target = max(-VOUCHER_LIMIT, min(VOUCHER_LIMIT, target))

        delta  = target - position
        if delta == 0:
            return []

        best_bid = max(order_depth.buy_orders)
        best_ask = min(order_depth.sell_orders)
        mid_v    = int((best_bid + best_ask) / 2)

        logger.print(f"{symbol} S={S:.1f} K={K} steps={steps} target={target} pos={position} delta={delta}")
        return [Order(symbol, mid_v, delta)]

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self.load_state(state)
        result: Dict[str, List[Order]] = {}
        conversions = 0

        # Prix du sous-jacent lu une seule fois — utilisé par tous les vouchers
        vef_depth = state.order_depths.get(Product.VELVETFRUIT_EXTRACT)
        if vef_depth and vef_depth.buy_orders and vef_depth.sell_orders:
            S = (max(vef_depth.buy_orders) + min(vef_depth.sell_orders)) / 2.0
        else:
            S = 5250.0  # fallback

        for product in state.order_depths.keys():

            order_depth: OrderDepth = state.order_depths[product]
            current_position = state.position.get(product, 0)

            # ── Delta-1 : produits avec params dans PARAMS ──
            if product in self.params:
                params = self.params[product]
                product_orders_this_tick: List[Order] = []

                fair_value = self.calculate_fair_value(product, order_depth, state.timestamp)

                if fair_value is None:
                    logger.print(f"Impossible to calculate the fair value for {product}.")
                    result[product] = []
                    continue

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

            # ── Options : vouchers VEV_* ──
            elif product in VOUCHER_STRIKES:
                result[product] = self.generate_option_orders(
                    product, order_depth, current_position, S
                )

            else:
                logger.print(f"[SKIP] {product}")

        traderData = self.save_state()
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData