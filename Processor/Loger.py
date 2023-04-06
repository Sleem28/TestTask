import datetime
from pathlib import Path


class Loger:
    """Custom loger"""

    async def write_deal_to_file(self, symbol: str,
                                 cur_price: float,
                                 stop_loss: float,
                                 take_profit: float,
                                 quantity: float,
                                 trade_mode: str,
                                 reason: str):
        """
        This method writes an info about completed deal to the file.
        @param symbol: instrument
        @param cur_price: current price
        @param stop_loss: stop loss
        @param take_profit: take profit
        @param quantity: quantyty of the futures pair
        @param trade_mode: the deal's trade mode
        @param reason: the reason
        """
        path = Path('reports/deals.txt')
        date = datetime.datetime.now()
        info = f'Date: {date} Symbol: {symbol} Price: {cur_price}  SL: {stop_loss} TP: {take_profit} ' \
               f'Quantity: {quantity} Trade mode: {trade_mode} Reason: {reason}\n\n'
        with open(path, 'a') as writer:
            writer.write(info)

    async def write_pump_to_file(self, symbol: str,
                                 low_price: float,
                                 high_price: float,
                                 lbc_time: datetime):
        """
        This method writes an info about the founded pump to the file.
        @param symbol: symbol
        @param low_price: the lowest price of the pump
        @param high_price: the highest price of the pump
        @param lbc_time: the time which the pump was founded
        """
        path = Path('reports/pumps.txt')
        date = datetime.datetime.now()
        lbc_time = datetime.datetime.fromtimestamp(lbc_time / 1000)
        info = f'Date: {date} Symbol: {symbol} Low price: {low_price}  High price: {high_price}' \
               f' Last candle time: {lbc_time}\n\n'
        with open(path, 'a') as writer:
            writer.write(info)
