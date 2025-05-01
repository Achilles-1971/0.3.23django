from datetime import date
import os, bcrypt, cloudinary, cloudinary.uploader
from uuid import uuid4
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage

from .models import (
    Enterprises, Indicators, IndicatorValues,
    ExchangeRates, Users         # кастомная таблица
)
from .utils  import calculate_weighted_indicators
from .forms  import LoginForm, RegisterForm


# ─────────────────────────────────────────────
#  Стандартные страницы
# ─────────────────────────────────────────────
def home(request):
    return render(request, "dashboard/home.html")


# ─────────────────────────────────────────────
#  Список предприятий
# ─────────────────────────────────────────────
def enterprise_list(request):
    q  = request.GET.get("q", "").strip()
    qs = Enterprises.objects.order_by('id')
    if q:
        qs = qs.filter(name__icontains=q)

    page_obj = Paginator(qs, 10).get_page(request.GET.get("page"))

    today = date.today()
    rates = {"RUB": 1.0}
    for r in ExchangeRates.objects.filter(to_currency__code="RUB", rate_date=today):
        rates[r.from_currency.code] = float(r.rate)

    for ent in page_obj:
        ent.weighted_sum = calculate_weighted_indicators(ent.id)

        latest = {}
        for v in IndicatorValues.objects.select_related("indicator", "currency_code").filter(enterprise_id=ent.id):
            if v.indicator_id not in latest or v.value_date > latest[v.indicator_id].value_date:
                latest[v.indicator_id] = v

        expl = []
        for v in latest.values():
            code = v.currency_code.code if v.currency_code else "RUB"
            imp  = float(v.indicator.importance or 1)
            rate = rates.get(code, 1)
            res  = round(float(v.value) * imp * rate, 2)
            expl.append({
                "name": v.indicator.name, "value": v.value,
                "currency": code, "importance": imp,
                "rate": rate, "result": res
            })
        ent.explanation = expl

    return render(request, "dashboard/enterprise_list.html", {
        "enterprises": page_obj,
        "search_query": q,
    })


# ─────────────────────────────────────────────
#  Справочник показателей
# ─────────────────────────────────────────────
def indicator_list(request):
    return render(request, "dashboard/indicator_list.html", {
        "indicators": Indicators.objects.all()
    })


# ─────────────────────────────────────────────
#  Значения показателей + фильтры
# ─────────────────────────────────────────────
def indicator_values(request):
    enterprise_id   = request.GET.get("enterprise_id")
    from_date       = request.GET.get("from_date")
    to_date         = request.GET.get("to_date")
    target_currency = request.GET.get("target_currency", "RUB")
    sort_by         = request.GET.get("sort_by", "")

    qs = IndicatorValues.objects.select_related("enterprise", "indicator", "currency_code")
    if enterprise_id:
        qs = qs.filter(enterprise_id=enterprise_id)
    if from_date:
        qs = qs.filter(value_date__gte=from_date)
    if to_date:
        qs = qs.filter(value_date__lte=to_date)

    order_map = {
        "enterprise": "enterprise__name",
        "indicator":  "indicator__name",
        "value":      "-value",
        "date":       "-value_date",
    }
    if sort_by in order_map:
        qs = qs.order_by(order_map[sort_by])

    values = Paginator(qs, 20).get_page(request.GET.get("page"))

    today = date.today()
    raw = (ExchangeRates.objects
           .filter(to_currency__code=target_currency, rate_date__lte=today)
           .order_by("from_currency__code", "-rate_date"))
    rates = {target_currency: 1.0}
    seen  = set()
    for r in raw:
        code = r.from_currency.code
        if code not in seen:
            rates[code] = float(r.rate)
            seen.add(code)

    return render(request, "dashboard/indicator_values.html", {
        "values": values,
        "enterprises": Enterprises.objects.all(),
        "indicators":  Indicators.objects.all(),
        "selected_enterprise": int(enterprise_id) if enterprise_id else None,
        "from_date": from_date, "to_date": to_date,
        "rates": rates, "today": today,
        "target_currency": target_currency,
        "currencies": ["RUB", "USD", "EUR"],
        "sort_by": sort_by,
        "sort_choices": [
            ("", "Без сортировки"), ("enterprise","По предприятию"),
            ("indicator","По показателю"), ("value","По значению"),
            ("date","По дате")
        ],
        "page_obj": values,
    })


# ─────────────────────────────────────────────
#  Добавление значения показателя
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
#  Курсы валют
# ─────────────────────────────────────────────
def currency_list(request):
    currencies = ["RUB", "USD", "EUR"]
    base   = request.GET.get("base_currency",  "USD").upper()
    target = request.GET.get("target_currency","RUB").upper()
    if base not in currencies:
        base = "USD"
    if target not in currencies or target == base:
        target = next(c for c in currencies if c != base)

    return render(request, "dashboard/currencies.html", {
        "currencies": currencies,
        "base_currency": base,
        "target_currency": target,
        "today": date.today(),
        "api_key": "be7c384e48029a798afca38bb34eebea",
    })


# ─────────────────────────────────────────────
#  Аутентификация
# ─────────────────────────────────────────────
def login_view(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']

        try:
            custom_user = Users.objects.get(username=username)

            # Проверка пароля
            try:
                if not bcrypt.checkpw(password.encode(), custom_user.hashed_password.encode()):
                    messages.error(request, "Неверный пароль")
                    return render(request, 'dashboard/auth/login.html', {'form': form})
            except ValueError:
                if custom_user.hashed_password != password:
                    messages.error(request, "Неверный пароль")
                    return render(request, 'dashboard/auth/login.html', {'form': form})
                custom_user.hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                custom_user.save()

            # Создание или обновление auth_user
            user, created = User.objects.get_or_create(username=username)
            if created or not user.has_usable_password():
                user.set_password(password)
                user.save()

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)

                # Проверка и очистка старого пути
                avatar_url = custom_user.avatar_url or ""
                if avatar_url.startswith("/uploads/") or avatar_url.startswith("avatars/"):
                    # Автоматическая подстановка дефолтной картинки (если ссылка старая)
                    avatar_url = "https://res.cloudinary.com/dx9zbn2jk/image/upload/v1/avatars/default.jpg"

                request.session['avatar_url'] = avatar_url
                return redirect('home')

            messages.error(request, "Ошибка входа")

        except Users.DoesNotExist:
            messages.error(request, "Пользователь не найден")

    return render(request, 'dashboard/auth/login.html', {'form': form})



def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('login')


# ─────────────────────────────────────────────
#  Регистрация + Cloudinary
# ─────────────────────────────────────────────
def register_view(request):
    form = RegisterForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        username    = form.cleaned_data['username']
        password    = form.cleaned_data['password1']
        avatar_file = form.cleaned_data.get('avatar_url')

        if Users.objects.filter(username=username).exists():
            messages.error(request, "Пользователь с таким именем уже существует")
            return render(request, 'dashboard/auth/register.html', {'form': form})

        # пароль
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Cloudinary конфиг
        cloudinary.config(
            cloud_name = settings.CLOUDINARY["cloud_name"],
            api_key    = settings.CLOUDINARY["api_key"],
            api_secret = settings.CLOUDINARY["api_secret"],
        )

        if avatar_file:
            res = cloudinary.uploader.upload(
                avatar_file,
                folder="avatars",
                resource_type="image"
            )
            avatar_url = res["secure_url"]
        else:
            avatar_url = "https://res.cloudinary.com/dx9zbn2jk/image/upload/v1/avatars/default.jpg"

        # в кастомную таблицу
        Users.objects.create(
            username=username,
            hashed_password=hashed_pw,
            avatar_url=avatar_url
        )

        # auth_user + логин
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        request.session['avatar_url'] = avatar_url
        return redirect('home')

    return render(request, 'dashboard/auth/register.html', {'form': form})

@csrf_exempt
def enterprise_add(request):
    if request.method == "POST":
        Enterprises.objects.create(
            name=request.POST.get("name"),
            requisites=request.POST.get("requisites"),
            phone=request.POST.get("phone"),
            contact_person=request.POST.get("contact_person")
        )
    return redirect('enterprise_list')

@login_required
def profile_view(request):
    user = request.user
    custom_user = Users.objects.filter(username=user.username).first()
    enterprises = Enterprises.objects.filter(added_by=user)  # предполагается поле added_by в модели

    avatar_url = custom_user.avatar_url if custom_user and custom_user.avatar_url else ""

    return render(request, 'dashboard/profile.html', {
        'user': user,
        'custom_user': custom_user,
        'enterprises': enterprises,
        'avatar_url': avatar_url,
    })
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
@require_POST
@login_required
def update_username(request):
    new_username = request.POST.get('username', '').strip()

    if new_username and new_username != request.user.username:
        # Обновим и auth_user, и кастомную Users
        request.user.username = new_username
        request.user.save()

        custom_user = Users.objects.filter(username=request.user.username).first()
        if custom_user:
            custom_user.username = new_username
            custom_user.save()

        # Обновим сессию
        update_session_auth_hash(request, request.user)

    return redirect('profile')

@require_POST
@login_required
def update_avatar(request):
    avatar_file = request.FILES.get('avatar')
    if avatar_file:
        # Настройка Cloudinary
        cloudinary.config(
            cloud_name = settings.CLOUDINARY["cloud_name"],
            api_key    = settings.CLOUDINARY["api_key"],
            api_secret = settings.CLOUDINARY["api_secret"],
        )

        # Загрузка в Cloudinary
        try:
            result = cloudinary.uploader.upload(
                avatar_file,
                folder="avatars",
                resource_type="image"
            )
            avatar_url = result.get("secure_url")
        except Exception as e:
            messages.error(request, f"Ошибка загрузки аватара: {e}")
            return redirect('profile')

        # Обновим в кастомной таблице
        custom_user = Users.objects.filter(username=request.user.username).first()
        if custom_user:
            custom_user.avatar_url = avatar_url
            custom_user.save()

        # Обновим в сессии
        request.session['avatar_url'] = avatar_url

    return redirect('profile')
