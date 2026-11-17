from flask import current_app, g, request, session

from extensions import get_db

ROTULOS = {
    "login": "Entrou no sistema",
    "login_falha": "Tentativa de entrada recusada",
    "saida": "Saiu do sistema",
    "atividade_criada": "Atividade cadastrada",
    "atividade_editada": "Atividade editada",
    "atividade_excluida": "Atividade excluída",
    "midias_enviadas": "Arquivos enviados",
    "midia_excluida": "Arquivo excluído",
    "usuario_criado": "Usuário cadastrado",
    "usuario_editado": "Usuário editado",
    "senha_redefinida": "Senha redefinida",
    "usuario_acesso_alterado": "Acesso ativado ou desativado",
}


def _id(chave):
    return (request.view_args or {}).get(chave)


def _alvo():
    return g.get("auditoria_alvo", "")


# endpoint -> (ação, função que monta o detalhe)
ACOES = {
    "auth.logout": ("saida", lambda r: None),
    "atividades.nova": (
        "atividade_criada",
        lambda r: request.form.get("nome", "")[:150],
    ),
    "atividades.editar": (
        "atividade_editada",
        lambda r: f"{request.form.get('nome', '')[:150]} (atividade {_id('atividade_id')})",
    ),
    "atividades.excluir": (
        "atividade_excluida",
        lambda r: f"{_alvo()} (atividade {_id('atividade_id')})",
    ),
    "midias.enviar": (
        "midias_enviadas",
        lambda r: (
            f"{len((r.get_json(silent=True) or {}).get('enviados', []))} arquivo(s) "
            f"na atividade {_id('atividade_id')}; autorização de uso de imagem confirmada"
        ),
    ),
    "midias.excluir": (
        "midia_excluida",
        lambda r: f"{_alvo()} (arquivo {_id('midia_id')})",
    ),
    "usuarios.novo": (
        "usuario_criado",
        lambda r: f"{request.form.get('email', '')[:150]} ({request.form.get('perfil', '')})",
    ),
    "usuarios.editar": (
        "usuario_editado",
        lambda r: f"{request.form.get('email', '')[:150]} ({request.form.get('perfil', '')})",
    ),
    "usuarios.redefinir_senha": (
        "senha_redefinida",
        lambda r: _alvo(),
    ),
    "usuarios.alternar": (
        "usuario_acesso_alterado",
        lambda r: _alvo(),
    ),
}

# Consultas feitas ANTES da ação, para guardar o nome do que será excluído ou alterado.
ALVOS = {
    "atividades.excluir": ("SELECT nome FROM atividades WHERE id = %s", "atividade_id"),
    "midias.excluir": ("SELECT nome_original FROM midias WHERE id = %s", "midia_id"),
    "usuarios.redefinir_senha": ("SELECT email FROM usuarios WHERE id = %s", "usuario_id"),
    "usuarios.alternar": (
        "SELECT CONCAT(email, IF(ativo = 1, ' (desativado)', ' (reativado)')) "
        "FROM usuarios WHERE id = %s",
        "usuario_id",
    ),
}


def registrar(acao, detalhe=None):
    """Grava uma linha em registros. O banco só recebe valores parametrizados."""
    usuario_id = session.get("usuario_id")
    usuario_nome = session.get("usuario_nome")
    if usuario_id is None:
        usuario_id, usuario_nome = g.get("auditoria_usuario", (None, None))

    texto = detalhe[:500] if detalhe else None

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO registros (usuario_id, usuario_nome, acao, detalhe, ip) "
            "VALUES (%s, %s, %s, %s, %s)",
            (usuario_id, usuario_nome, acao, texto, request.remote_addr),
        )
    db.commit()


def _antes():
    if request.method != "POST" or request.endpoint is None:
        return

    # Guarda quem era o usuário antes da ação (o logout apaga a sessão).
    g.auditoria_usuario = (session.get("usuario_id"), session.get("usuario_nome"))
    g.auditoria_flashes = len(session.get("_flashes", []))

    consulta = ALVOS.get(request.endpoint)
    if consulta and session.get("usuario_id") and request.view_args:
        sql, chave = consulta
        try:
            db = get_db()
            with db.cursor() as cursor:
                cursor.execute(sql, (request.view_args.get(chave),))
                linha = cursor.fetchone()
            db.commit()
            if linha:
                g.auditoria_alvo = str(next(iter(linha.values())))
        except Exception:
            current_app.logger.exception("Falha ao preparar o registro de auditoria")


def _depois(resposta):
    try:
        if request.method != "POST" or request.endpoint is None:
            return resposta

        endpoint = request.endpoint

        if endpoint == "auth.login":
            ja_logado = g.get("auditoria_usuario", (None, None))[0] is not None
            if resposta.status_code == 302 and not ja_logado:
                registrar("login")
            elif resposta.status_code in (400, 401, 403):
                registrar("login_falha", request.form.get("email", "")[:150])
            return resposta

        regra = ACOES.get(endpoint)
        if not regra or resposta.status_code not in (200, 302):
            return resposta

        # Só registra se a rota terminou com a mensagem de sucesso.
        mensagens = session.get("_flashes", [])
        if len(mensagens) <= g.get("auditoria_flashes", 0) or mensagens[-1][0] != "sucesso":
            return resposta

        acao, montar_detalhe = regra
        registrar(acao, montar_detalhe(resposta))
    except Exception:
        current_app.logger.exception("Falha ao gravar o registro de auditoria")
    return resposta


def init_app(app):
    app.before_request(_antes)
    app.after_request(_depois)