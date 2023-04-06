import time
import pandas as pd
from Analize_classes import Analizer
from Trade_classes import TradeProcessor
from Processor import FuturesGetter
from Processor.Loger import Loger
from binance import AsyncClient, BinanceSocketManager
from keys import api_key, api_secret
from enums import SWING_TRADE, CATCH_KNIVES
import config
import asyncio


class MainProcessor:
    """Makes an analysis and trade in the async mode."""
    CLIENT: AsyncClient
    FG: FuturesGetter
    LOGER: Loger
    ANALIZER: Analizer
    TRADE_PROCESSOR: TradeProcessor
    F_SYMBOLS: list
    TASKS: list
    BM: BinanceSocketManager
    TF: str
    PUMP_HEIGHT: float
    OPENED_POSITION: dict

    def __init__(self):
        self.FG = FuturesGetter()
        self.LOGER = Loger()
        self.ANALIZER = Analizer()
        self.OPENED_POSITION = {}

    async def __swing_trade__(self, symbol: str):
        """This is the task of the swing trade mode for one instrument."""
        control_time = 0
        current_high = -1.0
        is_pump = False
        is_volumes = False
        printed = False

        position_is_open = False
        stop_loss = 0.0
        take_profit = 0.0
        tf_ms = self.ANALIZER.kline_tf_to_int_minutes(config.tf) * 60

        if config.trade_mode == SWING_TRADE:
            async with self.BM.aggtrade_futures_socket(symbol=symbol) as ts:
                print(f'{symbol} initialized.')
                while True:  # Главный цикл
                    cur_time = time.time()
                    req = await ts.recv()

                    try:
                        df = pd.DataFrame(req)
                    except Exception as e:
                        print(f'Error during reading agg trades {symbol} {req = }')
                        continue
                    cur_price = float(df[df.index == 'p']['data'].values[0])

                    if current_high < cur_price:  # Перепишем хай пампа
                        current_high = cur_price

                    if not position_is_open:  # Если нет открытой позиции по инструменту

                        if cur_time >= control_time:  # Раз в период поищем последний медвежий бар

                            is_pump = False
                            is_volumes = False
                            control_time = cur_time - (cur_time % tf_ms) + tf_ms
                            lbcomv = await self.ANALIZER.get_last_bear_candle_params(
                                self.CLIENT,
                                symbol,
                                config.tf)

                            pump = lbcomv['last_bear_candle_low'] * (1 + (config.pump_height * 0.01))  # Высота пампа
                            coeff_volumes = lbcomv['swing_max_volume'] / lbcomv[
                                'last_bear_candle_volume']  # Коэффициент азницы объемов

                            if coeff_volumes >= config.coeff_volumes:  # Если объем на последней медвежей свече меньше
                                is_volumes = True                      # максимального объема в свинге

                        if current_high >= pump and not is_pump:  # Если текущий максимум выше расчетного пампа то
                            is_pump = True                        # можно искать вход

                        if is_pump and is_volumes:  # Можно открывать сделку
                            if not printed:
                                print(f'The pump at the symbol {symbol} is found.')
                                await self.LOGER.write_pump_to_file(symbol,
                                                                    lbcomv['last_bear_candle_low'],
                                                                    current_high,
                                                                    lbcomv['last_bear_candle_time'])
                                printed = True

                            stop_loss = cur_price * (1 + (config.stop_loss * 0.01))
                            take_profit = cur_price * (1 - (config.take_profit * 0.01))

                            # Проверим откат
                            is_rollback = self.ANALIZER.check_rollback(lbcomv['last_bear_candle_low'],
                                                                       current_high,
                                                                       cur_price,
                                                                       config.pump_rollback)
                            if is_rollback:
                                print(f'Open a deal {symbol}. {cur_price = } {stop_loss = } {take_profit = }')
                                if await self.TRADE_PROCESSOR.deal_by_market(symbol,
                                                                             config.risk_usdt_on_deal,
                                                                             cur_price,
                                                                             stop_loss,
                                                                             take_profit,
                                                                             SWING_TRADE):
                                    print(f'Position {symbol} is opened. ')
                                    position_is_open = True
                                    is_pump = False
                                    is_volumes = False
                                    printed = False
                                    current_high = -1.0

                    else:  # Если есть открытая позиция
                        if cur_price >= stop_loss:  # закроем по стопу
                            reason = 'stop loss'
                            if await self.TRADE_PROCESSOR.close_by_market(symbol,
                                                                          cur_price,
                                                                          stop_loss,
                                                                          take_profit,
                                                                          SWING_TRADE,
                                                                          reason):  # Закрываем
                                print(f'The deal {symbol} closed by stop_loss. {cur_price = } {stop_loss = } {take_profit = }')
                                position_is_open = False
                        elif cur_price <= take_profit:  # Закроем по тэйку
                            reason = 'take profit'
                            if await self.TRADE_PROCESSOR.close_by_market(symbol,
                                                                          cur_price,
                                                                          stop_loss,
                                                                          take_profit,
                                                                          SWING_TRADE,
                                                                          reason):  # Закрываем
                                print(
                                    f'The deal {symbol} closed by take profit. {cur_price = } {stop_loss = } {take_profit = }')
                                position_is_open = False

    async def __catch_knives__(self, symbol: str):
        """This is the task of the catch knives mode for one instrument."""
        control_time = 0
        prev_volume = 0
        tf = AsyncClient.KLINE_INTERVAL_1MINUTE
        printed = False
        price_in_diap = False
        volume_control = False
        pump_control = False
        now_time = 0
        future_time = 0
        up_diapason_board = 0.0  # верхняя граница диапазона остановки цены
        dn_diapason_board = 0.0  # нижняя граница диапазона остановки цены
        tf_sec = self.ANALIZER.kline_tf_to_int_minutes(config.tf) * 60

        position_is_open = False
        stop_loss = 0.0
        take_profit = 0.0

        if config.trade_mode == CATCH_KNIVES:
            async with self.BM.kline_futures_socket(symbol=symbol) as ts:
                print(f'{symbol} initialized.')
                while True:
                    cur_time = time.time()
                    req = await ts.recv()

                    try:
                        df = pd.DataFrame(req)['k']
                    except Exception as e:
                        print(f'Error during reading kline {symbol} {req = }')
                        continue

                    open_price = float(df.o)
                    high_price = float(df.h)
                    low_price = float(df.l)
                    close_price = float(df.c)
                    volume = float(df.v)
                    cdl_time = float(df.t)

                    if not position_is_open:  # Если нет открытой позиции по инструменту
                        if cur_time >= control_time:  # Раз в период возьмем инфо с предпоследней свечи
                            volume_control = False
                            pump_control = False
                            now_time = 0
                            future_time = 0
                            up_diapason_board = 0
                            dn_diapason_board = 0

                            control_time = cur_time - (cur_time % tf_sec) + tf_sec
                            prev_cdl = await self.ANALIZER.get_last_candle_params(self.CLIENT, symbol, tf)
                            prev_volume = float(prev_cdl.Volume)

                        pump_control_price = low_price * (1 + (config.pump_height * 0.01))
                        if volume > 0 and not volume_control:
                            volume_control = True if prev_volume // volume >= config.coeff_volumes else False
                        pump_control = True if not pump_control and high_price >= pump_control_price else False

                        if volume_control and pump_control and open_price > close_price:  # Можно искать остановку цены
                            if not printed:
                                print(f'The pump at the symbol {symbol} is found.')
                                await self.LOGER.write_pump_to_file(symbol,
                                                                    low_price,
                                                                    high_price,
                                                                    cdl_time)
                                printed = True
                            # Если параметры остановки цены не определены
                            if now_time == 0:
                                now_time = time.time()
                                future_time = now_time + config.stop_diap_time
                                diap = close_price * (0.01 * config.stop_diap)
                                up_diapason_board = close_price + (diap * 0.5)
                                dn_diapason_board = close_price - (diap * 0.5)
                                print(f'New stop diapason for {symbol} is calculated.')
                            # Если цена удержалась в диапазоне указанное время
                            if cur_time >= future_time and up_diapason_board >= close_price:
                                if close_price >= dn_diapason_board:
                                    print(f'Diapason is good {symbol}.')
                                    price_in_diap = True
                                    now_time = 0
                                    future_time = 0
                            # Если цена вышла за расчетные границы диапазона и время не вышло
                            elif cur_time < future_time and (
                                    close_price > up_diapason_board or close_price < dn_diapason_board):
                                print(f'Diapason is broken {symbol}')
                                price_in_diap = False
                                now_time = 0
                                future_time = 0

                            if price_in_diap:
                                stop_loss = close_price * (1 + (config.stop_loss * 0.01))
                                take_profit = close_price * (1 - (config.take_profit * 0.01))
                                print(f'Open a deal {symbol}. {close_price = } {stop_loss = } {take_profit = }')
                                if await self.TRADE_PROCESSOR.deal_by_market(symbol,
                                                                             config.risk_usdt_on_deal,
                                                                             close_price,
                                                                             stop_loss,
                                                                             take_profit,
                                                                             CATCH_KNIVES):
                                    position_is_open = True
                                    printed = False
                                    price_in_diap = False
                                    now_time = 0
                                    future_time = 0

                    else:  # Если есть открытая позиция
                        if close_price >= stop_loss:
                            reason = 'stop loss'
                            if await self.TRADE_PROCESSOR.close_by_market(symbol,
                                                                          close_price,
                                                                          stop_loss,
                                                                          take_profit,
                                                                          SWING_TRADE,
                                                                          reason):  # Закрываем
                                print(
                                    f'The deal {symbol} closed by stop_loss. {close_price = } {stop_loss = } {take_profit = }')
                                position_is_open = False
                        elif close_price <= take_profit:
                            reason = 'take profit'
                            if await self.TRADE_PROCESSOR.close_by_market(symbol,
                                                                          close_price,
                                                                          stop_loss,
                                                                          take_profit,
                                                                          SWING_TRADE,
                                                                          reason):  # Закрываем
                                print(
                                    f'The deal {symbol} closed by take profit. {close_price = } {stop_loss = } {take_profit = }')
                                position_is_open = False

    async def run(self):
        """This method needs to run in the asyncio loop."""
        self.CLIENT = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
        self.BM = BinanceSocketManager(self.CLIENT)
        self.TRADE_PROCESSOR = TradeProcessor(client=self.CLIENT)
        self.F_SYMBOLS = await self.FG.get_all_futures(client=self.CLIENT)
        self.TASKS = []

        tf_in_min = self.ANALIZER.kline_tf_to_int_minutes(config.tf)

        if tf_in_min < 1:
            print('Wrong timeframe!!!')
            await self.CLIENT.close_connection()

        for symbol in self.F_SYMBOLS:
            if config.trade_mode == SWING_TRADE:
                self.TASKS.append(asyncio.create_task(self.__swing_trade__(symbol=symbol)))
            elif config.trade_mode == CATCH_KNIVES:
                self.TASKS.append(asyncio.create_task(self.__catch_knives__(symbol=symbol)))

        for task in self.TASKS:
            await task

    async def close_connection(self):
        """Close the current async client"""
        await self.CLIENT.close_connection()
