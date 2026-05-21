# IMC Prosperity 3 — Sir Trades A Lot

Algorithmic trading competition by IMC. Source code and analysis notebooks for each round.

## Structure

```
tutorial_round/   # Warmup
Round_1/          # RAINFOREST_RESIN, KELP, SQUID_INK
Round_2/          # + CROISSANTS, JAMS, DJEMBES, PICNIC_BASKET
Round_3/          # + VOLCANIC_ROCK & vouchers
Round_4/          # + MAGNIFICENT_MACARONS
Round_5/          # All products — final submission
```

Each folder contains a `trader.py` (submitted algorithm) and analysis notebooks.

## How it works

Each iteration, the engine calls `Trader.run(state: TradingState)` with the current order book and recent trades. The algorithm places orders to match bot quotes or leaves resting quotes for bots to fill. Positions are tracked per product and must stay within hard limits — breaching them cancels all orders for that iteration.

## License

MIT 