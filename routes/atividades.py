from datetime import date, datetime

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

from extensions import get_db
from utils.decorators import login_required, perfil_required
from flask import current_app
from utils.uploads import apagar_arquivos

atividades_bp = Blueprint("atividades", __name__, url_prefix="/atividades")

POR_PAGINA = 15


# ---------------------------------------------------------------------
# Funções de apoio
# ---------------------------------------------------------------------

def buscar_listas(cursor):
    """Turmas e categorias ativas, para os campos de seleção."""
    cursor.execute("SELECT id, nome FROM turmas WHERE ativa = 1 ORDER BY nome")
    turmas = cursor.fetchall()
    cursor.execute("SELECT id, nome FROM categorias WHERE ativa = 1 ORDER BY nome")
    categorias = cursor.fetchall()
    return turmas, categorias


def buscar_atividade(cursor, atividade_id):
    cursor.execute(
        "SELECT a.id, a.nome, a.descricao, a.data_realizacao, a.turma_id, "
        "       a.categoria_id, a.usuario_id, a.criado_em, a.atualizado_em, "
        "       t.nome AS turma, c.nome AS categoria, u.nome AS responsavel "
        "FROM atividades a "
        "JOIN turmas t ON t.id = a.turma_id "
        "JOIN categorias c ON c.id = a.categoria_id "
        "JOIN usuarios u ON u.id = a.usuario_id "
        "WHERE a.id = %s",
        (atividade_id,),
    )
    return cursor.fetchone()


def pode_alterar(atividade):
    """Administrador altera qualquer uma; colaborador, só as próprias."""
    perfil = session.get("perfil")
    if perfil == "administrador":
        return True
    return perfil == "colaborador" and atividade["usuario_id"] == session.get("usuario_id")


def validar_formulario(cursor, formulario):
    """Valida os campos e devolve (dados_limpos, lista_de_erros)."""
    erros = []

    nome = formulario.get("nome", "").strip()
    descricao = formulario.get("descricao", "").strip()
    data_texto = formulario.get("data_realizacao", "").strip()
    turma_texto = formulario.get("turma_id", "").strip()
    categoria_texto = formulario.get("categoria_id", "").strip()

    if len(nome) < 3:
        erros.append("Informe o nome da atividade (mínimo de 3 letras).")
    elif len(nome) > 150:
        erros.append("O nome da atividade pode ter no máximo 150 letras.")

    if len(descricao) > 3000:
        erros.append("A descrição pode ter no máximo 3000 caracteres.")

    data_realizacao = None
    try:
        data_realizacao = datetime.strptime(data_texto, "%Y-%m-%d").date()
        if data_realizacao > date.today():
            erros.append("A data da atividade não pode estar no futuro.")
        elif data_realizacao.year < 2000:
            erros.append("Confira a data da atividade: o ano parece incorreto.")
    except ValueError:
        erros.append("Informe a data em que a atividade foi realizada.")

    turma_id = None
    if turma_texto.isdigit():
        cursor.execute(
            "SELECT id FROM turmas WHERE id = %s AND ativa = 1", (int(turma_texto),)
        )
        if cursor.fetchone():
            turma_id = int(turma_texto)
    if turma_id is None:
        erros.append("Escolha a turma.")

    categoria_id = None
    if categoria_texto.isdigit():
        cursor.execute(
            "SELECT id FROM categorias WHERE id = %s AND ativa = 1",
            (int(categoria_texto),),
        )
        if cursor.fetchone():
            categoria_id = int(categoria_texto)
    if categoria_id is None:
        erros.append("Escolha a categoria.")

    dados = {
        "nome": nome,
        "descricao": descricao,
        "data_realizacao": data_realizacao,
        "turma_id": turma_id,
        "categoria_id": categoria_id,
    }
    return dados, erros


# ---------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------

@atividades_bp.route("/")
@login_required
def listar():
    busca = request.args.get("busca", "").strip()[:100]
    turma = request.args.get("turma", "").strip()
    categoria = request.args.get("categoria", "").strip()
    data_inicio = request.args.get("de", "").strip()
    data_fim = request.args.get("ate", "").strip()
    pagina = request.args.get("pagina", "1")
    pagina = int(pagina) if pagina.isdigit() and int(pagina) > 0 else 1

    condicoes = []
    parametros = []

    if busca:
        condicoes.append("a.nome LIKE %s")
        parametros.append("%" + busca.replace("%", "\\%").replace("_", "\\_") + "%")
    if turma.isdigit():
        condicoes.append("a.turma_id = %s")
        parametros.append(int(turma))
    if categoria.isdigit():
        condicoes.append("a.categoria_id = %s")
        parametros.append(int(categoria))
    for texto, operador in ((data_inicio, ">="), (data_fim, "<=")):
        if texto:
            try:
                valor = datetime.strptime(texto, "%Y-%m-%d").date()
                condicoes.append(f"a.data_realizacao {operador} %s")
                parametros.append(valor)
            except ValueError:
                pass

    onde = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""

    db = get_db()
    with db.cursor() as cursor:
        turmas, categorias = buscar_listas(cursor)

        cursor.execute(f"SELECT COUNT(*) AS total FROM atividades a {onde}", parametros)
        total = cursor.fetchone()["total"]

        total_paginas = max(1, -(-total // POR_PAGINA))
        pagina = min(pagina, total_paginas)

        cursor.execute(
            "SELECT a.id, a.nome, a.data_realizacao, a.usuario_id, "
            "       t.nome AS turma, c.nome AS categoria, "
            "       (SELECT COUNT(*) FROM midias m WHERE m.atividade_id = a.id) AS total_midias "
            "FROM atividades a "
            "JOIN turmas t ON t.id = a.turma_id "
            "JOIN categorias c ON c.id = a.categoria_id "
            f"{onde} "
            "ORDER BY a.data_realizacao DESC, a.id DESC "
            "LIMIT %s OFFSET %s",
            parametros + [POR_PAGINA, (pagina - 1) * POR_PAGINA],
        )
        atividades = cursor.fetchall()

    filtros = {
        "busca": busca,
        "turma": turma,
        "categoria": categoria,
        "de": data_inicio,
        "ate": data_fim,
    }
    filtros_ativos = any(filtros.values())

    return render_template(
        "atividades.html",
        atividades=atividades,
        turmas=turmas,
        categorias=categorias,
        filtros=filtros,
        filtros_ativos=filtros_ativos,
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
    )


# ---------------------------------------------------------------------
# Cadastro
# ---------------------------------------------------------------------

@atividades_bp.route("/nova", methods=["GET", "POST"])
@perfil_required("administrador", "colaborador")
def nova():
    db = get_db()
    with db.cursor() as cursor:
        turmas, categorias = buscar_listas(cursor)

        if request.method == "POST":
            dados, erros = validar_formulario(cursor, request.form)

            if erros:
                for erro in erros:
                    flash(erro, "erro")
                return render_template(
                    "cadastro_atividade.html",
                    turmas=turmas,
                    categorias=categorias,
                    atividade=request.form,
                    editando=False,
                    hoje=date.today().isoformat(),
                ), 400

            cursor.execute(
                "INSERT INTO atividades "
                "(nome, descricao, data_realizacao, turma_id, categoria_id, usuario_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    dados["nome"],
                    dados["descricao"] or None,
                    dados["data_realizacao"],
                    dados["turma_id"],
                    dados["categoria_id"],
                    session["usuario_id"],
                ),
            )
            novo_id = cursor.lastrowid
            db.commit()

            flash("Atividade cadastrada com sucesso.", "sucesso")
            return redirect(url_for("atividades.detalhe", atividade_id=novo_id))

    return render_template(
        "cadastro_atividade.html",
        turmas=turmas,
        categorias=categorias,
        atividade={},
        editando=False,
        hoje=date.today().isoformat(),
    )


# ---------------------------------------------------------------------
# Detalhes
# ---------------------------------------------------------------------

@atividades_bp.route("/<int:atividade_id>")
@login_required
def detalhe(atividade_id):
    db = get_db()
    with db.cursor() as cursor:
        atividade = buscar_atividade(cursor, atividade_id)
        if not atividade:
            abort(404)

        cursor.execute(
            "SELECT id, nome_original, tipo, tamanho_bytes, enviado_em "
            "FROM midias WHERE atividade_id = %s ORDER BY enviado_em, id",
            (atividade_id,),
        )
        midias = cursor.fetchall()

    total_fotos = sum(1 for m in midias if m["tipo"] == "foto")
    total_videos = sum(1 for m in midias if m["tipo"] == "video")

    return render_template(
        "detalhe_atividade.html",
        atividade=atividade,
        midias=midias,
        total_fotos=total_fotos,
        total_videos=total_videos,
        pode_alterar=pode_alterar(atividade),
    )

# ---------------------------------------------------------------------
# Edição
# ---------------------------------------------------------------------

@atividades_bp.route("/<int:atividade_id>/editar", methods=["GET", "POST"])
@perfil_required("administrador", "colaborador")
def editar(atividade_id):
    db = get_db()
    with db.cursor() as cursor:
        atividade = buscar_atividade(cursor, atividade_id)
        if not atividade:
            abort(404)
        if not pode_alterar(atividade):
            abort(403)

        turmas, categorias = buscar_listas(cursor)

        if request.method == "POST":
            dados, erros = validar_formulario(cursor, request.form)

            if erros:
                for erro in erros:
                    flash(erro, "erro")
                formulario = dict(request.form)
                formulario["id"] = atividade_id
                return render_template(
                    "cadastro_atividade.html",
                    turmas=turmas,
                    categorias=categorias,
                    atividade=formulario,
                    editando=True,
                    hoje=date.today().isoformat(),
                ), 400

            cursor.execute(
                "UPDATE atividades SET nome = %s, descricao = %s, "
                "data_realizacao = %s, turma_id = %s, categoria_id = %s "
                "WHERE id = %s",
                (
                    dados["nome"],
                    dados["descricao"] or None,
                    dados["data_realizacao"],
                    dados["turma_id"],
                    dados["categoria_id"],
                    atividade_id,
                ),
            )
            db.commit()

            flash("Alterações salvas com sucesso.", "sucesso")
            return redirect(url_for("atividades.detalhe", atividade_id=atividade_id))

    return render_template(
        "cadastro_atividade.html",
        turmas=turmas,
        categorias=categorias,
        atividade={
            "id": atividade["id"],
            "nome": atividade["nome"],
            "descricao": atividade["descricao"] or "",
            "data_realizacao": atividade["data_realizacao"].isoformat(),
            "turma_id": atividade["turma_id"],
            "categoria_id": atividade["categoria_id"],
        },
        editando=True,
        hoje=date.today().isoformat(),
    )


# ---------------------------------------------------------------------
# Exclusão
# ---------------------------------------------------------------------

@atividades_bp.route("/<int:atividade_id>/excluir", methods=["POST"])
@perfil_required("administrador", "colaborador")
def excluir(atividade_id):
    db = get_db()
    with db.cursor() as cursor:
        atividade = buscar_atividade(cursor, atividade_id)
        if not atividade:
            abort(404)
        if not pode_alterar(atividade):
            abort(403)

        cursor.execute(
            "SELECT nome_arquivo FROM midias WHERE atividade_id = %s", (atividade_id,)
        )
        nomes = [linha["nome_arquivo"] for linha in cursor.fetchall()]

        # As mídias do banco são removidas em cascata (ON DELETE CASCADE).
        cursor.execute("DELETE FROM atividades WHERE id = %s", (atividade_id,))
        db.commit()

    apagar_arquivos(current_app.config, nomes)

    flash("Atividade excluída.", "sucesso")
    return redirect(url_for("atividades.listar"))