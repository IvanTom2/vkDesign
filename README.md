# vkDesign

Сервис генерации оформления групп ВКонтакте. Принимает сообщения из сообщества,
по триггеру ставит задачу, генерирует дизайн (Gemini / Nano Banana) и отправляет
результат обратно в диалог.

## Архитектура

Три независимых процесса, общающихся через PostgreSQL (состояние) и RabbitMQ (очереди):

```
        VK Long Poll                  RabbitMQ                     RabbitMQ
            │                      (vk_design_jobs)            (vk_design_results)
            ▼                            │                            │
   ┌──────────────┐  job + publish  ┌──────────┐  outbox + publish ┌──────────┐
   │   poll.py    │ ───────────────▶│ worker.py│ ─────────────────▶│ sender.py│
   │  PollerSvc   │                 │ WorkerSvc│                    │ SenderSvc│
   └──────┬───────┘                 └────┬─────┘                    └────┬─────┘
          │  messages/jobs               │ jobs/outbox (atomic)          │ outbox→sent
          ▼                              ▼                               ▼
                          ┌───────────────────────────┐
                          │   PostgreSQL: messages,    │
                          │   jobs, outbox             │
                          └───────────────────────────┘
```

1. **poll.py — поллер (этап 1).** Слушает Bots Long Poll сообщества. Каждое
   входящее сообщение пишется в историю (`messages`) — из неё извлекается
   контекст. По триггеру (слово `Начать`) собирает контекст из истории, создаёт
   задачу в БД и публикует её в очередь задач. Шлёт пользователю ack.
2. **worker.py — воркер (этап 2).** Слушает очередь задач, обрабатывает их
   обработчиком (сейчас один — создание дизайна). Сохраняет медиа, и **атомарно**
   (transactional outbox) фиксирует задачу как выполненную + ставит запись на
   отправку результата, после чего публикует её в очередь результатов.
3. **sender.py — отправщик (этап 3).** Слушает очередь результатов, отправляет
   готовый дизайн в VK и фиксирует выполнение.

### Развязка через интерфейсы

Прикладные сервисы зависят только от портов (`src/domain/interfaces.py`).
Реализации подставляются в composition root (`src/bootstrap.py`).

Постоянный стек — PostgreSQL + RabbitMQ. Задуманы сменяемыми только:

| Что меняется | Порт | Текущая реализация |
|---|---|---|
| Метод обработки сообщений | `ITriggerDetector`, `IContextExtractor`, `IJobHandler` | `KeywordTriggerDetector`, `SimpleContextExtractor`, `DesignJobHandler` |
| Генерация изображений | `IImageGeneratorService` | `ImageGeneratorServiceGeminiDynamicCreativeV5` |
| Отправка сообщений | `IMessageSender` | `VkMessageSender` |
| Хранилище медиа | `IMediaStorage` | `DiskMediaStorage` (на диск, путь в БД) |

### Логирование

`logger.py` (structlog). В классы логгер инжектится через `ILogger`, в простом
коде используется напрямую. Компонент помечается через `logger.bind(component=...)`.

## Запуск

```bash
# 1. Инфраструктура
docker compose up -d

# 2. Конфиг
cp example.env .env   # заполнить GEMINI_API_KEY, VK_GROUP_TOKEN, VK_GROUP_ID, ...

# 3. Зависимости
uv sync

# 4. Три процесса (в отдельных терминалах). Схема БД создаётся автоматически.
uv run python poll.py
uv run python worker.py
uv run python sender.py
```

## Структура

```
poll.py / worker.py / sender.py   точки входа
settings.py                       конфигурация (pydantic-settings)
logger.py                         structlog + ILogger
src/
  domain/
    models.py                     доменные сущности (Job, DialogMessage, OutboxMessage, ...)
    interfaces.py                 порты (интерфейсы сервисов и репозиториев)
    trigger.py / context.py       детект триггера и извлечение контекста (этап 1)
    handlers.py                   обработчик задачи (этап 2)
    generator/                    сервисы генерации изображений (Gemini)
  infra/
    db/                           ORM, engine, репозитории + Unit of Work (PostgreSQL)
    queue/                        клиент RabbitMQ
    storage/                      хранилище медиа (диск)
    vk/                           отправка сообщений в VK
  services/                       PollerService / WorkerService / ResultSenderService
  bootstrap.py                    composition root (сборка зависимостей)
  vk/                             низкоуровневое API VK
  gemini/                         клиент Gemini
```
