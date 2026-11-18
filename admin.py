# ============================================================
# PocketFinance AI
# admin.py
# ============================================================

import asyncio
import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Form,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
from starlette.middleware.trustedhost import TrustedHostMiddleware

from database import (
    get_broadcast_users,
)


# ============================================================
# ENV
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ENV_FILE = os.path.join(
    BASE_DIR,
    ".env",
)

load_dotenv(
    ENV_FILE
)

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME"
)

ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD"
)

ADMIN_SECRET_KEY = os.getenv(
    "ADMIN_SECRET_KEY"
)

ADMIN_HOST = os.getenv(
    "ADMIN_HOST",
    "0.0.0.0",
)

ADMIN_PORT = int(
    os.getenv(
        "ADMIN_PORT",
        "8000",
    )
)


# ============================================================
# SECURITY CHECK
# ============================================================

if not ADMIN_USERNAME:
    raise RuntimeError(
        "ADMIN_USERNAME не найден в .env"
    )

if not ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_PASSWORD не найден в .env"
    )

if not ADMIN_SECRET_KEY:
    raise RuntimeError(
        "ADMIN_SECRET_KEY не найден в .env"
    )

if len(ADMIN_SECRET_KEY) < 32:
    raise RuntimeError(
        "ADMIN_SECRET_KEY должен содержать "
        "минимум 32 символа"
    )


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="PocketFinance AI Admin",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


# ============================================================
# HOST PROTECTION
# ============================================================

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "*",
    ],
)


# ============================================================
# LOGIN RATE LIMIT
# ============================================================

LOGIN_ATTEMPTS = defaultdict(list)

MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW = 15 * 60


def is_login_allowed(
    client_ip: str,
) -> bool:

    now = time.time()

    attempts = LOGIN_ATTEMPTS[
        client_ip
    ]

    LOGIN_ATTEMPTS[
        client_ip
    ] = [
        timestamp
        for timestamp in attempts
        if now - timestamp < LOGIN_WINDOW
    ]

    return len(
        LOGIN_ATTEMPTS[
            client_ip
        ]
    ) < MAX_LOGIN_ATTEMPTS


def register_login_attempt(
    client_ip: str,
) -> None:

    LOGIN_ATTEMPTS[
        client_ip
    ].append(
        time.time()
    )


# ============================================================
# SESSION
# ============================================================

SESSION_MAX_AGE = 60 * 60 * 8


def create_session_token(
    csrf_token: str,
) -> str:

    expires = int(
        time.time()
        + SESSION_MAX_AGE
    )

    payload = (
        f"{expires}:{csrf_token}"
    )

    signature = hmac.new(
        ADMIN_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    return (
        f"{expires}:{csrf_token}:{signature}"
    )


def verify_session(
    token: str | None,
):

    if not token:
        return None

    try:

        expires_str, csrf_token, signature = (
            token.split(":")
        )

        expires = int(
            expires_str
        )

    except (
        ValueError,
        TypeError,
    ):

        return None

    if expires < int(
        time.time()
    ):
        return None

    payload = (
        f"{expires}:{csrf_token}"
    )

    expected_signature = hmac.new(
        ADMIN_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        signature,
        expected_signature,
    ):
        return None

    return {
        "csrf": csrf_token,
        "expires": expires,
    }


# ============================================================
# HTML
# ============================================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>PocketFinance AI — Вход</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;

    display: flex;
    align-items: center;
    justify-content: center;

    background: #f5f7fa;
    color: #111827;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

.card {
    width: min(400px, calc(100% - 32px));

    background: white;

    border: 1px solid #e5e7eb;
    border-radius: 18px;

    padding: 30px;

    box-shadow:
        0 10px 30px rgba(0, 0, 0, 0.06);

    position: relative;
}

.language-switch {
    position: absolute;

    top: 18px;
    right: 18px;

    display: flex;
    gap: 4px;
}

.language-switch button {
    border: 1px solid #d1d5db;

    background: white;
    color: #6b7280;

    border-radius: 7px;

    padding: 5px 8px;

    font-size: 11px;
    font-weight: 600;

    cursor: pointer;
}

.language-switch button.active {
    background: #111827;
    color: white;

    border-color: #111827;
}

h1 {
    margin: 0 0 6px;

    font-size: 23px;
}

.subtitle {
    color: #6b7280;

    margin-bottom: 25px;
}

label {
    display: block;

    margin-bottom: 7px;

    font-size: 14px;
    font-weight: 600;
}

input {
    width: 100%;

    padding: 12px 13px;

    border: 1px solid #d1d5db;
    border-radius: 10px;

    font-size: 15px;

    margin-bottom: 16px;

    outline: none;
}

input:focus {
    border-color: #111827;
}

.login-button {
    width: 100%;

    border: 0;
    border-radius: 10px;

    padding: 12px;

    background: #111827;
    color: white;

    font-size: 15px;
    font-weight: 600;

    cursor: pointer;
}

.login-button:hover {
    background: #1f2937;
}

.notice {
    margin-bottom: 16px;

    padding: 11px;

    border-radius: 9px;

    font-size: 14px;
}

.error {
    background: #fef2f2;
    color: #b91c1c;
}

.success {
    background: #ecfdf5;
    color: #047857;
}

</style>

</head>

<body>

<div class="card">

    <div class="language-switch">

        <button
            type="button"
            id="ruButton"
            onclick="setLanguage('ru')"
        >
            RU
        </button>

        <button
            type="button"
            id="enButton"
            onclick="setLanguage('en')"
        >
            EN
        </button>

    </div>

    <h1>
        PocketFinance AI
    </h1>

    <div
        class="subtitle"
        id="subtitle"
    >
        Панель администратора
    </div>

    {notice}

    <form
        method="post"
        action="/admin/login"
    >

        <label
            for="username"
            id="usernameLabel"
        >
            Логин
        </label>

        <input
            id="username"
            type="text"
            name="username"
            autocomplete="username"
            required
        >

        <label
            for="password"
            id="passwordLabel"
        >
            Пароль
        </label>

        <input
            id="password"
            type="password"
            name="password"
            autocomplete="current-password"
            required
        >

        <button
            class="login-button"
            type="submit"
            id="loginButton"
        >
            Войти
        </button>

    </form>

</div>

<script>

function setLanguage(language) {

    document.documentElement.lang =
        language;

    const subtitle =
        document.getElementById(
            "subtitle"
        );

    const usernameLabel =
        document.getElementById(
            "usernameLabel"
        );

    const passwordLabel =
        document.getElementById(
            "passwordLabel"
        );

    const loginButton =
        document.getElementById(
            "loginButton"
        );

    if (language === "en") {

        subtitle.textContent =
            "Administrator panel";

        usernameLabel.textContent =
            "Username";

        passwordLabel.textContent =
            "Password";

        loginButton.textContent =
            "Log in";

    } else {

        subtitle.textContent =
            "Панель администратора";

        usernameLabel.textContent =
            "Логин";

        passwordLabel.textContent =
            "Пароль";

        loginButton.textContent =
            "Войти";
    }

    const notices =
        document.querySelectorAll(
            "[data-ru][data-en]"
        );

    notices.forEach(
        function(notice) {

            notice.textContent =
                notice.getAttribute(
                    "data-" + language
                );

        }
    );

    document
        .getElementById("ruButton")
        .classList.toggle(
            "active",
            language === "ru"
        );

    document
        .getElementById("enButton")
        .classList.toggle(
            "active",
            language === "en"
        );

    localStorage.setItem(
        "admin_language",
        language
    );
}


const savedLanguage =
    localStorage.getItem(
        "admin_language"
    ) || "ru";

setLanguage(
    savedLanguage
);

</script>

</body>
</html>
"""

# ============================================================
# ADMIN HTML
# ============================================================

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>PocketFinance AI — Admin</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;

    background: #f5f7fa;
    color: #111827;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

.container {
    width: min(760px, calc(100% - 32px));

    margin: 45px auto;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    margin-bottom: 25px;
}

h1 {
    margin: 0;

    font-size: 25px;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 14px;
}

.language-switch {
    display: flex;
    gap: 4px;
}

.language-switch button {
    border: 1px solid #d1d5db;

    background: white;
    color: #6b7280;

    border-radius: 8px;

    padding: 6px 9px;

    font-size: 12px;
    font-weight: 600;

    cursor: pointer;
}

.language-switch button.active {
    background: #111827;
    color: white;

    border-color: #111827;
}

.logout {
    color: #6b7280;
    text-decoration: none;

    font-size: 14px;
}

.card {
    background: white;

    border: 1px solid #e5e7eb;
    border-radius: 18px;

    padding: 25px;

    box-shadow:
        0 10px 30px rgba(0, 0, 0, 0.05);
}

.stats {
    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 12px;

    margin-bottom: 24px;
}

.stat {
    background: #f9fafb;

    border-radius: 12px;

    padding: 16px;
}

.stat-title {
    color: #6b7280;

    font-size: 13px;

    margin-bottom: 5px;
}

.stat-value {
    font-size: 22px;
    font-weight: 700;
}

.section {
    margin-top: 25px;
}

.section-title {
    font-size: 15px;
    font-weight: 700;

    margin-bottom: 9px;
}

textarea {
    width: 100%;

    min-height: 170px;

    resize: vertical;

    padding: 13px;

    border: 1px solid #d1d5db;
    border-radius: 11px;

    font-size: 15px;
    line-height: 1.5;

    font-family: inherit;

    outline: none;
}

textarea:focus {
    border-color: #111827;
}

.actions {
    margin-top: 22px;

    display: flex;
    justify-content: flex-end;
}

.send-button {
    border: 0;

    border-radius: 10px;

    padding: 12px 20px;

    background: #111827;
    color: white;

    font-size: 15px;
    font-weight: 600;

    cursor: pointer;
}

.send-button:hover {
    background: #1f2937;
}

.notice {
    margin-top: 20px;

    padding: 12px;

    border-radius: 10px;

    background: #f3f4f6;

    font-size: 14px;
}

.error {
    background: #fef2f2;
    color: #b91c1c;
}

.success {
    background: #ecfdf5;
    color: #047857;
}

.hidden {
    display: none;
}

@media (max-width: 600px) {

    .container {
        margin: 20px auto;
    }

    .card {
        padding: 18px;
    }

    .stats {
        grid-template-columns: 1fr;
    }

    .header {
        align-items: flex-start;
    }

    .header-right {
        gap: 8px;
    }

}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        <h1>
            PocketFinance AI
        </h1>

        <div class="header-right">

            <div class="language-switch">

                <button
                    type="button"
                    id="ruButton"
                    onclick="setLanguage('ru')"
                >
                    RU
                </button>

                <button
                    type="button"
                    id="enButton"
                    onclick="setLanguage('en')"
                >
                    EN
                </button>

            </div>

            <a
                class="logout"
                href="/admin/logout"
                id="logoutLink"
            >
                Выйти
            </a>

        </div>

    </div>

    <div class="card">

        <div class="stats">

            <div class="stat">

                <div
                    class="stat-title"
                    data-ru="🇷🇺 Русский"
                    data-en="🇷🇺 Russian"
                >
                    🇷🇺 Русский
                </div>

                <div class="stat-value">
                    {ru_count}
                </div>

            </div>

            <div class="stat">

                <div
                    class="stat-title"
                    data-ru="🇺🇸 English"
                    data-en="🇺🇸 English"
                >
                    🇺🇸 English
                </div>

                <div class="stat-value">
                    {en_count}
                </div>

            </div>

        </div>

        <form
            method="post"
            action="/admin/broadcast"
            onsubmit="return confirmBroadcast()"
        >

            <input
                type="hidden"
                name="csrf"
                value="{csrf}"
            >

            <div class="section">

                <div
                    class="section-title"
                    data-ru="🇷🇺 Сообщение для русскоязычных"
                    data-en="🇷🇺 Message for Russian users"
                >
                    🇷🇺 Сообщение для русскоязычных
                </div>

                <textarea
                    name="ru_text"
                    maxlength="4096"
                    data-placeholder-ru="Введите сообщение..."
                    data-placeholder-en="Enter message..."
                    placeholder="Введите сообщение..."
                ></textarea>

            </div>

            <div class="section">

                <div
                    class="section-title"
                    data-ru="🇺🇸 Сообщение для англоязычных"
                    data-en="🇺🇸 Message for English users"
                >
                    🇺🇸 Сообщение для англоязычных
                </div>

                <textarea
                    name="en_text"
                    maxlength="4096"
                    data-placeholder-ru="Введите сообщение..."
                    data-placeholder-en="Enter message..."
                    placeholder="Введите сообщение..."
                ></textarea>

            </div>

            <div class="actions">

                <button
                    class="send-button"
                    type="submit"
                    id="sendButton"
                >
                    Отправить рассылку
                </button>

            </div>

        </form>

        {notice}

    </div>

</div>

<script>

function setLanguage(language) {

    document.documentElement.lang = language;

    const elements =
        document.querySelectorAll(
            "[data-ru][data-en]"
        );

    elements.forEach(
        function(element) {

            element.textContent =
                element.getAttribute(
                    "data-" + language
                );

        }
    );

    const textareas =
        document.querySelectorAll(
            "textarea[data-placeholder-ru]"
        );

    textareas.forEach(
        function(textarea) {

            textarea.placeholder =
                textarea.getAttribute(
                    "data-placeholder-" + language
                );

        }
    );

    const logoutLink =
        document.getElementById(
            "logoutLink"
        );

    if (language === "en") {

        logoutLink.textContent =
            "Log out";

    } else {

        logoutLink.textContent =
            "Выйти";

    }

    const sendButton =
        document.getElementById(
            "sendButton"
        );

    if (language === "en") {

        sendButton.textContent =
            "Send broadcast";

    } else {

        sendButton.textContent =
            "Отправить рассылку";

    }

    document
        .getElementById("ruButton")
        .classList.toggle(
            "active",
            language === "ru"
        );

    document
        .getElementById("enButton")
        .classList.toggle(
            "active",
            language === "en"
        );

    localStorage.setItem(
        "admin_language",
        language
    );
}


function confirmBroadcast() {

    const ruText =
        document.querySelector(
            'textarea[name="ru_text"]'
        ).value.trim();

    const enText =
        document.querySelector(
            'textarea[name="en_text"]'
        ).value.trim();

    if (!ruText && !enText) {

        const language =
            localStorage.getItem(
                "admin_language"
            ) || "ru";

        if (language === "en") {

            alert(
                "Enter at least one message."
            );

        } else {

            alert(
                "Введите хотя бы одно сообщение."
            );

        }

        return false;
    }

    const language =
        localStorage.getItem(
            "admin_language"
        ) || "ru";

    if (language === "en") {

        return confirm(
            "Are you sure you want to send this broadcast to all users?"
        );

    }

    return confirm(
        "Вы уверены, что хотите отправить эту рассылку всем пользователям?"
    );
}


const savedLanguage =
    localStorage.getItem(
        "admin_language"
    ) || "ru";

setLanguage(
    savedLanguage
);

</script>

</body>
</html>
"""

# ============================================================
# HELPERS
# ============================================================

def render_login(
    error: str = "",
    success: str = "",
) -> str:

    notice_html = ""

    if success:

        notice_html = (
            '<div '
            'class="notice success" '
            'data-ru="Рассылка успешно завершена. '
            'Теперь войдите снова." '
            'data-en="Broadcast completed successfully. '
            'Please log in again."'
            '>'
            'Рассылка успешно завершена. '
            'Теперь войдите снова.'
            '</div>'
        )

    elif error:

        notice_html = (
            '<div '
            'class="notice error" '
            'data-ru="Неверный логин или пароль." '
            'data-en="Invalid username or password."'
            '>'
            f'{error}'
            '</div>'
        )

    return LOGIN_HTML.replace(
        "{notice}",
        notice_html,
    )


def render_admin(
    csrf: str,
    ru_count: int,
    en_count: int,
    notice: str = "",
) -> str:

    notice_html = ""

    if notice:

        notice_html = (
            f'<div class="notice">'
            f'{notice}'
            f'</div>'
        )

    return (
        ADMIN_HTML
        .replace("{csrf}", csrf)
        .replace("{ru_count}", str(ru_count))
        .replace("{en_count}", str(en_count))
        .replace("{notice}", notice_html)
    )


def get_session(
    request: Request,
):

    token = request.cookies.get(
        "admin_session"
    )

    return verify_session(
        token
    )


# ============================================================
# LOGIN
# ============================================================

@app.get(
    "/admin/login",
    response_class=HTMLResponse,
)
async def admin_login_page(
    request: Request,
):

    session = get_session(
        request
    )

    if session:

        return RedirectResponse(
            "/admin",
            status_code=303,
        )

    broadcast_success = (
        request.query_params.get(
            "broadcast"
        )
        == "success"
    )

    if broadcast_success:

        return HTMLResponse(
            render_login(
                success=(
                    "Рассылка успешно завершена. "
                    "Теперь войдите снова."
                )
            )
        )

    return HTMLResponse(
        render_login()
    )

@app.post(
    "/admin/login",
    response_class=HTMLResponse,
)
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):

    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    if not is_login_allowed(
        client_ip
    ):

        return HTMLResponse(
            render_login(
                "Слишком много попыток. "
                "Попробуйте позже."
            ),
            status_code=429,
        )

    register_login_attempt(
        client_ip
    )

    username_ok = hmac.compare_digest(
        username,
        ADMIN_USERNAME,
    )

    password_ok = hmac.compare_digest(
        password,
        ADMIN_PASSWORD,
    )

    if not (
        username_ok
        and password_ok
    ):

        return HTMLResponse(
            render_login(
                "Неверный логин или пароль."
            ),
            status_code=401,
        )

    csrf_token = secrets.token_urlsafe(
        32
    )

    session_token = create_session_token(
        csrf_token
    )

    response = RedirectResponse(
        "/admin",
        status_code=303,
    )

    response.set_cookie(
        key="admin_session",
        value=session_token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return response


# ============================================================
# ADMIN PAGE
# ============================================================

@app.get(
    "/admin",
    response_class=HTMLResponse,
)
async def admin_page(
    request: Request,
):

    session = get_session(
        request
    )

    if not session:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    users = get_broadcast_users()

    ru_count = sum(
        1
        for user in users
        if user["language"] == "ru"
    )

    en_count = sum(
        1
        for user in users
        if user["language"] == "en"
    )

    return HTMLResponse(
        render_admin(
            csrf=session["csrf"],
            ru_count=ru_count,
            en_count=en_count,
        )
    )


# ============================================================
# BROADCAST
# ============================================================

broadcast_lock = asyncio.Lock()


@app.post(
    "/admin/broadcast",
    response_class=HTMLResponse,
)
async def admin_broadcast(
    request: Request,
    csrf: str = Form(...),
    ru_text: str = Form(""),
    en_text: str = Form(""),
):

    session = get_session(
        request
    )

    if not session:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    if not hmac.compare_digest(
        csrf,
        session["csrf"],
    ):

        return HTMLResponse(
            "Forbidden",
            status_code=403,
        )

    ru_text = ru_text.strip()
    en_text = en_text.strip()

    if not ru_text and not en_text:

        users = get_broadcast_users()

        return HTMLResponse(
            render_admin(
                csrf=session["csrf"],
                ru_count=sum(
                    user["language"] == "ru"
                    for user in users
                ),
                en_count=sum(
                    user["language"] == "en"
                    for user in users
                ),
                notice=(
                    "Введите хотя бы одно сообщение."
                ),
            )
        )

    if len(ru_text) > 4096:

        return HTMLResponse(
            "Русское сообщение слишком длинное.",
            status_code=400,
        )

    if len(en_text) > 4096:

        return HTMLResponse(
            "English message is too long.",
            status_code=400,
        )

    bot = request.app.state.bot

    users = get_broadcast_users()

    ru_users = [
        user
        for user in users
        if user["language"] == "ru"
    ]

    en_users = [
        user
        for user in users
        if user["language"] == "en"
    ]

    async with broadcast_lock:

        ru_sent = 0
        en_sent = 0
        failed = 0

        for user in ru_users:

            if not ru_text:
                continue

            try:

                await bot.send_message(
                    user["telegram_id"],
                    ru_text,
                    disable_web_page_preview=True,
                )

                ru_sent += 1

                await asyncio.sleep(
                    0.04
                )

            except Exception:

                failed += 1

        for user in en_users:

            if not en_text:
                continue

            try:

                await bot.send_message(
                    user["telegram_id"],
                    en_text,
                    disable_web_page_preview=True,
                )

                en_sent += 1

                await asyncio.sleep(
                    0.04
                )

            except Exception:

                failed += 1

    # --------------------------------------------------------
    # ПОСЛЕ РАССЫЛКИ — ВЫХОД ИЗ АДМИНКИ
    # --------------------------------------------------------

    response = RedirectResponse(
        "/admin/login?broadcast=success",
        status_code=303,
    )

    response.delete_cookie(
        key="admin_session",
    )

    return response


# ============================================================
# LOGOUT
# ============================================================

@app.get(
    "/admin/logout",
)
async def admin_logout():

    response = RedirectResponse(
        "/admin/login",
        status_code=303,
    )

    response.delete_cookie(
        "admin_session"
    )

    return response


# ============================================================
# SERVER
# ============================================================

async def run_admin_server(
    bot,
):

    app.state.bot = bot

    import uvicorn

    config = uvicorn.Config(
        app,
        host=ADMIN_HOST,
        port=ADMIN_PORT,
        log_level="warning",
        access_log=False,
    )

    server = uvicorn.Server(
        config
    )

    await server.serve()