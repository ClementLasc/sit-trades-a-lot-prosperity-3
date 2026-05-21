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

        # Position limits remain the same
        self.position_limit = {
            "VOLCANIC_ROCK_VOUCHER_9500": 200,
            "VOLCANIC_ROCK_VOUCHER_9750": 200,
            "VOLCANIC_ROCK_VOUCHER_10000": 200,
            "VOLCANIC_ROCK_VOUCHER_10250": 200,
            "VOLCANIC_ROCK_VOUCHER_10500": 200,
            "VOLCANIC_ROCK" : 400
        }

        # Voucher strikes remain the same
        self.voucher_strikes = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }

    # --- Paramètres de la Stratégie Market Maker Deep OTM ---
        self.target_otm_symbol = "VOLCANIC_ROCK_VOUCHER_10500" # Cible principale
        self.target_otm_strike = 10500

        # Prix statiques pour Bid et Ask (basé sur l'observation du graph)
        # IMPORTANT: Le prix 0 n'est peut-être pas valide, utiliser 1 si nécessaire.
        self.target_bid_price = 0  # Mettre 1 si 0 n'est pas permis
        self.target_ask_price = 1  # Viser à vendre à 1 (ou 2?)

        self.quote_size = 10       # Quantité pour chaque ordre Bid/Ask
        self.max_inventory = 50    # Position nette max (longue ou courte) sur l'option cible

        # Seuil de sécurité: arrêter si S se rapproche trop du strike OTM
        self.safety_underlying_threshold = self.target_otm_strike - 100 # Ex: Stop si S > 10400

    # Pas besoin de calcul de delta complexe pour cette version simplifiée
    # def calculate_delta_near_expiry(...): ...

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders: Dict[str, List[Order]] = {self.target_otm_symbol: []}
        conversions = 0

        # --- 1. Obtenir le prix du sous-jacent (S) ---
        rock_mid_price = 0.0
        # (Logique pour obtenir rock_mid_price - reprise d'avant)
        # ... [Copier la logique de récupération de rock_mid_price d'une version précédente] ...
        if "VOLCANIC_ROCK" in state.order_depths:
             od_rock = state.order_depths["VOLCANIC_ROCK"]
             if od_rock.buy_orders and od_rock.sell_orders:
                 best_bid_rock = max(od_rock.buy_orders.keys())
                 best_ask_rock = min(od_rock.sell_orders.keys())
                 rock_mid_price = (best_bid_rock + best_ask_rock) / 2

             else:
                  logger.print("ERROR: Cannot determine VOLCANIC_ROCK price. Skipping MM.")
                  return {}, 0, jsonpickle.encode(self.traderData)
        else:
             logger.print("ERROR: No order depth or last price for VOLCANIC_ROCK. Skipping MM.")
             return {}, 0, jsonpickle.encode(self.traderData)


        # --- 2. Vérification de Sécurité ---
        if rock_mid_price >= self.safety_underlying_threshold:
            logger.print(f"WARN: Underlying price {rock_mid_price} too close to OTM strike {self.target_otm_strike}. Stopping market making.")
            # Idéalement, ici on annulerait aussi les ordres existants
            return {}, 0, jsonpickle.encode(self.traderData) # Ne pas placer de nouveaux ordres

        # --- 3. Logique de Market Making sur l'Option Cible ---
        current_pos = state.position.get(self.target_otm_symbol, 0)
        final_orders = {} # Utiliser un dict temporaire pour les ordres finaux

        # --- Placement du Bid (Ordre d'Achat Limite) ---
        can_place_bid = True
        if current_pos >= self.max_inventory:
            logger.print(f"INFO: Max long inventory ({self.max_inventory}) reached for {self.target_otm_symbol}. Not placing BID.")
            can_place_bid = False

        # Vérifier aussi la limite de position générale (même si max_inventory devrait être plus petit)
        general_limit = self.position_limit.get(self.target_otm_symbol, 200)
        if current_pos + self.quote_size > general_limit:
             logger.print(f"INFO: General position limit ({general_limit}) prevents placing BID for {self.target_otm_symbol}.")
             can_place_bid = False

        if can_place_bid:
            bid_quantity = self.quote_size
            # S'assurer que la quantité ne dépasse pas max_inventory si on est proche
            if current_pos + bid_quantity > self.max_inventory:
                bid_quantity = self.max_inventory - current_pos

            if bid_quantity > 0:
                 if self.target_otm_symbol not in final_orders: final_orders[self.target_otm_symbol] = []
                 final_orders[self.target_otm_symbol].append(Order(self.target_otm_symbol, self.target_bid_price, bid_quantity))
                 logger.print(f"MM OTM: Placing BID for {bid_quantity} of {self.target_otm_symbol} at {self.target_bid_price}")


        # --- Placement de l'Ask (Ordre de Vente Limite) ---
        can_place_ask = True
        if current_pos <= -self.max_inventory:
             logger.print(f"INFO: Max short inventory ({-self.max_inventory}) reached for {self.target_otm_symbol}. Not placing ASK.")
             can_place_ask = False

        # Vérifier aussi la limite de position générale
        if current_pos - self.quote_size < -general_limit:
             logger.print(f"INFO: General position limit ({-general_limit}) prevents placing ASK for {self.target_otm_symbol}.")
             can_place_ask = False

        if can_place_ask:
            ask_quantity = -self.quote_size # Négatif pour vente
             # S'assurer que la quantité ne dépasse pas -max_inventory si on est proche
            if current_pos + ask_quantity < -self.max_inventory:
                ask_quantity = -self.max_inventory - current_pos # Ex: pos=-45, max=50 -> ask_qty=-50 - (-45) = -5

            if ask_quantity < 0:
                 if self.target_otm_symbol not in final_orders: final_orders[self.target_otm_symbol] = []
                 final_orders[self.target_otm_symbol].append(Order(self.target_otm_symbol, self.target_ask_price, ask_quantity))
                 logger.print(f"MM OTM: Placing ASK for {abs(ask_quantity)} of {self.target_otm_symbol} at {self.target_ask_price}")
        # --- Finalisation ---
        trader_data_out = jsonpickle.encode(self.traderData)
        # Assurez-vous que le logger est bien utilisé si nécessaire
        # logger.flush(state, final_orders, conversions, trader_data_out)
        return final_orders, conversions, trader_data_out