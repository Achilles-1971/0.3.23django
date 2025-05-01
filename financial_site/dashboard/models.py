from django.db import models
from django.contrib.auth.models import User

class AlembicVersion(models.Model):
    version_num = models.CharField(primary_key=True, max_length=32)

    class Meta:
        managed = False
        db_table = 'alembic_version'


class Currencies(models.Model):
    code = models.CharField(primary_key=True, max_length=3)
    name = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'currencies'


class Enterprises(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    requisites = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)


class ExchangeRates(models.Model):
    from_currency = models.ForeignKey(Currencies, models.DO_NOTHING, db_column='from_currency', blank=True, null=True)
    to_currency = models.ForeignKey(Currencies, models.DO_NOTHING, db_column='to_currency', related_name='exchangerates_to_currency_set', blank=True, null=True)
    rate = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    rate_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'exchange_rates'
        unique_together = (('from_currency', 'to_currency', 'rate_date'),)


class IndicatorValues(models.Model):
    enterprise = models.ForeignKey(Enterprises, models.DO_NOTHING, blank=True, null=True)
    indicator = models.ForeignKey('Indicators', models.DO_NOTHING, blank=True, null=True)
    value_date = models.DateField(blank=True, null=True)
    value = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    currency_code = models.ForeignKey(Currencies, models.DO_NOTHING, db_column='currency_code', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'indicator_values'


class Indicators(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    importance = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'indicators'


class Users(models.Model):
    username = models.CharField(unique=True, max_length=255, blank=True, null=True)
    hashed_password = models.CharField(max_length=255)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'
