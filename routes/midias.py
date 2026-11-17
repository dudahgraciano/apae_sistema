from datetime import datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from extensions import get_db
from routes.atividades import buscar_atividade, buscar_listas, pode_alterar
from utils.decorators import login_required, perfil_required
from utils.uploads import (
    ErroUpload,
    apagar_arquivos,
    pasta_do_tipo,
    pasta_miniaturas,
    processar_arquivo,
)

midias_bp = Blueprint("midias", __name__)

MAX_ARQUIVOS_POR_ENVIO = 50
POR_PAGINA_GALERIA = 24


# ---------------------------------------------------------------------
# Galeria
# ---------------------------------------------------------------------

@midias_bp.route("/galeria")
@login_required
def galeria():
    busca = request.args.get("busca", "").strip()[:100]
    turma = request.args.get("turma", "").strip()
    categoria = request.args.get("categoria", "").strip()
    tipo = request.args.get("tipo", "").strip()
    if tipo not in ("foto", "video"):
        tipo = ""
    data_inicio = request.args.get("de", "").strip()
    data_fim = request.args.get("ate", "").strip()
    pagina = request.args.get("pagina", "1")
    pagina = int(pagina) if pagina.isdigit() and int(pagina) > 0 else 1

    condicoes = []
    parametros = []

    if busca:
        padrao = "%" + (
            busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        ) + "%"
        condicoes.append("(a.nome LIKE %s OR m.nome_original LIKE %s)")
        parametros.extend([padrao, padrao])
    if turma.isdigit():
        condicoes.append("a.turma_id = %s")
        parametros.append(int(turma))
    if categoria.isdigit():
        condicoes.append("a.categoria_id = %s")
        parametros.append(int(categoria))
    if tipo:
        condicoes.append("m.tipo = %s")
        parametros.append(tipo)
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

        cursor.execute(
            "SELECT COUNT(*) AS total "
            "FROM midias m JOIN atividades a ON a.id = m.atividade_id "
            f"{onde}",
            parametros,
        )
        total = cursor.fetchone()["total"]

        total_paginas = max(1, -(-total // POR_PAGINA_GALERIA))
        pagina = min(pagina, total_paginas)

        cursor.execute(
            "SELECT m.id, m.nome_original, m.tipo, "
            "       a.id AS atividade_id, a.nome AS atividade, "
            "       a.data_realizacao, a.usuario_id, "
            "       t.nome AS turma, c.nome AS categoria "
            "FROM midias m "
            "JOIN atividades a ON a.id = m.atividade_id "
            "JOIN turmas t ON t.id = a.turma_id "
            "JOIN categorias c ON c.id = a.categoria_id "
            f"{onde} "
            "ORDER BY a.data_realizacao DESC, m.id DESC "
            "LIMIT %s OFFSET %s",
            parametros + [POR_PAGINA_GALERIA, (pagina - 1) * POR_PAGINA_GALERIA],
        )
        midias = cursor.fetchall()

    perfil = session.get("perfil")
    usuario_id = session.get("usuario_id")
    for m in midias:
        m["pode"] = perfil == "administrador" or (
            perfil == "colaborador" and m["usuario_id"] == usuario_id
        )

    filtros = {
        "busca": busca,
        "turma": turma,
        "categoria": categoria,
        "tipo": tipo,
        "de": data_inicio,
        "ate": data_fim,
    }

    return render_template(
        "galeria.html",
        midias=midias,
        turmas=turmas,
        categorias=categorias,
        filtros=filtros,
        filtros_ativos=any(filtros.values()),
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
    )


# ---------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------

@midias_bp.route("/atividades/<int:atividade_id>/midias", methods=["POST"])
@perfil_required("administrador", "colaborador")
def enviar(atividade_id):
    db = get_db()
    with db.cursor() as cursor:
        atividade = buscar_atividade(cursor, atividade_id)
        if not atividade:
            return jsonify(erro="Atividade não encontrada."), 404
        if not pode_alterar(atividade):
            return jsonify(erro="Você não tem permissão para enviar arquivos a esta atividade."), 403

    if request.form.get("autorizacao") != "1":
        return jsonify(
            erro="Confirme a autorização de uso de imagem dos alunos antes de enviar."
        ), 400
    arquivos = [a for a in request.files.getlist("arquivos") if a and a.filename]

    if not arquivos:
        return jsonify(erro="Escolha ao menos um arquivo para enviar."), 400
    if len(arquivos) > MAX_ARQUIVOS_POR_ENVIO:
        return jsonify(
            erro=f"Envie no máximo {MAX_ARQUIVOS_POR_ENVIO} arquivos de cada vez."
        ), 400
    arquivos = [a for a in request.files.getlist("arquivos") if a and a.filename]

    config = current_app.config
    enviados = []
    falhas = []

    for arquivo in arquivos:
        nome_exibido = arquivo.filename
        try:
            dados = processar_arquivo(arquivo, config)
        except ErroUpload as erro:
            falhas.append({"nome": nome_exibido, "motivo": str(erro)})
            continue
        except Exception:
            current_app.logger.exception("Falha inesperada ao processar upload")
            falhas.append({"nome": nome_exibido, "motivo": "ocorreu um erro ao salvar este arquivo."})
            continue

        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO midias "
                    "(atividade_id, nome_original, nome_arquivo, tipo, mime_type, "
                    " tamanho_bytes, enviado_por) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        atividade_id,
                        dados["nome_original"],
                        dados["nome_arquivo"],
                        dados["tipo"],
                        dados["mime_type"],
                        dados["tamanho_bytes"],
                        session["usuario_id"],
                    ),
                )
            db.commit()
            enviados.append(dados["nome_original"])
        except Exception:
            db.rollback()
            apagar_arquivos(config, [dados["nome_arquivo"]])
            current_app.logger.exception("Falha ao registrar mídia no banco")
            falhas.append({"nome": nome_exibido, "motivo": "não foi possível registrar o arquivo."})

    if enviados:
        quantidade = len(enviados)
        flash(
            f"{quantidade} {'arquivo enviado' if quantidade == 1 else 'arquivos enviados'} com sucesso.",
            "sucesso",
        )

    status = 200 if enviados else 400
    return jsonify(enviados=enviados, falhas=falhas,
                   destino=url_for("atividades.detalhe", atividade_id=atividade_id)), status


# ---------------------------------------------------------------------
# Entrega protegida dos arquivos
# ---------------------------------------------------------------------

def buscar_midia(midia_id):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT id, atividade_id, nome_original, nome_arquivo, tipo, mime_type "
            "FROM midias WHERE id = %s",
            (midia_id,),
        )
        return cursor.fetchone()


@midias_bp.route("/midias/<int:midia_id>/arquivo")
@login_required
def arquivo(midia_id):
    midia = buscar_midia(midia_id)
    if not midia:
        abort(404)

    resposta = send_from_directory(
        pasta_do_tipo(current_app.config, midia["tipo"]),
        midia["nome_arquivo"],
        mimetype=midia["mime_type"],
        conditional=True,  # permite avançar e voltar nos vídeos
    )
    resposta.headers["Cache-Control"] = "private, max-age=3600"
    return resposta


@midias_bp.route("/midias/<int:midia_id>/miniatura")
@login_required
def miniatura(midia_id):
    midia = buscar_midia(midia_id)
    if not midia or midia["tipo"] != "foto":
        abort(404)

    base = midia["nome_arquivo"].rsplit(".", 1)[0]
    resposta = send_from_directory(
        pasta_miniaturas(current_app.config),
        f"{base}.jpg",
        mimetype="image/jpeg",
    )
    resposta.headers["Cache-Control"] = "private, max-age=3600"
    return resposta


@midias_bp.route("/midias/<int:midia_id>/baixar")
@login_required
def baixar(midia_id):
    midia = buscar_midia(midia_id)
    if not midia:
        abort(404)

    return send_from_directory(
        pasta_do_tipo(current_app.config, midia["tipo"]),
        midia["nome_arquivo"],
        mimetype=midia["mime_type"],
        as_attachment=True,
        download_name=midia["nome_original"],
    )


# ---------------------------------------------------------------------
# Exclusão de uma mídia
# ---------------------------------------------------------------------

@midias_bp.route("/midias/<int:midia_id>/excluir", methods=["POST"])
@perfil_required("administrador", "colaborador")
def excluir(midia_id):
    midia = buscar_midia(midia_id)
    if not midia:
        abort(404)

    db = get_db()
    with db.cursor() as cursor:
        atividade = buscar_atividade(cursor, midia["atividade_id"])
        if not atividade:
            abort(404)
        if not pode_alterar(atividade):
            abort(403)

        cursor.execute("DELETE FROM midias WHERE id = %s", (midia_id,))
        db.commit()

    apagar_arquivos(current_app.config, [midia["nome_arquivo"]])
    flash("Arquivo excluído.", "sucesso")

    # Quem excluiu pela galeria volta para a galeria.
    if request.form.get("voltar") == "galeria":
        return redirect(url_for("midias.galeria"))
    return redirect(url_for("atividades.detalhe", atividade_id=midia["atividade_id"]))