from functools import wraps

from flask import abort, flash, redirect, session, url_for

from extensions import get_db


def login_required(funcao):
    @wraps(funcao)
    def verificar(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Faça login para continuar.", "aviso")
            return redirect(url_for("auth.login"))

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT nome, perfil, ativo FROM usuarios WHERE id = %s",
                (session["usuario_id"],),
            )
            usuario = cursor.fetchone()

        if not usuario or not usuario["ativo"]:
            session.clear()
            flash("Seu acesso foi desativado. Procure a coordenação.", "erro")
            return redirect(url_for("auth.login"))

        # Mantém a sessão em dia se o administrador mudou o perfil ou o nome.
        session["perfil"] = usuario["perfil"]
        session["usuario_nome"] = usuario["nome"]

        return funcao(*args, **kwargs)

    return verificar


def perfil_required(*perfis):
    """Exige que o usuário logado tenha um dos perfis informados."""

    def decorador(funcao):
        @wraps(funcao)
        @login_required
        def verificar(*args, **kwargs):
            if session.get("perfil") not in perfis:
                abort(403)
            return funcao(*args, **kwargs)

        return verificar

    return decorador