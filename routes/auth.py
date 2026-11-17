from urllib.parse import urlparse

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from extensions import get_db, limiter

auth_bp = Blueprint("auth", __name__)

# Hash falso usado para gastar o mesmo tempo quando o e-mail não existe,
# evitando que alguém descubra quais e-mails estão cadastrados.
HASH_FALSO = (
    "scrypt:32768:8:1$aaaaaaaaaaaaaaaa$"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)


def destino_seguro(destino):
    """Aceita apenas caminhos internos do sistema (evita redirecionamento externo)."""
    if not destino:
        return None
    partes = urlparse(destino)
    if partes.scheme or partes.netloc or not destino.startswith("/"):
        return None
    if destino.startswith("//"):
        return None
    return destino


@auth_bp.route("/", methods=["GET"])
def inicio():
    if "usuario_id" in session:
        return redirect(url_for("dashboard.painel"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if "usuario_id" in session:
        return redirect(url_for("dashboard.painel"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        if not email or not senha:
            flash("Informe o e-mail e a senha.", "erro")
            return render_template("login.html"), 400

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, senha_hash, perfil, ativo "
                "FROM usuarios WHERE email = %s",
                (email,),
            )
            usuario = cursor.fetchone()

        if usuario:
            senha_confere = check_password_hash(usuario["senha_hash"], senha)
        else:
            check_password_hash(HASH_FALSO, senha)
            senha_confere = False

        if not usuario or not senha_confere:
            flash("E-mail ou senha incorretos.", "erro")
            return render_template("login.html", email=email), 401

        if not usuario["ativo"]:
            flash("Este acesso está desativado. Procure a coordenação.", "erro")
            return render_template("login.html", email=email), 403

        session.clear()
        session.permanent = True
        session["usuario_id"] = usuario["id"]
        session["usuario_nome"] = usuario["nome"]
        session["perfil"] = usuario["perfil"]

        destino = destino_seguro(request.args.get("next"))
        return redirect(destino or url_for("dashboard.painel"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Você saiu do sistema.", "sucesso")
    return redirect(url_for("auth.login"))