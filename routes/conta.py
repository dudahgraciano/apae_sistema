from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import get_db
from utils.decorators import login_required
from utils.seguranca import avaliar_senha

conta_bp = Blueprint("conta", __name__, url_prefix="/conta")


@conta_bp.route("/", methods=["GET", "POST"])
@login_required
def minha_conta():
    db = get_db()

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT nome, email, perfil, senha_hash FROM usuarios WHERE id = %s",
            (session["usuario_id"],),
        )
        usuario = cursor.fetchone()

    if request.method == "POST":
        atual = request.form.get("senha_atual", "")
        nova = request.form.get("senha_nova", "")
        confirmacao = request.form.get("confirmacao", "")

        erros = []
        if not check_password_hash(usuario["senha_hash"], atual):
            erros.append("A senha atual está incorreta.")
        erros += avaliar_senha(nova)
        if nova != confirmacao:
            erros.append("A nova senha e a confirmação não são iguais.")
        if not erros and check_password_hash(usuario["senha_hash"], nova):
            erros.append("A nova senha precisa ser diferente da atual.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template("conta.html", usuario=usuario), 400

        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET senha_hash = %s WHERE id = %s",
                (generate_password_hash(nova), session["usuario_id"]),
            )
        db.commit()

        flash("Senha alterada com sucesso.", "sucesso")
        return redirect(url_for("conta.minha_conta"))

    return render_template("conta.html", usuario=usuario)