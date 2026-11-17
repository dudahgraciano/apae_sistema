import re

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pymysql.err import IntegrityError
from werkzeug.security import generate_password_hash

from extensions import get_db
from utils.decorators import perfil_required
from utils.seguranca import avaliar_senha

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

PERFIS = {
    "administrador": "Administrador",
    "colaborador": "Colaborador",
    "visualizador": "Visualizador",
}

PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------
# Funções de apoio
# ---------------------------------------------------------------------

def buscar_usuario(cursor, usuario_id):
    cursor.execute(
        "SELECT id, nome, email, perfil, ativo, criado_em "
        "FROM usuarios WHERE id = %s",
        (usuario_id,),
    )
    return cursor.fetchone()


def outros_admins_ativos(cursor, usuario_id):
    """Quantos administradores ativos existem além deste usuário."""
    cursor.execute(
        "SELECT COUNT(*) AS total FROM usuarios "
        "WHERE perfil = 'administrador' AND ativo = 1 AND id <> %s",
        (usuario_id,),
    )
    return cursor.fetchone()["total"]


def validar_senha(senha, confirmacao):
    erros = avaliar_senha(senha)
    if senha != confirmacao:
        erros.append("As duas senhas digitadas não são iguais.")
    return erros

def validar_dados(cursor, formulario, usuario_id=0):
    """Valida nome, e-mail e perfil. Devolve (dados, erros)."""
    erros = []

    nome = formulario.get("nome", "").strip()
    email = formulario.get("email", "").strip().lower()
    perfil = formulario.get("perfil", "").strip()

    if len(nome) < 3:
        erros.append("Informe o nome completo (mínimo de 3 letras).")
    elif len(nome) > 120:
        erros.append("O nome pode ter no máximo 120 letras.")

    if not PADRAO_EMAIL.match(email) or len(email) > 150:
        erros.append("Informe um e-mail válido.")
    else:
        cursor.execute(
            "SELECT id FROM usuarios WHERE email = %s AND id <> %s",
            (email, usuario_id),
        )
        if cursor.fetchone():
            erros.append("Já existe um usuário com este e-mail.")

    if perfil not in PERFIS:
        erros.append("Escolha o perfil de acesso.")

    return {"nome": nome, "email": email, "perfil": perfil}, erros


# ---------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------

@usuarios_bp.route("/")
@perfil_required("administrador")
def listar():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT u.id, u.nome, u.email, u.perfil, u.ativo, u.criado_em, "
            "       (SELECT COUNT(*) FROM atividades a WHERE a.usuario_id = u.id) "
            "           AS total_atividades "
            "FROM usuarios u "
            "ORDER BY u.ativo DESC, u.nome"
        )
        usuarios = cursor.fetchall()

    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        perfis=PERFIS,
        usuario_atual=session["usuario_id"],
    )


# ---------------------------------------------------------------------
# Cadastro
# ---------------------------------------------------------------------

@usuarios_bp.route("/novo", methods=["GET", "POST"])
@perfil_required("administrador")
def novo():
    if request.method == "POST":
        db = get_db()
        with db.cursor() as cursor:
            dados, erros = validar_dados(cursor, request.form)
            erros += validar_senha(
                request.form.get("senha", ""), request.form.get("confirmacao", "")
            )

            if not erros:
                try:
                    cursor.execute(
                        "INSERT INTO usuarios (nome, email, senha_hash, perfil) "
                        "VALUES (%s, %s, %s, %s)",
                        (
                            dados["nome"],
                            dados["email"],
                            generate_password_hash(request.form["senha"]),
                            dados["perfil"],
                        ),
                    )
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    erros.append("Já existe um usuário com este e-mail.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template(
                "usuario_form.html",
                usuario=dados,
                perfis=PERFIS,
                editando=False,
                proprio=False,
            ), 400

        flash("Usuário cadastrado com sucesso.", "sucesso")
        return redirect(url_for("usuarios.listar"))

    return render_template(
        "usuario_form.html",
        usuario={"perfil": "colaborador"},
        perfis=PERFIS,
        editando=False,
        proprio=False,
    )


# ---------------------------------------------------------------------
# Edição
# ---------------------------------------------------------------------

@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@perfil_required("administrador")
def editar(usuario_id):
    db = get_db()
    with db.cursor() as cursor:
        usuario = buscar_usuario(cursor, usuario_id)
        if not usuario:
            abort(404)

        proprio = usuario_id == session["usuario_id"]

        if request.method == "POST":
            dados, erros = validar_dados(cursor, request.form, usuario_id)

            if proprio:
                # Evita o administrador se rebaixar e perder o acesso a esta tela.
                dados["perfil"] = usuario["perfil"]
            elif (
                usuario["perfil"] == "administrador"
                and usuario["ativo"]
                and dados["perfil"] != "administrador"
                and outros_admins_ativos(cursor, usuario_id) == 0
            ):
                erros.append("O sistema precisa ter pelo menos um administrador ativo.")

            if not erros:
                try:
                    cursor.execute(
                        "UPDATE usuarios SET nome = %s, email = %s, perfil = %s "
                        "WHERE id = %s",
                        (dados["nome"], dados["email"], dados["perfil"], usuario_id),
                    )
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    erros.append("Já existe um usuário com este e-mail.")

            if erros:
                for erro in erros:
                    flash(erro, "erro")
                formulario = dict(dados)
                formulario["id"] = usuario_id
                formulario["ativo"] = usuario["ativo"]
                return render_template(
                    "usuario_form.html",
                    usuario=formulario,
                    perfis=PERFIS,
                    editando=True,
                    proprio=proprio,
                ), 400

            flash("Alterações salvas com sucesso.", "sucesso")
            return redirect(url_for("usuarios.listar"))

    return render_template(
        "usuario_form.html",
        usuario=usuario,
        perfis=PERFIS,
        editando=True,
        proprio=proprio,
    )


# ---------------------------------------------------------------------
# Redefinir senha
# ---------------------------------------------------------------------

@usuarios_bp.route("/<int:usuario_id>/senha", methods=["POST"])
@perfil_required("administrador")
def redefinir_senha(usuario_id):
    db = get_db()
    with db.cursor() as cursor:
        usuario = buscar_usuario(cursor, usuario_id)
        if not usuario:
            abort(404)

        erros = validar_senha(
            request.form.get("senha", ""), request.form.get("confirmacao", "")
        )
        if erros:
            for erro in erros:
                flash(erro, "erro")
            return redirect(url_for("usuarios.editar", usuario_id=usuario_id))

        cursor.execute(
            "UPDATE usuarios SET senha_hash = %s WHERE id = %s",
            (generate_password_hash(request.form["senha"]), usuario_id),
        )
        db.commit()

    flash(f"Senha de {usuario['nome']} redefinida com sucesso.", "sucesso")
    return redirect(url_for("usuarios.listar"))


# ---------------------------------------------------------------------
# Ativar / desativar
# ---------------------------------------------------------------------

@usuarios_bp.route("/<int:usuario_id>/alternar", methods=["POST"])
@perfil_required("administrador")
def alternar(usuario_id):
    if usuario_id == session["usuario_id"]:
        flash("Você não pode desativar o seu próprio acesso.", "erro")
        return redirect(url_for("usuarios.listar"))

    db = get_db()
    with db.cursor() as cursor:
        usuario = buscar_usuario(cursor, usuario_id)
        if not usuario:
            abort(404)

        if (
            usuario["ativo"]
            and usuario["perfil"] == "administrador"
            and outros_admins_ativos(cursor, usuario_id) == 0
        ):
            flash("O sistema precisa ter pelo menos um administrador ativo.", "erro")
            return redirect(url_for("usuarios.listar"))

        novo_estado = 0 if usuario["ativo"] else 1
        cursor.execute(
            "UPDATE usuarios SET ativo = %s WHERE id = %s", (novo_estado, usuario_id)
        )
        db.commit()

    if novo_estado:
        flash(f"Acesso de {usuario['nome']} reativado.", "sucesso")
    else:
        flash(f"Acesso de {usuario['nome']} desativado.", "sucesso")
    return redirect(url_for("usuarios.listar"))