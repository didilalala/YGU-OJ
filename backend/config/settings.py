"""
YGU OJ 后端配置。

所有环境相关的值都从环境变量读取：本地开发写在 backend/.env，
Docker 部署由 deploy/.env 经 docker-compose 注入。
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    return [item.strip() for item in env(key, default).split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY 未设置，请参考 backend/.env.example")

DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "account",
    "announcement",
    "problem",
    "submission",
    "judge",
    "contest",
    "classroom",
    "stats",
    "options",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------- 数据库与缓存

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": env("MYSQL_HOST", "127.0.0.1"),
        "PORT": int(env("MYSQL_PORT", "3306")),
        "NAME": env("MYSQL_DATABASE", "oj"),
        "USER": env("MYSQL_USER", "oj"),
        "PASSWORD": env("MYSQL_PASSWORD", ""),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

REDIS_URL = env("REDIS_URL", "redis://127.0.0.1:6379")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/0",
        "KEY_PREFIX": "oj",
    }
}

# ---------------------------------------------------------------- 认证

AUTH_USER_MODEL = "account.User"

AUTHENTICATION_BACKENDS = ["account.backends.UsernameOrEmailBackend"]

# 第一个为默认哈希器；InitialPasswordHasher 只用于批量生成的初始密码，见 account/hashers.py
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "account.hashers.InitialPasswordHasher",
]

# 学号格式（导入学生时校验），可按学校实际情况通过环境变量调整
STUDENT_NO_PATTERN = env("STUDENT_NO_PATTERN", r"^\d{4,20}$")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["utils.renderers.UnifiedJSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "utils.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "utils.exceptions.exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")

# 后端只能经由 Nginx 访问时开启，见 utils.request.get_client_ip
TRUST_X_REAL_IP = env_bool("TRUST_X_REAL_IP", False)

# ---------------------------------------------------------------- Celery 与判题

CELERY_BROKER_URL = env("CELERY_BROKER_URL", f"{REDIS_URL}/1")
CELERY_RESULT_BACKEND = None
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TIMEZONE = "Asia/Shanghai"

# 判题服务器（QDUOJ JudgeServer）的通信令牌，与 judge-server 容器的 TOKEN 一致
JUDGE_SERVER_TOKEN = env("JUDGE_SERVER_TOKEN", "")

# ---------------------------------------------------------------- 文件目录

DATA_DIR = Path(env("OJ_DATA_DIR", BASE_DIR.parent / "data"))
TEST_CASE_DIR = DATA_DIR / "test_case"
LOG_DIR = DATA_DIR / "log"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = DATA_DIR / "upload"

# ---------------------------------------------------------------- 国际化

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
