from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Trade, Observation, ProsperityEncoder
from typing import List
from statistics import mean, stdev
import json
from typing import Any



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


class Trader:
    
    def __init__(self):
        # Initialize state to track historical prices for each product
        self.historical_prices = {}
        self.ema = {}  # Pour stocker l'EMA par produit
        self.alpha = 0.4
        # Position tracking
        self.positions = {"RAINFOREST_RESIN": 0, "KELP": 0,"SQUID_INK" : 0}
        # Position limits
        self.position_limits = {"RAINFOREST_RESIN": 50, "KELP": 50,"SQUID_INK" : 50}
        
    def run(self, state: TradingState):
       
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        
        # Parse trader data if it exists
        if state.traderData and state.traderData != "":
            try:
                saved_data = eval(state.traderData)
                self.historical_prices = saved_data.get("prices", {})
                self.positions = saved_data.get("positions", {"RAINFOREST_RESIN": 0, "KELP": 0})
            except:
                pass
        
        # Update positions from state if available
        if state.position:
            for product, position in state.position.items():
                self.positions[product] = position
                
        result = {}
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            
            # Calculate acceptable price dynamically based on market data and product type
            acceptable_price = self.calculate_acceptable_price(product, order_depth)
            
            print(f"Product: {product}, Acceptable price: {acceptable_price}")
            print(f"Current position: {self.positions.get(product, 0)}/{self.position_limits.get(product, 50)}")
            print(f"Buy Order depth: {len(order_depth.buy_orders)}, Sell order depth: {len(order_depth.sell_orders)}")
    
           
            if len(order_depth.sell_orders) != 0:
                # Sort sell orders by price (lowest first)
                sorted_sells = sorted(order_depth.sell_orders.items())
                
                # Process all sell orders that are below our acceptable price
                for ask_price, ask_volume in sorted_sells:
                    # Check if buying would exceed position limit
                    max_buy_volume = self.position_limits.get(product, 50) - self.positions.get(product, 0)
                    
                    if int(ask_price) < acceptable_price and max_buy_volume > 0:
                        if product == "SQUID_INK":
                            buy_volume = 1
                        else :
                            buy_volume = int(min(-ask_volume, max_buy_volume))
                        if buy_volume > 0:
                            print(f"BUY {buy_volume}x {ask_price}")
                            orders.append(Order(product, ask_price, buy_volume))
                            # Update our position tracking
                            self.positions[product] = self.positions.get(product, 0) + buy_volume
    
     
            if len(order_depth.buy_orders) != 0:
                sorted_buys = sorted(order_depth.buy_orders.items(), reverse=True)
                for bid_price, bid_volume in sorted_buys:
                    # Check if selling would exceed negative position limit
                    max_sell_volume = self.positions.get(product, 0) + self.position_limits.get(product, 50)
                    
                    if int(bid_price) > acceptable_price and max_sell_volume > 0:
                        sell_volume = min(bid_volume, max_sell_volume) ## Best strategy so far : Sell everything
                        if sell_volume > 0:
                            print(f"SELL {sell_volume}x {bid_price}")
                            orders.append(Order(product, bid_price, -sell_volume))
                            # Update our position tracking
                            self.positions[product] = self.positions.get(product, 0) - sell_volume
            
            result[product] = orders
            
            # Update historical prices for this product
            self.update_historical_prices(product, order_depth)
    
        # Store historical prices and positions in trader data for next round
        traderData = str({"prices": self.historical_prices, "positions": self.positions})
        
        conversions = 0  # No conversions in this simple strategy
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData
    
    def calculate_acceptable_price(self, product, order_depth):
        """Calculate a dynamic acceptable price based on market data and product type"""
        if product == "KELP":
            default_price = 2023
        elif product == "SQUID_INK":
            default_price = 1973
        elif product == "RAINFOREST_RESIN":
            default_price = 10000
        
        
        
        # Get current market prices
        buy_prices = list(order_depth.buy_orders.keys()) if order_depth.buy_orders else []
        sell_prices = list(order_depth.sell_orders.keys()) if order_depth.sell_orders else []
        
        # Different strategies based on product
        if product == "RAINFOREST_RESIN":
            if product in self.historical_prices and len(self.historical_prices[product]) >= 5:
                hist_mean = mean(self.historical_prices[product])
                return hist_mean
            elif buy_prices and sell_prices:
                return (max(buy_prices) + min(sell_prices)) / 2
            else:
                return default_price
                
        if product == "KELP":
            # Compute volume-weighted mid price using all bids + asks
            total_bid = sum(price * vol for price, vol in order_depth.buy_orders.items())
            total_ask = sum(price * abs(vol) for price, vol in order_depth.sell_orders.items())
            vol_bid = sum(order_depth.buy_orders.values())
            vol_ask = sum(abs(v) for v in order_depth.sell_orders.values())
            
            if vol_bid + vol_ask > 0:
                mid = (total_bid + total_ask) / (vol_bid + vol_ask)
            else:
                mid = self.ema.get(product, default_price)
                
            # Update EMA
            if product not in self.ema:
                self.ema[product] = mid
            else:
                self.ema[product] = self.alpha * mid + (1 - self.alpha) * self.ema[product]
                
            return self.ema[product]
            

        elif product == "SQUID_INK":
            total_bid = sum(price * vol for price, vol in order_depth.buy_orders.items())
            total_ask = sum(price * abs(vol) for price, vol in order_depth.sell_orders.items())
            vol_bid = sum(order_depth.buy_orders.values())
            vol_ask = sum(abs(v) for v in order_depth.sell_orders.values())
            
            if vol_bid + vol_ask > 0:
                vwap = (total_bid + total_ask) / (vol_bid + vol_ask)    
                return vwap
            else:
                return default_price
            

    
    def update_historical_prices(self, product, order_depth):
        """Update historical price data for a product"""
        # Initialize if this is a new product
        if product not in self.historical_prices:
            self.historical_prices[product] = []
        
        # Add current mid prices to historical data
        buy_prices = list(order_depth.buy_orders.keys()) if order_depth.buy_orders else []
        sell_prices = list(order_depth.sell_orders.keys()) if order_depth.sell_orders else []
        
        if buy_prices and sell_prices:
            mid_price = (max(buy_prices) + min(sell_prices)) / 2
            max_history = 30 if product == "KELP" else 20
            self.historical_prices[product] = (self.historical_prices[product] + [mid_price])[-max_history:]