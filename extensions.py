from flask import current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import pymysql
from pymysql.cursors import DictCursor

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def get_db():
    """Devolve a conexão com o banco da requisição atual.

    A conexão é aberta na primeira chamada e reaproveitada até o fim
    da requisição, quando é fechada por fechar_db().
    """
    if "db" not in g:
        g.db = pymysql.connect(
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            charset="utf8mb4",
            cursorclass=DictCursor,
            connect_timeout=5,
            autocommit=False,
        )
    return g.db


def fechar_db(erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    csrf.init_app(app)
    limiter.init_app(app)
    app.teardown_appcontext(fechar_db)