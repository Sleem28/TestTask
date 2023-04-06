from binance import AsyncClient
import pandas as pd


class FuturesGetter:

    async def get_all_futures(self, client) -> list:
        """
        This method finds symbol names from client.futures_exchange_info()
        @param client: AsyncClient
        @return: the list with the futures names
        """
        res = await client.futures_exchange_info()
        df = pd.DataFrame(res['symbols'])
        df = df[df.symbol.str.contains('USDT')]
        lst = list(df['symbol'])
        return lst
