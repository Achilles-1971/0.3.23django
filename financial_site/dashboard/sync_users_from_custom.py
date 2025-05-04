from django.core.management.base import BaseCommand
from dashboard.models import Users  # твоя таблица "users"
from django.contrib.auth.models import User
from django.contrib.auth.hashers import is_password_usable

class Command(BaseCommand):
    help = "Синхронизирует пользователей из кастомной таблицы `users` в `auth_user`"

    def handle(self, *args, **kwargs):
        created_count = 0
        for user in Users.objects.all():
            if User.objects.filter(username=user.username).exists():
                continue

            if is_password_usable(user.hashed_password):
                django_password = user.hashed_password
            else:
                self.stdout.write(self.style.WARNING(f"Пропущен пользователь {user.username}: неподдерживаемый формат пароля"))
                continue

            u = User.objects.create(
                username=user.username,
                password=django_password, 
            )
            created_count += 1
        self.stdout.write(self.style.SUCCESS(f"Импортировано: {created_count} пользователей."))
