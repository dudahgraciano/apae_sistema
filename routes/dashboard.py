from flask import Blueprint, render_template

from extensions import get_db
from utils.decorators import login_required

dashboard_bp = Blueprint("dashboard", __name__)

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


@dashboard_bp.route("/dashboard")
@login_required
def painel():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM atividades")
        total_atividades = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT "
            "COALESCE(SUM(tipo = 'foto'), 0) AS fotos, "
            "COALESCE(SUM(tipo = 'video'), 0) AS videos "
            "FROM midias"
        )
        contagem = cursor.fetchone()

        cursor.execute(
            "SELECT a.id, a.nome, a.data_realizacao, a.criado_em, "
            "       t.nome AS turma, c.nome AS categoria, "
            "       (SELECT COUNT(*) FROM midias m WHERE m.atividade_id = a.id) AS total_midias "
            "FROM atividades a "
            "JOIN turmas t ON t.id = a.turma_id "
            "JOIN categorias c ON c.id = a.categoria_id "
            "ORDER BY a.criado_em DESC, a.id DESC "
            "LIMIT 6"
        )
        recentes = cursor.fetchall()

    return render_template(
        "dashboard.html",
        total_atividades=total_atividades,
        total_fotos=int(contagem["fotos"]),
        total_videos=int(contagem["videos"]),
        recentes=recentes,
    )