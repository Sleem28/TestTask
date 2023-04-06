# Поиск пампа по всем фьючам Binance.


## Общая концепция

Ищет пампы на фьючах Бинанса и заходит в шорт при снижении активности в ленте. Сокеты, все монеты USDT.
Т.к. на картинке таймфрейм М5, то вполне вероятно, что движение могло произойти за несколько минутных свечей.

**Исходя из этого сделаем 2 режима работы:**
1. *Режим свинговой торговли*
2. *Классическая ловля ножа.*

### Режим свинговой торговли. Детали анализа.

1. На рабочем таймфрейме ищем последнюю медвежью свечу и берем за точку начала свинга ее лоу.
2. Расчитываем цену пампа, и если текущая цена выше или равна цене пампа, то ищем откат на определенное количество процентов.
3. Входим по рынку в шорт.
4. Выходим по рынку по стопу или тэйку.


### Классическая ловля ножа. Детали анализа.

Классический памп происходит в течении 40сек - 1мин. Для анализа используем текущую минутную свечу.

1. Мониторим чтобы на текущей свече был памп на заданный процент, и объем текущей свечи должен быть выше объема предыдущей свечи в N раз.
2. Если словили памп, то ищем приостановку цены в узком диапазоне в течении 1 - 2 секунд.
3. Входим по рынку в шорт.
4. Выходим по рынку по стопу или тэйку.

### Библиотеки

python-binance, pandas

### Настройки
* Ключи вставляем в keys.py
* Настройки робота в config.py

### Логирование
* Пампы в \reports\pumps.txt
* Сделки в \reports\deals.txt