from flask import Blueprint, render_template, request

from extensions import get_db
from utils.auditoria import ROTULOS
from utils.decorators import perfil_required

registros_bp = Blueprint("registros", __name__, url_prefix="/registros")

POR_PAGINA = 50


@registros_bp.route("/")
@perfil_required("administrador")
def listar():
    acao = request.args.get("acao", "").strip()
    if acao not in ROTULOS:
        acao = ""

    pagina = request.args.get("pagina", "1")
    pagina = int(pagina) if pagina.isdigit() and int(pagina) > 0 else 1

    onde = "WHERE acao = %s" if acao else ""
    parametros = [acao] if acao else []

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) AS total FROM registros {onde}", parametros)
        total = cursor.fetchone()["total"]

        total_paginas = max(1, -(-total // POR_PAGINA))
        pagina = min(pagina, total_paginas)

        cursor.execute(
            "SELECT usuario_nome, acao, detalhe, ip, criado_em "
            f"FROM registros {onde} "
            "ORDER BY criado_em DESC, id DESC LIMIT %s OFFSET %s",
            parametros + [POR_PAGINA, (pagina - 1) * POR_PAGINA],
        )
        registros = cursor.fetchall()

    return render_template(
        "registros.html",
        registros=registros,
        rotulos=ROTULOS,
        acao=acao,
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
    )