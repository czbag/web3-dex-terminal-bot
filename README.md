# Web3 DEX Terminal (test)

Telegram-бот для поиска, анализа и торговли токенами на DEX-биржах через EVM-совместимые блокчейны. Позволяет управлять кошельками, сканировать ликвидность, совершать свопы и настраивать торговые параметры — всё из интерфейса Telegram.

## Возможности

- **Мультичейн-поиск токенов** — поиск по контрактному адресу одновременно по всем включённым сетям
- **Анализ ликвидности** — сканирование пулов на Uniswap V2, V3 и Aerodrome, выбор лучшего маршрута
- **Покупка и продажа** — свопы через пресеты или произвольные суммы с симуляцией транзакций
- **Управление кошельками** — генерация (BIP39) и импорт кошельков с шифрованием приватных ключей (Fernet)
- **Гибкие настройки** — slippage, price impact, gas delta, max gas price/limit для каждой сети отдельно
- **Approve/Revoke** — управление разрешениями токенов
- **Мультихоп-роутинг** — автоматический выбор маршрута (прямой или через стейблкоины)
- **Фоновые задачи** — периодическое обновление цены ETH через Binance API

## Поддерживаемые сети

| Сеть     | Нативный токен | DEX                          |
|----------|----------------|------------------------------|
| Ethereum | ETH            | Uniswap V2, Uniswap V3      |
| BSC      | BNB            | Uniswap V2, Uniswap V3      |

## Архитектура

```
Telegram (aiogram + aiogram-dialog)
    │
    ├── Dialogs ── Меню / Сети / Кошельки / Настройки
    ├── Handlers ── Парсинг адресов / Торговля
    │
    ├── Services
    │   ├── LiquidityScanner ── Сканирование пулов по сетям
    │   ├── SwapClient ── Симуляция и исполнение свопов
    │   ├── TokenService ── Метаданные токенов
    │   └── WalletService ── Шифрование / расшифровка ключей
    │
    ├── DEX Clients
    │   ├── UniswapV2Client
    │   ├── UniswapV3Client
    │   └── AerodromeV2Client
    │
    ├── Database (SQLAlchemy + asyncpg)
    │   └── PostgreSQL ── Users, Wallets, Chains, Tokens, Settings
    │
    ├── Background Tasks (Taskiq + Redis)
    │   └── Обновление цены ETH каждую минуту
    │
    └── Smart Contract (Solidity)
        └── TradingBotSwap ── Свопы через V2/V3 на уровне контракта
```

## Стек

| Компонент        | Технология                  |
|------------------|-----------------------------|
| Бот-фреймворк    | aiogram 3.22 + aiogram-dialog 2.4 |
| Web3             | web3.py 7.14                |
| ORM              | SQLAlchemy 2.0              |
| Миграции         | Alembic 1.17                |
| БД               | PostgreSQL (asyncpg)        |
| Кеш / FSM / Очередь | Redis                   |
| Фоновые задачи   | Taskiq (Redis broker)       |
| Шифрование       | cryptography (Fernet)       |
| Конфигурация     | Dynaconf                    |
| Логирование      | Loguru                      |
| Python           | >= 3.12                     |

## Установка

### 1. Клонирование

```bash
git clone https://github.com/czbag/test-project.git
cd test-project
```

### 2. Зависимости

Проект использует `uv` (или `pip`):

```bash
uv sync
# или
pip install -e .
```

### 3. Переменные окружения

Скопировать `.env.example` в `.env` и заполнить:

```bash
cp .env.example .env
```

```env
ENV_FOR_DYNACONF=development

BOT_TOKEN=<токен Telegram-бота>
POSTGRES_DSN=postgresql+asyncpg://user:password@localhost:5432/dbname
REDIS_PASSWORD=<пароль Redis>
WALLET_ENCRYPTION_KEY=<Fernet-ключ>
```

Сгенерировать Fernet-ключ:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 4. База данных

Создать БД в PostgreSQL, затем применить миграции:

```bash
alembic upgrade head
```

### 5. Redis

Убедиться, что Redis запущен и доступен по параметрам из `config.toml`.

### 6. Конфигурация

Отредактировать `config.toml` при необходимости:

- `ADMINS` — список Telegram user ID администраторов
- `WEBHOOK_*` — настройки вебхука (или использовать polling)
- `REDIS_HOST`, `REDIS_PORT` — параметры подключения к Redis
- `FSM_STORAGE` — `redis` или `memory`

## Запуск

```bash
python bot.py
```

Бот поддерживает два режима: **webhook** и **polling** (настраивается в `bot.py`).

## Использование

### Главное меню (`/start`)

Три раздела:

- **Chains** — включение/выключение сетей для поиска токенов
- **Wallets** — генерация и импорт кошельков (по сетям)
- **Settings** — настройка торговых параметров по сетям

### Поиск токена

Отправить контрактный адрес токена в чат:

```
0x1111111111166b7FE7bd91427724B487980aFc69
```

Бот выполнит поиск по всем включённым сетям и DEX, покажет:
- Название, тикер, decimals, total supply
- Цена, market cap, TVL пула
- Баланс кошелька (нативный + токен)
- Маршрут свопа (direct / multihop)

### Покупка

Пресеты: `0.01` · `0.05` · `0.1` · `0.2` · `0.5` · `1` ETH

Кнопка **Buy X ETH** — ввод произвольного значения (0.0001–100 ETH).

### Продажа

Пресеты: `25%` · `50%` · `75%` · `100%` от баланса токена.

### Настройки (по каждой сети)

| Параметр        | Раздел   | Диапазон           |
|-----------------|----------|--------------------|
| `slippage`      | Buy/Sell | 0.1 – 1000%        |
| `price_impact`  | Buy/Sell | 0.1 – 100%         |
| `gas_delta`     | Buy/Sell/Approve | 0.1 – 1,000,000 |
| `max_gas_price` | Общие    | 5 – 1,000,000 Gwei |
| `max_gas_limit` | Общие    | 1M – 30M           |
| `auto_approve`  | Approve  | on/off              |

## Структура проекта

```
├── bot.py                  # Точка входа
├── config.py               # Конфигурация (Dynaconf)
├── config.toml             # Параметры по окружениям
├── contract.sol            # Solidity-контракт для свопов
├── alembic/                # Миграции БД
├── chains/                 # Конфигурации сетей (Ethereum, BSC)
├── clients/evm/            # Web3-клиенты
│   ├── scanner.py          # Сканер ликвидности
│   ├── swap.py             # Исполнение свопов
│   ├── token.py            # Сервис токенов
│   ├── wallet.py           # Операции с кошельками
│   └── dex/                # DEX-клиенты (Uniswap, Aerodrome)
├── db/                     # Модели и репозитории (SQLAlchemy)
├── dialogs/                # UI-диалоги (aiogram-dialog)
│   ├── user_menu/          # Главное меню
│   ├── chains_menu/        # Меню сетей
│   ├── wallets_menu/       # Меню кошельков
│   └── settings_menu/      # Меню настроек
├── handlers/               # Обработчики команд и сообщений
├── filters/                # Фильтры сообщений
├── states/                 # FSM-состояния
├── services/               # Бизнес-логика
├── middlewares/             # Middleware (DB, Redis, throttling)
├── keyboards/              # Inline-клавиатуры
├── taskiq_app/             # Фоновые задачи (Taskiq)
└── utils/                  # Утилиты
```

## Лицензия

Private. All rights reserved.
