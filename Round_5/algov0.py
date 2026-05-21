from datamodel import OrderDepth, UserId, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List, Dict, Any
import string
import json
import jsonpickle
from math import log, sqrt, exp, erf, pi
import math
import numpy as np


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

    def print(self, *objects, sep: str = " ", end: str = "\n") -> None:
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

    def compress_state(self, state: TradingState, trader_data: str) -> list:
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

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list]:
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

    def compress_observations(self, observations: Observation) -> list:
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

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()


class Product:
    VOLCANIC_ROCK = "VOLCANIC_ROCK"
    VOLCANIC_ROCK_VOUCHER_9500 = "VOLCANIC_ROCK_VOUCHER_9500"
    VOLCANIC_ROCK_VOUCHER_9750 = "VOLCANIC_ROCK_VOUCHER_9750"
    VOLCANIC_ROCK_VOUCHER_10000 = "VOLCANIC_ROCK_VOUCHER_10000"
    VOLCANIC_ROCK_VOUCHER_10250 = "VOLCANIC_ROCK_VOUCHER_10250"
    VOLCANIC_ROCK_VOUCHER_10500 = "VOLCANIC_ROCK_VOUCHER_10500"



PARAMS = {
    
    Product.VOLCANIC_ROCK_VOUCHER_9500: {
        "mean_volatility": 0.119077,
        
        "strike": 9500, 
        "starting_time_to_expiry": 7 / 365,
        "std_window": 6,
        "z_score_threshold": 21,
    },
    Product.VOLCANIC_ROCK_VOUCHER_9750: {
        "mean_volatility": 0.147417,
        # "threshold": 0,
        "strike": 10000,
        "starting_time_to_expiry": 7 / 365,
        "std_window": 6,
    },
    Product.VOLCANIC_ROCK_VOUCHER_10000: {
        "mean_volatility": 0.140554,
        "strike": 10000,
        "starting_time_to_expiry": 7 / 365,
        "std_window": 6,
    },
    Product.VOLCANIC_ROCK_VOUCHER_10250: {
        "mean_volatility": 0.128666,
        "strike": 10000,
        "starting_time_to_expiry": 7 / 365,
        "std_window": 6,
    },
    Product.VOLCANIC_ROCK_VOUCHER_10500: {
        "mean_volatility": 0.127146,
        # "threshold": 0.0552,
        "strike": 10000,
        "starting_time_to_expiry": 7 / 365,
        "std_window": 6,
    }

}




class Trader:
    def __init__(self, params=None):
        if params is None:
            params = PARAMS

        self.params = params
        self.PRODUCT_LIMIT = {
                              Product.VOLCANIC_ROCK: 400,
                              Product.VOLCANIC_ROCK_VOUCHER_9500: 200,
                              Product.VOLCANIC_ROCK_VOUCHER_9750: 200,
                              Product.VOLCANIC_ROCK_VOUCHER_10000: 200,
                              Product.VOLCANIC_ROCK_VOUCHER_10250: 200,
                              Product.VOLCANIC_ROCK_VOUCHER_10500: 200,
                    }


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

    def implied_vol_call(self, market_price, S, K, T_days, r, tol=0.00000000000001, max_iter=250):
        """
        Calculate implied volatility from market call option price using bisection.

        Parameters:
        - market_price: observed market price of the option
        - S: spot price
        - K: strike price
        - T_days: time to maturity in days
        - r: risk-free interest rate
        - tol: convergence tolerance
        - max_iter: maximum number of iterations

        Returns:
        - Implied volatility (sigma)
        """
        # Set reasonable initial bounds
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
        """
        Calculate the Black-Scholes delta of a European call option.

        Parameters:
        - S: Current stock price
        - K: Strike price
        - T: Time to maturity (in days)
        - r: Risk-free interest rate
        - sigma: Volatility (annual)

        Returns:
        - delta: Call option delta
        """
        r = 0
        T = T / 365
        if T == 0 or sigma == 0:
            return 1.0 if S > K else 0.0

        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        return 0.5 * (1 + math.erf(d1 / math.sqrt(2)))

    def trade_10000(self, state, market_data, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_10000"
        delta_sum = 0
        orders = {}
        for p in ["VOLCANIC_ROCK", "VOLCANIC_ROCK_VOUCHER_10000"]:
            orders[p] = []
        fair = market_data.fair[product]
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1_000_000
        v_t = self.implied_vol_call(fair, underlying_fair, 10000, dte, 0)
        delta = self.call_delta(fair, underlying_fair, dte, v_t)
        m_t = np.log(10000 / underlying_fair) / np.sqrt(dte / 365)
        

        
        base_coef = 0.14786181  
        linear_coef = 0.00099561 
        squared_coef = 0.23544086  
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
                rock_amount = amount

                # print(rock_amount)
                '''for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK"])):
                    fill = min(-market_data.ask_volumes["VOLCANIC_ROCK"][i], rock_amount)
                    #print(fill)
                    if fill != 0:
                        orders["VOLCANIC_ROCK"].append(Order("VOLCANIC_ROCK", market_data.ask_prices["VOLCANIC_ROCK"][i], fill))
                        market_data.buy_sum["VOLCANIC_ROCK"] -= fill
                        market_data.end_pos["VOLCANIC_ROCK"] += fill
                        rock_amount -= fill
                        #print(fill)'''

                for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_10000"])):
                    fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10000"][i], option_amount)
                    delta_sum -= delta * fill
                    if fill != 0:
                        orders["VOLCANIC_ROCK_VOUCHER_10000"].append(Order("VOLCANIC_ROCK_VOUCHER_10000",
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
                rock_amount = amount
                # print(f"{rock_amount} rocks")
                for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK_VOUCHER_10000"])):
                    fill = min(-market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_10000"][i], option_amount)
                    delta_sum += delta * fill
                    if fill != 0:
                        orders["VOLCANIC_ROCK_VOUCHER_10000"].append(Order("VOLCANIC_ROCK_VOUCHER_10000",
                                                                           market_data.ask_prices[
                                                                               "VOLCANIC_ROCK_VOUCHER_10000"][i], fill))
                        market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_10000"] -= fill
                        market_data.end_pos["VOLCANIC_ROCK_VOUCHER_10000"] += fill
                        option_amount -= fill

                '''for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK"])):
                        fill = min(market_data.bid_volumes["VOLCANIC_ROCK"][i], rock_amount)
                        #print(fill)
                        if fill != 0:
                            orders["VOLCANIC_ROCK"].append(Order("VOLCANIC_ROCK", market_data.bid_prices["VOLCANIC_ROCK"][i], -fill))
                            market_data.sell_sum["VOLCANIC_ROCK"] -= fill
                            market_data.end_pos["VOLCANIC_ROCK"] -= fill
                            rock_amount -= fill'''

        return orders["VOLCANIC_ROCK_VOUCHER_10000"]

    def trade_10500(self, state, market_data, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_10500"
        delta_sum = 0
        orders = {}
        for p in ["VOLCANIC_ROCK", "VOLCANIC_ROCK_VOUCHER_10500"]:
            orders[p] = []
        fair = market_data.fair[product]
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1_000_000
        v_t = self.implied_vol_call(fair, underlying_fair, 10500, dte, 0)
        try:
            delta = self.call_delta(fair, underlying_fair, dte, v_t)
        except:
            return [], []
        m_t = np.log(10500 / underlying_fair) / np.sqrt(dte / 365)
        # print(f"m_t = {m_t}")

        # , ,
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
        threshold = 0.001
        if diff > threshold:  # short vol so sell option, buy und
            amount = min(market_data.buy_sum["VOLCANIC_ROCK"], market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_10500"])
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10500"]))
            option_amount = amount
            if np.mean(traderObject["prices_10500"]) > 0:
                rock_amount = amount
            else:
                rock_amount = amount // 2

            # print(rock_amount)
            for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK"])):
                fill = min(-market_data.ask_volumes["VOLCANIC_ROCK"][i], rock_amount)
                # print(fill)
                if fill != 0:
                    orders["VOLCANIC_ROCK"].append(
                        Order("VOLCANIC_ROCK", market_data.ask_prices["VOLCANIC_ROCK"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK"] += fill
                    rock_amount -= fill
                    # print(fill)

            for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_10500"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_10500"][i], option_amount)
                delta_sum -= delta * fill
                if fill != 0:
                    orders["VOLCANIC_ROCK_VOUCHER_10500"].append(Order("VOLCANIC_ROCK_VOUCHER_10500",
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
                    orders["VOLCANIC_ROCK_VOUCHER_10500"].append(Order("VOLCANIC_ROCK_VOUCHER_10500",
                                                                       market_data.ask_prices[
                                                                           "VOLCANIC_ROCK_VOUCHER_10500"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_10500"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_10500"] += fill
                    option_amount -= fill

            """ for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK"][i], rock_amount)
                # print(fill)
                if fill != 0:
                    orders["VOLCANIC_ROCK"].append(
                        Order("VOLCANIC_ROCK", market_data.bid_prices["VOLCANIC_ROCK"][i], -fill))
                    market_data.sell_sum["VOLCANIC_ROCK"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK"] -= fill
                    rock_amount -= fill """

        return orders["VOLCANIC_ROCK"], orders["VOLCANIC_ROCK_VOUCHER_10500"]

    def trade_9500(self, state, market_data, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_9500"
        delta_sum = 0
        orders = {}
        for p in ["VOLCANIC_ROCK", "VOLCANIC_ROCK_VOUCHER_9500"]:
            orders[p] = []
        fair = market_data.fair[product]
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1_000_000
        v_t = self.implied_vol_call(fair, underlying_fair, 9500, dte, 0)
        try:
            delta = self.call_delta(fair, underlying_fair, dte, v_t)
        except:
            return [], []
        m_t = np.log(9500 / underlying_fair) / np.sqrt(dte / 365)
        base_coef = 0.264416  # 0.13571776890273662 + 0.00229274*dte
        linear_coef = 0.010031  # -0.03685812200491957 + 0.0072571*dte
        squared_coef = 0.147604  # 0.16277746617792221 + 0.01096456*dte
        fair_iv = base_coef + linear_coef * m_t + squared_coef * (m_t ** 2)
        # print(fair_iv)

        diff = v_t - fair_iv
        if "prices_9500" not in traderObject:
            traderObject["prices_9500"] = [diff]
        else:
            traderObject["prices_9500"].append(diff)
        # print(diff)
        if len(traderObject["prices_9500"]) > 13:
            diff -= np.mean(traderObject["prices_9500"])
            traderObject["prices_9500"].pop(0)
        threshold = 0.0005
        if diff > threshold:  
            amount = min(market_data.buy_sum["VOLCANIC_ROCK"], market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_9500"])
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_9500"]))
            option_amount = amount
            rock_amount = amount
            for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK"])):
                fill = min(-market_data.ask_volumes["VOLCANIC_ROCK"][i], rock_amount)
                if fill != 0:
                    orders["VOLCANIC_ROCK"].append(
                        Order("VOLCANIC_ROCK", market_data.ask_prices["VOLCANIC_ROCK"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK"] += fill
                    rock_amount -= fill

            for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_9500"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_9500"][i], option_amount)
                delta_sum -= delta * fill
                if fill != 0:
                    orders["VOLCANIC_ROCK_VOUCHER_9500"].append(Order("VOLCANIC_ROCK_VOUCHER_9500",
                                                                      market_data.bid_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_9500"][i],
                                                                      -fill))
                    market_data.sell_sum["VOLCANIC_ROCK_VOUCHER_9500"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_9500"] -= fill
                    option_amount -= fill

        elif diff < -threshold:  
            amount = min(market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_9500"], market_data.sell_sum["VOLCANIC_ROCK"])
            # print(amount)
            amount = min(amount, -sum(market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_9500"]),
                         sum(market_data.bid_volumes["VOLCANIC_ROCK"]))
            # print(amount)
            option_amount = amount
            rock_amount = amount

            for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK_VOUCHER_9500"])):
                fill = min(-market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_9500"][i], option_amount)
                delta_sum += delta * fill
                if fill != 0:
                    orders["VOLCANIC_ROCK_VOUCHER_9500"].append(Order("VOLCANIC_ROCK_VOUCHER_9500",
                                                                      market_data.ask_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_9500"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_9500"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_9500"] += fill
                    option_amount -= fill

            """ for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK"][i], rock_amount)
                # print(fill)
                if fill != 0:
                    orders["VOLCANIC_ROCK"].append(
                        Order("VOLCANIC_ROCK", market_data.bid_prices["VOLCANIC_ROCK"][i], -fill))
                    market_data.sell_sum["VOLCANIC_ROCK"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK"] -= fill
                    rock_amount -= fill """

        return  orders["VOLCANIC_ROCK_VOUCHER_9500"]

    def trade_9750(self, state, market_data, traderObject):
        product = "VOLCANIC_ROCK_VOUCHER_9750"
        orders = {}
        for p in ["VOLCANIC_ROCK", "VOLCANIC_ROCK_VOUCHER_9750"]:
            orders[p] = []
        fair = market_data.fair[product]
        underlying_fair = market_data.fair["VOLCANIC_ROCK"]
        dte = DAYS_LEFT - state.timestamp / 1_000_000

        v_t = self.implied_vol_call(fair, underlying_fair, 9750, dte, 0)
        m_t = np.log(9750 / underlying_fair) / np.sqrt(dte / 365)
        # print(f"m_t = {m_t}")

        # , ,
        base_coef = 0.264416  
        linear_coef = 0.010031  
        squared_coef = 0.147604  
        fair_iv = base_coef + linear_coef * m_t + squared_coef * (m_t ** 2)
        # print(fair_iv)
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

            rock_amount = amount

            for i in range(0, len(market_data.bid_prices["VOLCANIC_ROCK_VOUCHER_9750"])):
                fill = min(market_data.bid_volumes["VOLCANIC_ROCK_VOUCHER_9750"][i], option_amount)
                if fill != 0:
                    orders["VOLCANIC_ROCK_VOUCHER_9750"].append(Order("VOLCANIC_ROCK_VOUCHER_9750",
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
            rock_amount = amount
            # print(f"{rock_amount} rocks")
            for i in range(0, len(market_data.ask_prices["VOLCANIC_ROCK_VOUCHER_9750"])):
                fill = min(-market_data.ask_volumes["VOLCANIC_ROCK_VOUCHER_9750"][i], option_amount)
                if fill != 0:
                    orders["VOLCANIC_ROCK_VOUCHER_9750"].append(Order("VOLCANIC_ROCK_VOUCHER_9750",
                                                                      market_data.ask_prices[
                                                                          "VOLCANIC_ROCK_VOUCHER_9750"][i], fill))
                    market_data.buy_sum["VOLCANIC_ROCK_VOUCHER_9750"] -= fill
                    market_data.end_pos["VOLCANIC_ROCK_VOUCHER_9750"] += fill
                    option_amount -= fill

            
        return orders["VOLCANIC_ROCK_VOUCHER_9750"]
    def calculate_sunlight_rate_of_change(self,traderObject):
        """Calculate the average rate of change of sunlight over the last 5 ticks
        :param traderObject:
        """
        if len(traderObject["sunlight_history"]) < 5:
            return 0
        changes = []
        for i in range(1, len(traderObject["sunlight_history"])):
            changes.append(traderObject["sunlight_history"][i] - traderObject["sunlight_history"][i - 1])
        return sum(changes) / len(changes)

   

    def run(self, state: TradingState):
        traderObject = {}
        result = {}
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
            market_data.buy_sum[product] = self.PRODUCT_LIMIT[product] - position
            market_data.sell_sum[product] = self.PRODUCT_LIMIT[product] + position
            market_data.bid_prices[product] = list(bids.keys())
            market_data.bid_volumes[product] = list(bids.values())
            market_data.ask_prices[product] = list(asks.keys())
            market_data.ask_volumes[product] = list(asks.values())
            market_data.fair[product] = fair_price

        result = {}
        result[Product.VOLCANIC_ROCK_VOUCHER_9500] =self.trade_9500(state,market_data,traderObject)
        result[Product.VOLCANIC_ROCK_VOUCHER_9750] = self.trade_9750(state, market_data, traderObject)
        result[Product.VOLCANIC_ROCK_VOUCHER_10000] = self.trade_10000(state, market_data, traderObject)
        result[Product.VOLCANIC_ROCK_VOUCHER_10500] = self.trade_10500(state, market_data, traderObject)
        

    

        traderData = jsonpickle.encode(traderObject)
        logger.flush(state, result, 0, traderData)

        return result, 0, traderData
