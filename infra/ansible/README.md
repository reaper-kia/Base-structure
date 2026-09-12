# Деплой на VPS

Плейбук ставит Docker, клонирует репозиторий, разворачивает `.env.prod`,
поднимает `compose.prod.yml` и тянет веса модели. Рассчитан на чистый
Ubuntu-сервер.

## Требования к серверу

Стек целиком локальный, внешних платных API нет, поэтому всё упирается в
модель:

| Ресурс | Минимум | Комментарий |
|---|---|---|
| RAM | 8 ГБ | 6 ГБ выделено контейнеру Ollama под `qwen2.5:7b-instruct` |
| Диск | 20 ГБ | ~5 ГБ веса модели, остальное — образы и база |
| CPU | 4 ядра | на CPU обработка одного черновика занимает 20–60 секунд |
| GPU | не требуется | с GPU обработка ускоряется, но не обязательна |

Открытые порты: 80 и 443. Ollama наружу не публикуется — она доступна
только внутри сети `backend`.

## Подготовка

```bash
cd infra/ansible
cp inventory/group_vars/doc3/secrets.yml.example inventory/group_vars/doc3/secrets.yml
$EDITOR inventory/group_vars/doc3/secrets.yml   # пароль базы
$EDITOR inventory/prod.yml                      # адрес, SSH-пользователь, ключ
$EDITOR inventory/group_vars/doc3/vars.yml      # app_repo, deploy_dir, ORG_NAME
```

`app_repo` по умолчанию — заглушка `CHANGE-ME`: подставьте адрес своего
репозитория, иначе клонирование упадёт.

## Запуск

```bash
ansible-playbook playbooks/deploy.yml
```

Первый прогон долгий: сборка образов плюс скачивание ~5 ГБ весов.
Повторный запуск обновляет код и перезапускает стек — веса уже лежат в
томе `prod_ollama_models` и заново не тянутся.

## TLS

Плейбук выпускает самоподписанный сертификат на IP сервера: стенд
поднимается сразу, браузер показывает предупреждение. Для домена
положите рядом настоящий сертификат:

```bash
# на сервере, после того как домен указывает на VPS
sudo certbot certonly --standalone -d example.com
sudo cp /etc/letsencrypt/live/example.com/fullchain.pem /opt/doc3/certs/localhost.crt
sudo cp /etc/letsencrypt/live/example.com/privkey.pem   /opt/doc3/certs/localhost.key
cd /opt/doc3 && docker compose -f compose.prod.yml restart frontend
```

Плейбук существующий сертификат не перезаписывает.

## Проверка после деплоя

```bash
curl -k https://<адрес>/health
make smoke-prod PROD_URL=https://<адрес>    # из корня репозитория
```

`make smoke-prod` проходит весь сценарий: создаёт документ, дожидается
обработки и скачивает DOCX.
