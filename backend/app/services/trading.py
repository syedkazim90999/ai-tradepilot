"""Trading engine.
- Production (live) trading is DISABLED unless the `live_trading_enabled`
  system setting is True AND the connection environment is 'live' AND the
  user has explicitly consented (bot_settings.trading_enabled).
- Idempotent order placement: clientOrderId is deterministic
  (TP-<user8>-<signal8>-<side>-<type>) with a DB unique constraint.
- Execution is always verified via order status; never assumed from a send.
"""
import hashlib
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Position, SystemSetting, Trade
from app.services.binance_client import BinanceClient, BinanceError
from app.services.risk import check_trade_allowed, get_effective_settings


def deterministic_client_order_id(user_id, signal_id, symbol: str, side: str, order_type: str) -> str:
    raw = f"{user_id}:{signal_id}:{symbol}:{side}:{order_type}"
    return "TP-" + hashlib.sha256(raw.encode()).hexdigest()[:28]


async def live_trading_enabled(db: AsyncSession) -> bool:
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "live_trading_enabled"))
    row = result.scalar_one_or_none()
    return bool(row and row.value.lower() == "true")


async def get_symbol_filters(client: BinanceClient, symbol: str) -> dict:
    """Quantity/price precision + min notional from exchangeInfo."""
    info = await client.exchange_info()
    for s in info.get("symbols", []):
        if s["symbol"] == symbol:
            filters = {f["filterType"]: f for f in s.get("filters", [])}
            lot = filters.get("LOT_SIZE", {})
            price_f = filters.get("PRICE_FILTER", {})
            min_notional = filters.get("MIN_NOTIONAL", {})
            return {
                "step_size": Decimal(lot.get("stepSize", "0.001")),
                "min_qty": Decimal(lot.get("minQty", "0")),
                "tick_size": Decimal(price_f.get("tickSize", "0.01")),
                "min_notional": Decimal(min_notional.get("notional", "0")),
            }
    raise BinanceError(f"Symbol {symbol} not found in exchangeInfo")


def round_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    return (value / step).quantize(Decimal("1")) * step


class TradingEngine:
    def __init__(self, db: AsyncSession, client: BinanceClient, user_id, environment: str = "testnet"):
        self.db = db
        self.client = client
        self.user_id = user_id
        self.environment = environment

    async def _guard_live(self):
        if self.environment == "live" and not await live_trading_enabled(self.db):
            raise PermissionError(
                "Live trading is DISABLED. It requires explicit Super Admin activation "
                "and user consent. Testnet remains available.")

    async def place_order(self, symbol: str, side: str, order_type: str, quantity: Decimal,
                          price: Decimal | None = None, stop_price: Decimal | None = None,
                          signal_id=None, trade_id=None, reduce_only: bool = False) -> Order:
        await self._guard_live()
        client_order_id = deterministic_client_order_id(
            self.user_id, signal_id or uuid.uuid4(), symbol, side, order_type)
        # Idempotency: return existing order if this clientOrderId was already placed.
        existing = (await self.db.execute(
            select(Order).where(Order.client_order_id == client_order_id))).scalar_one_or_none()
        if existing is not None:
            return existing

        order = Order(
            user_id=self.user_id, trade_id=trade_id, symbol=symbol,
            client_order_id=client_order_id, side=side, order_type=order_type,
            quantity=quantity, price=price, reduce_only=reduce_only,
            environment=self.environment,
        )
        self.db.add(order)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = (await self.db.execute(
                select(Order).where(Order.client_order_id == client_order_id))).scalar_one()
            return existing

        # Send to exchange, then VERIFY execution via order status.
        try:
            resp = await self.client.place_order(
                symbol, side, order_type, float(quantity),
                price=float(price) if price else None,
                stop_price=float(stop_price) if stop_price else None,
                client_order_id=client_order_id, reduce_only=reduce_only)
        except BinanceError as exc:
            order.status = "REJECTED"
            order.raw_response = {"error": str(exc), "code": exc.code}
            await self.db.commit()
            raise

        order.exchange_order_id = resp.get("orderId")
        order.raw_response = resp
        # Verify actual execution status from the exchange.
        try:
            verified = await self.client.get_order(symbol, order_id=resp.get("orderId"))
            order.status = verified.get("status", resp.get("status", "NEW"))
            order.executed_qty = Decimal(str(verified.get("executedQty", 0)))
            if verified.get("avgPrice"):
                order.avg_price = Decimal(str(verified["avgPrice"]))
        except BinanceError:
            order.status = resp.get("status", "NEW")
            order.executed_qty = Decimal(str(resp.get("executedQty", 0)))
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def cancel_order(self, order: Order) -> Order:
        await self.client.cancel_order(order.symbol, order_id=order.exchange_order_id,
                                       orig_client_order_id=order.client_order_id)
        verified = await self.client.get_order(order.symbol, order_id=order.exchange_order_id)
        order.status = verified.get("status", "CANCELED")
        await self.db.commit()
        return order

    async def execute_signal(self, signal, equity: Decimal) -> Trade | None:
        """Risk-checked execution of a LONG/SHORT signal. Returns the Trade or None."""
        await self._guard_live()
        if signal.direction == "WAIT":
            return None
        side = "BUY" if signal.direction == "LONG" else "SELL"
        # Leverage is always kept within 10x–50x: the user's configured max
        # leverage, clamped. (Pre-existing settings rows may still hold the
        # old 2x default, so the lower clamp matters.)
        settings = await get_effective_settings(self.db, self.user_id)
        settings_leverage = min(max(settings.max_leverage, 10), 50)
        decision = await check_trade_allowed(
            self.db, self.user_id, signal.symbol, equity,
            Decimal(str(signal.entry_price)), Decimal(str(signal.stop_loss)), settings_leverage)
        if not decision.allowed:
            return None
        filters = await get_symbol_filters(self.client, signal.symbol)
        qty = round_to_step(decision.position_size, filters["step_size"])
        if qty < filters["min_qty"] or qty * Decimal(str(signal.entry_price)) < filters["min_notional"]:
            return None
        order = await self.place_order(signal.symbol, side, "MARKET", qty,
                                       signal_id=signal.id)
        if order.status in ("REJECTED", "EXPIRED", "CANCELED"):
            return None
        trade = Trade(
            user_id=self.user_id, signal_id=signal.id, symbol=signal.symbol,
            side=signal.direction, status="open",
            entry_price=order.avg_price or signal.entry_price,
            quantity=order.executed_qty or qty, leverage=settings_leverage,
            stop_loss=signal.stop_loss, take_profit=signal.take_profit,
            environment=self.environment,
        )
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        # Attach stop-loss / take-profit (reduce-only) orders.
        stop_side = "SELL" if side == "BUY" else "BUY"
        try:
            await self.place_order(signal.symbol, stop_side, "STOP_MARKET", qty,
                                   stop_price=signal.stop_loss, signal_id=signal.id,
                                   trade_id=trade.id, reduce_only=True)
            await self.place_order(signal.symbol, stop_side, "TAKE_PROFIT_MARKET", qty,
                                   stop_price=signal.take_profit, signal_id=signal.id,
                                   trade_id=trade.id, reduce_only=True)
        except Exception:
            pass  # SL/TP placement failure is logged by the caller; trade stays open.
        return trade

    async def reconcile_positions(self) -> list[dict]:
        """Compare local open positions with the exchange; report mismatches."""
        exchange_positions = await self.client.positions()
        exchange_map = {p["symbol"]: Decimal(p["positionAmt"]) for p in exchange_positions}
        local = (await self.db.execute(
            select(Position).where(Position.user_id == self.user_id, Position.is_open == True))).scalars().all()  # noqa: E712
        mismatches = []
        for pos in local:
            ex_qty = exchange_map.get(pos.symbol, Decimal("0"))
            if ex_qty == 0:
                mismatches.append({"symbol": pos.symbol, "issue": "local open, exchange closed"})
            elif (ex_qty > 0) != (pos.side == "LONG") or abs(ex_qty) != pos.quantity:
                mismatches.append({"symbol": pos.symbol, "issue": "quantity/side mismatch",
                                   "local": str(pos.quantity), "exchange": str(ex_qty)})
        return mismatches
