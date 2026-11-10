# Arcana Diary

ИИ-таро с дневником. План продукта: https://claude.ai/artifact/PtJFSSX4C16tHKvTEqWM7R

## Деплой

```bash
deploy/deploy.sh
```

Скрипт подтягивает `main`, собирает сайт, перезапускает контейнеры и запускает `deploy/check-indexing.sh`.
Настройки — в `deploy/.env` (шаблон `deploy/.env.example`, в git не попадает).

## До запуска

`LAUNCHED=false`: сайт закрыт паролем (`STAGE_USER` / `STAGE_PASSWORD` из `deploy/.env`)
и отдаёт `X-Robots-Tag: noindex, nofollow`. `Disallow: /` в robots.txt не используется никогда.

## Запуск (снятие закрытия)

1. В `deploy/.env` поставить `LAUNCHED=true`.
2. `deploy/deploy.sh` — проверка должна пройти в режиме «после запуска».
3. В первые 5 минут открыть `https://arcanadiary.com/robots.txt` и проверить сайт в Search Console.
