from datetime import date
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages

from .models import (
    Enterprises,
    Indicators,
    IndicatorValues,
    ExchangeRates,
)
from .utils import calculate_weighted_indicators


# ---------- стандартные страницы ----------

def home(request):
    return render(request, "dashboard/home.html")


def enterprise_list(request):
    enterprises = Enterprises.objects.all()
    for e in enterprises:
        e.weighted_sum = calculate_weighted_indicators(e.id)
    return render(request, "dashboard/enterprise_list.html",
                  {"enterprises": enterprises})


def indicator_list(request):
    indicators = Indicators.objects.all()
    return render(request, "dashboard/indicator_list.html",
                  {"indicators": indicators})


# ---------- страница показателей ----------

def indicator_values(request):
    enterprise_id   = request.GET.get("enterprise_id")
    from_date       = request.GET.get("from_date")
    to_date         = request.GET.get("to_date")
    target_currency = request.GET.get("target_currency", "RUB")

    qs = IndicatorValues.objects.select_related(
        "enterprise", "indicator", "currency_code"
    )
    if enterprise_id:
        qs = qs.filter(enterprise_id=enterprise_id)
    if from_date:
        qs = qs.filter(value_date__gte=from_date)
    if to_date:
        qs = qs.filter(value_date__lte=to_date)

    today = date.today()

    raw_rates = (ExchangeRates.objects
                 .filter(to_currency__code=target_currency,
                         rate_date__lte=today)
                 .order_by("from_currency__code", "-rate_date"))

    rates = {target_currency: 1.0}
    seen = set()
    for r in raw_rates:
        code = r.from_currency.code
        if code not in seen:
            rates[code] = float(r.rate)
            seen.add(code)

    ctx = {
        "values": qs,
        "enterprises":         Enterprises.objects.all(),
        "indicators":          Indicators.objects.all(),
        "selected_enterprise": int(enterprise_id) if enterprise_id else None,
        "from_date":           from_date,
        "to_date":             to_date,
        "rates":               rates,
        "today":               today,
        "target_currency":     target_currency,
        "currencies":          ["RUB", "USD", "EUR"],
    }
    return render(request, "dashboard/indicator_values.html", ctx)


# ---------- добавление показателя ----------

@csrf_protect
def indicator_add(request):
    if request.method == "POST":
        try:
            IndicatorValues.objects.create(
                indicator_id     = request.POST["indicator_id"],
                enterprise_id    = request.POST["enterprise_id"],
                value_date       = request.POST["value_date"],
                value            = request.POST["value"],
                currency_code_id = request.POST["currency_code"],
            )
            messages.success(request, "Показатель успешно добавлен.")
        except Exception as exc:
            messages.error(request, f"Ошибка: {exc}")
    return redirect("indicator_values")


# ---------- страница «Курсы валют» ----------

def currency_list(request):
    """
    Курсы USD, EUR, RUB. График строится на фронте.
    """
    currencies = ["RUB", "USD", "EUR"]

    # Валидация GET-параметров
    base = request.GET.get("base_currency", "USD").upper()
    target = request.GET.get("target_currency", "RUB").upper()

    # Убедимся, что валюты валидны
    if base not in currencies:
        base = "USD"
    if target not in currencies or target == base:
        target = next(c for c in currencies if c != base)

    return render(request, "dashboard/currencies.html", {
        "currencies": currencies,
        "base_currency": base,
        "target_currency": target,
        "today": date.today(),
        "api_key": "be7c384e48029a798afca38bb34eebea",  # Замените, если не работает
    })