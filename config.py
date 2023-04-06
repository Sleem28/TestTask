from binance import AsyncClient
from enums import CATCH_KNIVES, SWING_TRADE

''' Параметры для анализа и торговли '''

pump_height = 5         # Высота пампа в %
risk_usdt_on_deal = 1   # Количество риска в USDT на сделку
shoulder = 20           # кредитное плечо
depo_load = 70.0        # Максимально допустимая загрузка депозита в процентах
coeff_volumes = 3       # Коэффициент разницы между объемом текущей и предыдущей свечи
stop_loss = 1           # стоп лосс в процентах  инструмента
take_profit = 5         # тэйк профит в процентах  инструмента

# Режимы торговли: CATCH_KNIVES или SWING_TRADE
trade_mode = CATCH_KNIVES
# Параметры для режима swing trade
tf = AsyncClient.KLINE_INTERVAL_1MINUTE  # Рабочий таймфрейм
pump_rollback = 10.0                     # Величина отката цены после пампа в процентах от величины памп-свинга для входа в сделку
# Параметры для режима catch knives
stop_diap = 0.2                          # размер диапазона остановки цены при пампе в процентах инструмента
stop_diap_time = 2                       # количество секунд нахождения цены в стоп диапазоне
