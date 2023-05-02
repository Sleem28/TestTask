from binance import AsyncClient
import pandas as pd


class Analizer:
    """ This class contains a various methods for analyzing a trading information. """
    async def __get_last_candles(self, client: AsyncClient, symbol: str, tf: str) -> pd.DataFrame:
        """ Return a dataframe with last candles. """
        global last_candle
        start_str = self.__get_start_param__(tf=tf)

        while True:
            req = await client.futures_historical_klines(symbol, tf, start_str)
            if not req:
                continue
            else:
                last_candle = pd.DataFrame(req)
                break

        last_candle = last_candle.iloc[:, :6]
        last_candle.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        last_candle = last_candle.astype(float)
        return last_candle

    def kline_tf_to_int_minutes(self, tf: str) -> int:
        """ Converting the AsyncClient.KLINE_INTERVAL to the int value. """
        match tf:
            case AsyncClient.KLINE_INTERVAL_1MINUTE:
                return 1
            case AsyncClient.KLINE_INTERVAL_5MINUTE:
                return 5
            case AsyncClient.KLINE_INTERVAL_15MINUTE:
                return 15
            case _:
                return 0

    def __get_start_param__(self, tf: str) -> str:
        """ Returns how many candles needs to return. """
        match tf:
            case AsyncClient.KLINE_INTERVAL_1MINUTE:
                return '50m UTC'
            case AsyncClient.KLINE_INTERVAL_5MINUTE:
                return '4h UTC'
            case AsyncClient.KLINE_INTERVAL_15MINUTE:
                return '12h UTC'
            case _:
                return '1d UTC'

    async def get_last_bear_candle_params(self, client: AsyncClient, symbol: str, tf: str) -> dict:
        """ Returns a dictionary with the open of the last bearish candle and the swing's max volume from the
        DateFrame."""
        last_cdls = await self.__get_last_candles(client, symbol, tf)
        last_bear_candle = last_cdls[last_cdls['Open'] > last_cdls['Close']].tail(1)
        s_low = last_bear_candle['Low'].values[0]
        s_volume = last_bear_candle['Volume'].values[0]
        s_time = last_bear_candle['Time'].values[0]
        swing_max_volume = last_cdls[last_cdls['Time'].values >= s_time]['Volume'].values.max()
        return {'last_bear_candle_low': s_low,
                'last_bear_candle_volume': s_volume,
                'last_bear_candle_time': s_time,
                'swing_max_volume': swing_max_volume}

    def check_rollback(self, lbcw: float, cur_high: float, cur_price: float, rollback: float) -> bool:
        swing_height = cur_high - lbcw
        target_price = cur_high - (swing_height * rollback * 0.01)
        if cur_price <= target_price:
            print(f'{cur_price = }, {target_price = }')
        return True if cur_price <= target_price else False

    async def get_last_candle_params(self, client: AsyncClient, symbol: str, tf: str):
        prev_cdl = None
        while True:
            last_kline = await client.futures_historical_klines(symbol, tf, '3min ago UTC')

            if not last_kline:
                continue
            df = pd.DataFrame(last_kline)
            df = df.iloc[:, :6]
            df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            try:
                prev_cdl = df.iloc[1]
            except Exception as e:
                print(e)
                continue
            break

        return prev_cdl

