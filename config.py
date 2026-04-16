from decimal import getcontext

# Настройка точности Decimal
getcontext().prec = 28

# Значения по умолчанию (будут перезаписаны при загрузке)
start_value_gas = 25745
start_value_electricity = 9838
start_value_water = 502

# Тарифы
tarif_gas = 8.7
tarif_electricity = 7.1
tarif_water = 84.44

# Комиссия банка (1% = 0.01)
fee_gas = 0.01
fee_electricity = 0.01
fee_water = 0.01


