from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List, Dict
import jsonpickle
from typing import Any
import json

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

        # We truncate state.traderData, trader_data, and self.logs to fit the log limit
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

class Trader:
    def __init__(self):
        self.traderData = {}

        # All relevant voucher position limits (clamped to [-200, 200] here)
        # Add or remove strikes as needed.
        self.position_limit = {
            "VOLCANIC_ROCK_VOUCHER_9500": 200,
            "VOLCANIC_ROCK_VOUCHER_9750": 200,
            "VOLCANIC_ROCK_VOUCHER_10000": 200,
            "VOLCANIC_ROCK_VOUCHER_10250": 200,
            "VOLCANIC_ROCK_VOUCHER_10500": 200,
            "VOLCANIC_ROCK" : 400
        }

        # Map each voucher symbol to its strike price
        self.voucher_strikes = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }
    def calculate_delta_approx(self, underlying_price: float, strike_price: float) -> float:
        
        diff = underlying_price - strike_price
        itm_threshold = 20.0 #20
        otm_threshold = -100.0 #-50

        if diff >= itm_threshold:
            return 1.0 # Deep ITM
        elif diff <= otm_threshold:
            return 0.0 # Deep OTM
        else:
            return (diff - otm_threshold) / (itm_threshold - otm_threshold)

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """
        Stratégie:
        1. Applique la stratégie originale sur les options (vouchers).
        2. Calcule le delta total des positions *actuelles* en options.
        3. Calcule la position cible sur le sous-jacent (VOLCANIC_ROCK) pour hedger partiellement ce delta.
        4. Place les ordres pour les options ET pour le sous-jacent.
        """

        orders: Dict[str, List[Order]] = {}
        conversions = 0
        replication_coef=5

        # --- 1. Calcul du prix mid de VOLCANIC_ROCK ---
        if "VOLCANIC_ROCK" not in state.order_depths:
            logger.print("WARN: No order depth found for VOLCANIC_ROCK")
            return {}, 0, jsonpickle.encode(self.traderData)

        od_rock = state.order_depths["VOLCANIC_ROCK"]
        if not od_rock.buy_orders or not od_rock.sell_orders:
            logger.print("WARN: Incomplete order depth for VOLCANIC_ROCK")
            # Peut-être utiliser le dernier prix connu ou une autre estimation ?
            # Pour l'instant, on retourne sans trader si on n'a pas de mid-price fiable
            return {}, 0, jsonpickle.encode(self.traderData)

        best_bid_rock = max(od_rock.buy_orders.keys())
        best_ask_rock = min(od_rock.sell_orders.keys())
        rock_mid_price = (best_bid_rock + best_ask_rock) / 2

        # --- 2. Calcul des ordres pour les Vouchers (Stratégie Originale) ---
        for voucher_symbol, strike_price in self.voucher_strikes.items():
            orders[voucher_symbol] = [] # Initialise la liste d'ordres pour ce voucher

            # Vérifier la présence de l'order book du voucher
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

            # Calcul de l'ordre à passer pour le voucher
            current_position_voucher = state.position.get(voucher_symbol, 0)
            delta_position_voucher = target_position_voucher - current_position_voucher

            if delta_position_voucher == 0:
                continue # Pas d'ordre à passer

            
            best_bid_vouch = max(od_voucher.buy_orders.keys())
            best_ask_vouch = min(od_voucher.sell_orders.keys())
            mid_vouch = (best_bid_vouch+best_ask_vouch)/2

            if delta_position_voucher > 0: 
               
             
                orders[voucher_symbol].append(Order(voucher_symbol, int(mid_vouch), delta_position_voucher))
            else: 
                
                orders[voucher_symbol].append(Order(voucher_symbol, int(mid_vouch), delta_position_voucher))

       
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

        
        orders["VOLCANIC_ROCK"] = [] 
        current_position_underlying = state.position.get("VOLCANIC_ROCK", 0)
        delta_position_underlying = target_replication_position - current_position_underlying

        if delta_position_underlying != 0:
           
            if delta_position_underlying > 0: 
                price = int(rock_mid_price)
                orders["VOLCANIC_ROCK"].append(Order("VOLCANIC_ROCK", int(price), delta_position_underlying))
            else: # Vendre
                price = rock_mid_price
                orders["VOLCANIC_ROCK"].append(Order("VOLCANIC_ROCK", int(price), delta_position_underlying))
            logger.print(f"HEDGING: Total Option Delta={total_current_delta:.2f}, Target Hedge Pos={target_replication_position}, Current Hedge Pos={current_position_underlying}, Order Hedge Qty={delta_position_underlying}")
        else:
            logger.print(f"HEDGING: Total Option Delta={total_current_delta:.2f}, Target Hedge Pos={target_replication_position}, Current Hedge Pos={current_position_underlying}. No Hedge Order Needed.")


        # --- Finalisation ---
        trader_data_out = jsonpickle.encode(self.traderData) # Sauvegarder l'état si nécessaire
        logger.flush(state, orders, conversions, trader_data_out)
        return orders, conversions, trader_data_out