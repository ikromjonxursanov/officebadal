# Officebadal

Kichik ofis uchun oddiy oylik badal tizimi.

## Nima qiladi?

- Xodimlar bot orqali Telegram username kiritib tizimga kiradi.
- Admin har oy uchun badal summasi va to'lov kunini belgilaydi.
- Telegram bot xodimni username orqali taniydi.
- To'lov kuni kelganda Celery to'lamaganlarga har 2 soatda eslatma yuboradi.
- To'lovlar admin panelda ko'riladi va boshqariladi.

## Asosiy buyruqlar

- `/start` - login qilish uchun username so'raydi.
- `/login` - username qayta kiritish uchun ishlatiladi.
- `/toladim` - joriy oy badali uchun to'lov arizasini adminga yuboradi.
- `/status` - joriy oy bo'yicha holatni ko'rsatadi.

## Ishga tushirish

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py runserver
```

Bot:

```bash
python3 manage.py runbot
```

Celery worker va beat:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

## Admin oqimi

1. `Monthly contributions` bo'limida oy, summa va to'lov kunini kiriting. `month` oyning 1-sanasi bo'lishi kerak.
2. Xodim Telegram botga `/start` yuboradi.
3. Bot so'raganda xodim username yozadi: `ali_valiyev` yoki `@ali_valiyev`.
4. Tizim userni avtomatik yaratadi yoki mavjud username bo'lsa Telegram akkauntga ulaydi.
5. To'lov qilinganda xodim `/toladim` yuboradi.
6. Admin `Payments` bo'limida to'lovni `Tasdiqlandi` qiladi. Shundan keyin user statusida to'langan ko'rinadi.

## Production checklist

Production uchun `.env` qiymatlarini aniq qo'ying:

```env
DEBUG=False
SECRET_KEY=long-random-secret
ALLOWED_HOSTS=your-domain.uz,server-ip
CSRF_TRUSTED_ORIGINS=https://your-domain.uz
DB_ENGINE=django.db.backends.postgresql
DB_NAME=officebadal
DB_USER=officebadal
DB_PASSWORD=strong-password
DB_HOST=127.0.0.1
DB_PORT=5432
TELEGRAM_BOT_TOKEN=...
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

Deploy komandalar:

```bash
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py collectstatic --noinput
python3 manage.py check --deploy
```

Django app:

```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

Bot:

```bash
python3 manage.py runbot
```

Celery:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

Nginx productionda quyidagilarni serve qilishi kerak:

- `/static/` -> `staticfiles/`
- `/media/` -> `media/`

`media/receipts/` ichida user yuborgan to'lov cheklari saqlanadi. Shu papkani backupga qo'shing.
