import asyncio
import time
from Processor.Loger import Loger
from binance import AsyncClient
import pandas as pd
import config
from binance.enums import *
import json


class TradeProcessor:

    CLIENT: AsyncClient
    LOGER: Loger
    OPEN_POSITIONS: dict # Сюда сложим открытые позиции

    def __init__(self, client: AsyncClient):
        self.CLIENT = client
        self.LOGER = Loger()
        self.OPEN_POSITIONS = {}

    async def __check_open_position__(self, symbol: str) -> list:
        """Looking open positions by the instrument and return a list with the instrument and the quantity."""
        print(f'Check open positions by {symbol} parameters........ ')
        req = await self.CLIENT.futures_account(symbol=symbol)
        f_acc_info = json.dumps(req)
        f_acc_list_list = json.loads(f_acc_info)['positions']
        df = pd.DataFrame(f_acc_list_list)
        qty = float(df[df['symbol'] == symbol]['positionAmt'].values)
        return [symbol, qty]

    async def deal_by_market(self, symbol: str,
                             qty_usdt: float,
                             cur_price: float,
                             stop_loss: float,
                             take_profit: float,
                             mode_trade: str,
                             side=SIDE_SELL) -> bool:
        """Open a deal by market."""
        print(f'Opening deal by {symbol}........ ')
        trading_conditions, balance = await self.__check_trading_conditions__(qty_usdt=qty_usdt, symbol=symbol)
        print(f'Trading conditions are checked {symbol}')
        if trading_conditions:
            qty = await self.__calc_lot__(symbol, qty_usdt, cur_price, stop_loss, take_profit, balance)
            print(f'Lot calculated {symbol}')
            reason = 'deal open'
            print(f'Opening deal at symbol {symbol}. quantity:{qty}')
            if qty > 0:
                sell_deal_req = await self.CLIENT.futures_create_order(symbol=symbol,
                                                                       side=side,
                                                                       type=ORDER_TYPE_MARKET,
                                                                       quantity=qty)

                print(f'Pposition by {symbol} is open. Info about the opened position:\n{sell_deal_req}]\n')
                open_deal = await self.__check_open_position__(symbol)
                if abs(open_deal[1]) > 0:
                    self.OPEN_POSITIONS[open_deal[0]] = open_deal[1]
                    print(f'The position list has position by {symbol} .')
                    await self.LOGER.write_deal_to_file(symbol, cur_price, stop_loss, take_profit, qty, mode_trade,
                                                        reason)
                    return True
                else:
                    print(f'The deal at {symbol} is not open.')
                    return False
            else:
                print(f'Wrong {symbol} quantity.')
                return False

    async def close_by_market(self, symbol: str,
                              cur_price: float,
                              stop_loss: float,
                              take_profit: float,
                              mode_trade: str,
                              reason: str,
                              side=SIDE_BUY) -> bool:
        """Close a deal by market."""
        qty = abs(self.OPEN_POSITIONS[symbol])

        if qty > 0:
            close_req = await self.CLIENT.futures_create_order(symbol=symbol,
                                                               side=side,
                                                               type=ORDER_TYPE_MARKET,
                                                               quantity=qty)

            time.sleep(0.1)

            print(f'Info about the closed position by {symbol}:\n{close_req}]\n')
            closed_deal = await self.__check_open_position__(symbol)
            if closed_deal[1] == 0:
                self.OPEN_POSITIONS[closed_deal[0]] = closed_deal[1]
                print(f'The deal at {symbol} is closed.')
                await self.LOGER.write_deal_to_file(symbol, cur_price, stop_loss, take_profit, qty, mode_trade, reason)
                return True
            else:
                print(f'The deal at {symbol} is not closed.')
                return False
        else:
            print(f'Wrong quantity for closing the deal {symbol}.')
            return False

    async def __calc_lot__(self, symbol: str,
                           qty_usdt: float,
                           cur_price: float,
                           stop_loss: float,
                           take_profit: float,
                           money: float) -> float:
        """Calculating a quantity of the volume for the deal."""
        print(f'Calculate lot for {symbol}........ ')
        min_usdt = 5   # минимальный объем сделки по фьючу в usdt
        max_qty, min_qty, step, tick_size = await self.__get_qty_params__(symbol)
        min_vol = (((min_usdt/take_profit)//min_qty) + min_qty)
        vol = qty_usdt/(stop_loss - cur_price)
        max_balance_qty = ((money * config.shoulder / cur_price * (config.depo_load * 0.01)) // step) * step

        if vol < min_vol:
            vol = min_qty
        elif vol > max_qty:
            vol = max_qty
        elif vol > max_balance_qty:
            vol = max_balance_qty
        else:
            vol = (vol // step) * step
        return min_vol

    async def __get_qty_params__(self, symbol: str):
        """Getting the max-min quantity and the step for the instrument."""
        print(f'Getting {symbol} parameters........ ')
        req = await self.CLIENT.futures_exchange_info()

        df = pd.DataFrame(req['symbols'])
        df = df[df.symbol.str.contains(symbol)]
        lst = df.filters.tolist()[0][2]
        tick_size = df.filters.tolist()[0][0]
        lst = [lst['maxQty'], lst['minQty'], lst['stepSize'], tick_size['tickSize']]
        print(lst)
        lst = tuple(map(float, lst))
        return lst

    async def __check_trading_conditions__(self, qty_usdt: float, symbol: str) -> tuple:
        """Check the account status and return the conditions and the balance"""
        print(f'Check {symbol} conditions........ ')
        req = await self.CLIENT.futures_account()
        print(f'Request {symbol} conditions received.')

        can_trade = bool(req['canTrade'])
        money = float(req['totalMarginBalance'])
        margin = float(req['totalMaintMargin'])

        if not can_trade:
            print('Trading is blocked.')
            return False, money
        elif qty_usdt > money:
            print('Insufficient funds.')
            return False, money
        elif margin > 0:
            print(f'Margin is no null')
            load_percent = round(margin/(money * 0.01), 2)
            print(f'{load_percent = } {money/load_percent = } {config.depo_load = }')
            if money/load_percent > config.depo_load:
                print(f'The deposit is overloaded.{money = } {margin = } {load_percent}')
                return False, money
            else:
                print(f'Trading conditions by {symbol} are checked. OK.')
                return True, money
        else:
            print(f'Trading conditions by {symbol} are checked. OK.')
            return True, money
