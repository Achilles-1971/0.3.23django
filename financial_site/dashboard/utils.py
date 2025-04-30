from datetime import date
from .models import IndicatorValues, ExchangeRates

def calculate_weighted_indicators(enterprise_id: int) -> float:
    """
    Возвращает СУММУ взвешенных показателей (уникальные показатели,
    берётся самое свежее значение) в рублях.
    """
    today = date.today()

    # 1) Словарь курсов -> RUB на сегодня
    rates: dict[str, float] = {"RUB": 1.0}
    for r in ExchangeRates.objects.filter(to_currency__code="RUB", rate_date=today):
        if r.from_currency_id and r.rate:
            rates[r.from_currency.code] = float(r.rate)

    # 2) Все значения предприятия
    values = (
        IndicatorValues.objects
        .select_related("indicator", "currency_code")
        .filter(enterprise_id=enterprise_id)
    )

    # 3) Оставляем по одному (самому свежему) значению на показатель
    latest: dict[int, IndicatorValues] = {}
    for v in values:
        ind_id = v.indicator_id
        if ind_id not in latest or v.value_date > latest[ind_id].value_date:
            latest[ind_id] = v

    # 4) Считаем сумму
    total = 0.0
    for v in latest.values():
        rate = rates.get(v.currency_code.code if v.currency_code else "RUB", 1.0)
        importance = float(v.indicator.importance or 1.0)
        total += float(v.value) * importance * rate

    return round(total, 2)
