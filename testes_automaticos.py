import io
import re
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

import pymysql
from PIL import Image
from werkzeug.security import generate_password_hash

from app import app
from config import Config
from extensions import limiter
from utils.uploads import apagar_arquivos

SENHA = "TesteApae2026x"

USUARIOS = {
    "admin": ("Teste Administrador", "teste_admin@apae.teste", "administrador"),
    "colab": ("Teste Colaborador", "teste_colab@apae.teste", "colaborador"),
    "colab2": ("Teste Colaborador Dois", "teste_colab2@apae.teste", "colaborador"),
    "visu": ("Teste Visualizador", "teste_visu@apae.teste", "visualizador"),
}

CAMINHOS_PROTEGIDOS = [
    "/dashboard",
    "/galeria",
    "/atividades/",
    "/atividades/nova",
    "/usuarios/",
    "/registros/",
    "/midias/1/arquivo",
    "/midias/1/miniatura",
    "/midias/1/baixar",
]

PADRAO_TOKEN = re.compile(
    r'(?:name="csrf_token" value|name="csrf-token" content)="([^"]+)"'
)
PADRAO_NOME_ARQUIVO = re.compile(r"^[0-9a-f]{32}\.(png|jpg|jpeg|webp|mp4|mov|webm)$")

resultados = []


# ---------------------------------------------------------------------
# Apoio
# ---------------------------------------------------------------------

def verificar(descricao, condicao, detalhe=""):
    resultados.append(bool(condicao))
    if condicao:
        print(f"[OK]     {descricao}")
    else:
        extra = f"  (obtido: {detalhe})" if detalhe != "" else ""
        print(f"[FALHA]  {descricao}{extra}")


def secao(titulo):
    print(f"\n=== {titulo} ===")


def conectar():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def sql(consulta, parametros=()):
    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()
    finally:
        conexao.close()


def limpar():
    """Remove tudo o que os testes criaram (só mexe em e-mails @apae.teste)."""
    ids = [l["id"] for l in sql("SELECT id FROM usuarios WHERE email LIKE %s", ("%@apae.teste",))]
    if ids:
        m = ",".join(["%s"] * len(ids))
        arquivos = [
            l["nome_arquivo"]
            for l in sql(
                "SELECT m.nome_arquivo FROM midias m "
                "JOIN atividades a ON a.id = m.atividade_id "
                f"WHERE a.usuario_id IN ({m}) OR m.enviado_por IN ({m})",
                ids + ids,
            )
        ]
        apagar_arquivos(app.config, arquivos)
        sql(f"DELETE FROM midias WHERE enviado_por IN ({m})", ids)
        sql(f"DELETE FROM atividades WHERE usuario_id IN ({m})", ids)
        sql(f"DELETE FROM registros WHERE usuario_id IN ({m})", ids)
    sql(
        "DELETE FROM registros WHERE detalhe LIKE %s OR usuario_nome LIKE %s",
        ("%@apae.teste%", "Teste %"),
    )
    sql("DELETE FROM usuarios WHERE email LIKE %s", ("%@apae.teste",))


def criar_usuarios():
    senha_hash = generate_password_hash(SENHA)
    ids = {}
    for chave, (nome, email, perfil) in USUARIOS.items():
        sql(
            "INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES (%s, %s, %s, %s)",
            (nome, email, senha_hash, perfil),
        )
        ids[chave] = sql("SELECT id FROM usuarios WHERE email = %s", (email,))[0]["id"]
    return ids


def token(cliente, url="/dashboard"):
    resposta = cliente.get(url)
    achado = PADRAO_TOKEN.search(resposta.get_data(as_text=True))
    return achado.group(1) if achado else ""


def entrar(chave):
    cliente = app.test_client()
    t = token(cliente, "/login")
    resposta = cliente.post(
        "/login",
        data={"email": USUARIOS[chave][1], "senha": SENHA, "csrf_token": t},
    )
    if resposta.status_code != 302:
        raise RuntimeError(f"Não foi possível entrar como {chave} (status {resposta.status_code}).")
    return cliente


def imagem_png():
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), (30, 120, 90)).save(buffer, "PNG")
    return buffer.getvalue()


def enviar(cliente, atividade_id, arquivos, autorizar=True):
    dados = {
        "csrf_token": token(cliente),
        "arquivos": [(io.BytesIO(conteudo), nome) for nome, conteudo in arquivos],
    }
    if autorizar:
        dados["autorizacao"] = "1"
    return cliente.post(
        f"/atividades/{atividade_id}/midias",
        data=dados,
        content_type="multipart/form-data",
    )


def caminho_no_disco(linha):
    pasta = "fotos" if linha["tipo"] == "foto" else "videos"
    return Path(app.config["UPLOAD_FOLDER"]) / pasta / linha["nome_arquivo"]


# ---------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------

def executar(ids):
    turma_id = sql("SELECT id FROM turmas WHERE ativa = 1 ORDER BY id LIMIT 1")[0]["id"]
    categoria_id = sql("SELECT id FROM categorias WHERE ativa = 1 ORDER BY id LIMIT 1")[0]["id"]

    def dados_atividade(nome, data=None):
        return {
            "nome": nome,
            "descricao": "Criada pelo teste automático.",
            "data_realizacao": (data or date.today()).isoformat(),
            "turma_id": str(turma_id),
            "categoria_id": str(categoria_id),
        }

    # ------------------------------------------------------------------
    secao("1. Acesso sem login")
    anonimo = app.test_client()
    for caminho in CAMINHOS_PROTEGIDOS:
        r = anonimo.get(caminho)
        verificar(
            f"{caminho} sem login leva ao login",
            r.status_code == 302 and "/login" in r.headers.get("Location", ""),
            r.status_code,
        )

    # ------------------------------------------------------------------
    secao("2. Login e ataques ao login")
    c = app.test_client()
    t = token(c, "/login")
    email = USUARIOS["colab"][1]

    r = c.post("/login", data={"email": email, "senha": "senhaerrada", "csrf_token": t})
    verificar("Senha errada é recusada (401)", r.status_code == 401, r.status_code)
    verificar(
        "A mensagem de erro é genérica",
        "E-mail ou senha incorretos" in r.get_data(as_text=True),
    )

    r = c.post("/login", data={"email": "nao_existe@apae.teste", "senha": "qualquer", "csrf_token": t})
    verificar("E-mail inexistente recebe a mesma resposta (401)", r.status_code == 401, r.status_code)

    r = c.post("/login", data={"email": email, "senha": SENHA})
    verificar("Login sem token CSRF é bloqueado (400)", r.status_code == 400, r.status_code)

    for email_ataque, senha_ataque in [("' OR '1'='1", "' OR '1'='1"), (email + "' --", "x")]:
        r = c.post("/login", data={"email": email_ataque, "senha": senha_ataque, "csrf_token": t})
        verificar(f"SQL Injection no login é recusada ({email_ataque[:18]}...)", r.status_code == 401, r.status_code)

    c2 = app.test_client()
    t2 = token(c2, "/login")
    r = c2.post(
        "/login?next=https://evil.example.com",
        data={"email": email, "senha": SENHA, "csrf_token": t2},
    )
    verificar(
        "Redirecionamento para site externo é ignorado",
        r.status_code == 302 and "evil.example.com" not in r.headers.get("Location", ""),
        r.headers.get("Location", ""),
    )

    # ------------------------------------------------------------------
    secao("3. Permissões por perfil")
    admin = entrar("admin")
    colab = entrar("colab")
    colab2 = entrar("colab2")
    visu = entrar("visu")

    matriz = [
        ("administrador", admin, [("/usuarios/", 200), ("/registros/", 200), ("/atividades/nova", 200), ("/galeria", 200)]),
        ("colaborador", colab, [("/usuarios/", 403), ("/registros/", 403), ("/atividades/nova", 200), ("/galeria", 200)]),
        ("visualizador", visu, [("/usuarios/", 403), ("/registros/", 403), ("/atividades/nova", 403), ("/atividades/", 200), ("/galeria", 200)]),
    ]
    for perfil, cliente, regras in matriz:
        for caminho, esperado in regras:
            r = cliente.get(caminho)
            verificar(f"{perfil} em {caminho} -> {esperado}", r.status_code == esperado, r.status_code)

    # ------------------------------------------------------------------
    secao("4. Atividades: cadastro, validação, edição e dono")
    t = token(colab)

    r = colab.post("/atividades/nova", data={**dados_atividade("ab"), "csrf_token": t})
    verificar("Nome curto demais é recusado (400)", r.status_code == 400, r.status_code)

    futuro = date.today() + timedelta(days=5)
    r = colab.post("/atividades/nova", data={**dados_atividade("Teste data futura", futuro), "csrf_token": t})
    verificar("Data no futuro é recusada (400)", r.status_code == 400, r.status_code)

    dados = dados_atividade("Teste atividade principal")
    dados["turma_id"] = "999999"
    r = colab.post("/atividades/nova", data={**dados, "csrf_token": t})
    verificar("Turma inventada (id inexistente) é recusada (400)", r.status_code == 400, r.status_code)

    r = colab.post("/atividades/nova", data={**dados_atividade("Teste atividade principal"), "csrf_token": t})
    verificar("Colaborador cadastra atividade (302)", r.status_code == 302, r.status_code)
    linha = sql(
        "SELECT id FROM atividades WHERE nome = %s AND usuario_id = %s",
        ("Teste atividade principal", ids["colab"]),
    )
    verificar("A atividade foi gravada no banco", len(linha) == 1)
    aid = linha[0]["id"]

    r = visu.get(f"/atividades/{aid}")
    verificar("Visualizador consegue ver os detalhes (200)", r.status_code == 200, r.status_code)
    r = colab.get("/atividades/999999")
    verificar("Atividade inexistente dá 404", r.status_code == 404, r.status_code)

    r = colab2.get(f"/atividades/{aid}/editar")
    verificar("Outro colaborador não abre a edição (403)", r.status_code == 403, r.status_code)
    r = colab2.post(f"/atividades/{aid}/excluir", data={"csrf_token": token(colab2)})
    verificar("Outro colaborador não exclui (403)", r.status_code == 403, r.status_code)
    r = visu.post(
        f"/atividades/{aid}/editar",
        data={**dados_atividade("Teste invasao"), "csrf_token": token(visu)},
    )
    verificar("Visualizador não edita (403)", r.status_code == 403, r.status_code)

    r = admin.post(
        f"/atividades/{aid}/editar",
        data={**dados_atividade("Teste atividade editada"), "csrf_token": token(admin)},
    )
    verificar("Administrador edita atividade de outra pessoa (302)", r.status_code == 302, r.status_code)
    nome_atual = sql("SELECT nome FROM atividades WHERE id = %s", (aid,))[0]["nome"]
    verificar("A edição foi gravada", nome_atual == "Teste atividade editada", nome_atual)

    r = colab.post(f"/atividades/{aid}/excluir")
    verificar("Exclusão sem token CSRF é bloqueada (400)", r.status_code == 400, r.status_code)
    r = colab.get(f"/atividades/{aid}/excluir")
    verificar("Exclusão por link (GET) não é permitida (405)", r.status_code == 405, r.status_code)

    # ------------------------------------------------------------------
    secao("5. Ataques por texto (SQL Injection e XSS)")
    ataques = [
        ("/galeria", {"busca": "' OR '1'='1"}),
        ("/galeria", {"busca": "%", "turma": "1 OR 1=1", "pagina": "abc"}),
        ("/atividades/", {"busca": "x'; DROP TABLE usuarios; --"}),
        ("/atividades/", {"turma": "1; DELETE FROM atividades", "de": "2026-99-99"}),
    ]
    for caminho, parametros in ataques:
        r = admin.get(caminho, query_string=parametros)
        verificar(f"Consulta maliciosa em {caminho} não quebra o sistema", r.status_code == 200, r.status_code)
    total_usuarios = sql("SELECT COUNT(*) AS n FROM usuarios")[0]["n"]
    verificar("A tabela de usuários continua intacta", total_usuarios >= len(USUARIOS), total_usuarios)

    nome_xss = "<script>alert(1)</script> Teste"
    r = colab.post("/atividades/nova", data={**dados_atividade(nome_xss), "csrf_token": token(colab)})
    achado = sql("SELECT id FROM atividades WHERE usuario_id = %s AND nome LIKE %s", (ids["colab"], "<script>%"))
    verificar("Atividade com <script> no nome é gravada como texto", len(achado) == 1)
    if achado:
        html = colab.get(f"/atividades/{achado[0]['id']}").get_data(as_text=True)
        verificar("O <script> aparece escapado na página (XSS barrado)", "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html)
        html = colab.get("/atividades/").get_data(as_text=True)
        verificar("O <script> também é escapado na lista", "<script>alert(1)</script>" not in html)

    # ------------------------------------------------------------------
    secao("6. Upload de arquivos")
    foto_valida = imagem_png()

    r = enviar(colab, aid, [("a.png", foto_valida)], autorizar=False)
    verificar("Envio sem a autorização de uso de imagem é recusado (400)", r.status_code == 400, r.status_code)

    r = enviar(colab, aid, [("foto.jpg", b"MZ isto e um programa, nao uma imagem")])
    json = r.get_json() or {}
    verificar("Arquivo falso renomeado para .jpg é recusado", r.status_code == 400 and len(json.get("falhas", [])) == 1, r.status_code)

    r = enviar(colab, aid, [("script.php.jpg", b"<?php echo 'oi'; ?>")])
    verificar("Script disfarçado de imagem é recusado", r.status_code == 400, r.status_code)

    r = enviar(colab, aid, [("virus.exe", b"MZ" + b"\x00" * 50)])
    verificar("Formato .exe não é aceito", r.status_code == 400, r.status_code)

    r = enviar(colab, aid, [("clipe_falso.mp4", b"isto nao e um video de verdade")])
    verificar("Vídeo falso é recusado", r.status_code == 400, r.status_code)

    r = enviar(colab, aid, [("vazio.png", b"")])
    verificar("Arquivo vazio é recusado", r.status_code == 400, r.status_code)

    r = enviar(colab, aid, [("foto1.png", foto_valida)])
    json = r.get_json() or {}
    verificar("Foto válida é aceita (200)", r.status_code == 200 and json.get("enviados") == ["foto1.png"], r.status_code)

    r = enviar(colab, aid, [("../../app.py.png", foto_valida)])
    verificar("Nome com ../ é aceito, mas neutralizado (200)", r.status_code == 200, r.status_code)

    r = enviar(colab, aid, [("foto2.png", foto_valida), ("falsa.jpg", b"nao sou imagem")])
    json = r.get_json() or {}
    verificar(
        "Envio misto: a foto boa entra e a falsa é recusada",
        r.status_code == 200 and len(json.get("enviados", [])) == 1 and len(json.get("falhas", [])) == 1,
        json,
    )

    video_ok = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200
    r = enviar(colab, aid, [("clipe.mp4", video_ok)])
    verificar("Vídeo com assinatura MP4 válida é aceito (200)", r.status_code == 200, r.status_code)

    r = enviar(visu, aid, [("v.png", foto_valida)])
    verificar("Visualizador não envia arquivos (403)", r.status_code == 403, r.status_code)
    r = enviar(colab2, aid, [("v.png", foto_valida)])
    verificar("Outro colaborador não envia à atividade alheia (403)", r.status_code == 403, r.status_code)

    linhas = sql(
        "SELECT id, nome_original, nome_arquivo, tipo FROM midias WHERE atividade_id = %s ORDER BY id",
        (aid,),
    )
    verificar("Exatamente 4 arquivos válidos foram gravados", len(linhas) == 4, len(linhas))
    verificar(
        "Todos os arquivos têm nome aleatório no disco",
        all(PADRAO_NOME_ARQUIVO.match(l["nome_arquivo"]) for l in linhas),
    )
    verificar("Todos os arquivos existem na pasta uploads", all(caminho_no_disco(l).exists() for l in linhas))
    verificar(
        "O nome original com ../ foi limpo (app.py.png)",
        any(l["nome_original"] == "app.py.png" for l in linhas),
        [l["nome_original"] for l in linhas],
    )
    verificar("O app.py não foi sobrescrito", Path("app.py").exists() and Path("app.py").stat().st_size > 1000)

    # ------------------------------------------------------------------
    secao("7. Entrega protegida dos arquivos")
    foto = next(l for l in linhas if l["tipo"] == "foto")
    video = next(l for l in linhas if l["tipo"] == "video")

    r = visu.get(f"/midias/{foto['id']}/arquivo")
    verificar("Usuário logado vê a foto (200, image/png)", r.status_code == 200 and r.mimetype == "image/png", r.status_code)
    r = visu.get(f"/midias/{foto['id']}/miniatura")
    verificar("Miniatura é entregue (200, image/jpeg)", r.status_code == 200 and r.mimetype == "image/jpeg", r.status_code)
    r = visu.get(f"/midias/{foto['id']}/baixar")
    verificar("Download sai como anexo", "attachment" in r.headers.get("Content-Disposition", ""))
    r = visu.get(f"/midias/{video['id']}/arquivo", headers={"Range": "bytes=0-9"})
    verificar("Vídeo aceita avançar e voltar (206)", r.status_code == 206, r.status_code)

    for rota in ("arquivo", "miniatura", "baixar"):
        r = anonimo.get(f"/midias/{foto['id']}/{rota}")
        verificar(f"Sem login, /{rota} da foto é barrado", r.status_code == 302, r.status_code)

    for caminho in ("/uploads/fotos/" + foto["nome_arquivo"], "/static/../uploads/fotos/" + foto["nome_arquivo"]):
        r = anonimo.get(caminho)
        verificar(f"A pasta uploads não é pública ({caminho[:28]}...)", r.status_code in (302, 404), r.status_code)

    # ------------------------------------------------------------------
    secao("8. Exclusão e limpeza do disco")
    r = colab2.post(f"/midias/{foto['id']}/excluir", data={"csrf_token": token(colab2)})
    verificar("Outro colaborador não exclui o arquivo (403)", r.status_code == 403, r.status_code)
    r = visu.post(f"/midias/{foto['id']}/excluir", data={"csrf_token": token(visu)})
    verificar("Visualizador não exclui o arquivo (403)", r.status_code == 403, r.status_code)

    r = colab.post(f"/midias/{foto['id']}/excluir", data={"csrf_token": token(colab)})
    verificar("O dono exclui o arquivo (302)", r.status_code == 302, r.status_code)
    verificar("O arquivo saiu do disco", not caminho_no_disco(foto).exists())

    restantes = [l for l in linhas if l["id"] != foto["id"]]
    r = colab.post(f"/atividades/{aid}/excluir", data={"csrf_token": token(colab)})
    verificar("O dono exclui a atividade (302)", r.status_code == 302, r.status_code)
    verificar("Todos os arquivos da atividade saíram do disco", not any(caminho_no_disco(l).exists() for l in restantes))
    sobra = sql("SELECT COUNT(*) AS n FROM midias WHERE atividade_id = %s", (aid,))[0]["n"]
    verificar("As mídias saíram do banco em cascata", sobra == 0, sobra)

    # ------------------------------------------------------------------
    secao("9. Registro de ações (auditoria)")
    def contar(acao, usuario):
        return sql(
            "SELECT COUNT(*) AS n FROM registros WHERE acao = %s AND usuario_id = %s",
            (acao, usuario),
        )[0]["n"]

    verificar("Login ficou registrado", contar("login", ids["colab"]) >= 1)
    verificar("Cadastro de atividade ficou registrado", contar("atividade_criada", ids["colab"]) >= 1)
    verificar("Edição feita pelo administrador ficou registrada", contar("atividade_editada", ids["admin"]) >= 1)
    verificar("Envio de arquivos ficou registrado", contar("midias_enviadas", ids["colab"]) >= 1)
    verificar("Exclusão de arquivo ficou registrada", contar("midia_excluida", ids["colab"]) >= 1)
    verificar("Exclusão de atividade ficou registrada", contar("atividade_excluida", ids["colab"]) >= 1)
    detalhe = sql(
        "SELECT detalhe FROM registros WHERE acao = 'midias_enviadas' AND usuario_id = %s ORDER BY id DESC LIMIT 1",
        (ids["colab"],),
    )
    verificar(
        "O registro do envio confirma a autorização de imagem",
        bool(detalhe) and "autorização" in (detalhe[0]["detalhe"] or ""),
    )
    falhas = sql("SELECT COUNT(*) AS n FROM registros WHERE acao = 'login_falha' AND detalhe LIKE %s", ("%@apae.teste%",))[0]["n"]
    verificar("Tentativas de login recusadas ficaram registradas", falhas >= 1, falhas)

    # ------------------------------------------------------------------
    secao("10. Gerenciamento de usuários")
    t = token(admin)
    novo = {
        "nome": "Teste Novo Usuario",
        "email": "teste_novo@apae.teste",
        "perfil": "colaborador",
        "csrf_token": t,
    }

    r = admin.post("/usuarios/novo", data={**novo, "senha": "abc12345", "confirmacao": "abc12345"})
    verificar("Senha fraca (8 caracteres) é recusada (400)", r.status_code == 400, r.status_code)
    r = admin.post("/usuarios/novo", data={**novo, "senha": "PinhalApae2026", "confirmacao": "Outra12345"})
    verificar("Senhas diferentes são recusadas (400)", r.status_code == 400, r.status_code)
    r = admin.post("/usuarios/novo", data={**novo, "senha": "PinhalApae2026", "confirmacao": "PinhalApae2026"})
    verificar("Senha forte cadastra o usuário (302)", r.status_code == 302, r.status_code)
    r = admin.post("/usuarios/novo", data={**novo, "senha": "PinhalApae2026", "confirmacao": "PinhalApae2026"})
    verificar("E-mail repetido é recusado (400)", r.status_code == 400, r.status_code)

    senha_guardada = sql("SELECT senha_hash FROM usuarios WHERE email = %s", (novo["email"],))[0]["senha_hash"]
    verificar("A senha fica guardada só como hash", senha_guardada.startswith(("scrypt:", "pbkdf2:")) and "PinhalApae2026" not in senha_guardada)

    r = admin.post(f"/usuarios/{ids['admin']}/alternar", data={"csrf_token": token(admin)})
    ativo = sql("SELECT ativo FROM usuarios WHERE id = %s", (ids["admin"],))[0]["ativo"]
    verificar("O administrador não consegue desativar a si mesmo", ativo == 1)

    r = admin.post(
        f"/usuarios/{ids['admin']}/editar",
        data={"nome": USUARIOS["admin"][0], "email": USUARIOS["admin"][1], "perfil": "visualizador", "csrf_token": token(admin)},
    )
    perfil = sql("SELECT perfil FROM usuarios WHERE id = %s", (ids["admin"],))[0]["perfil"]
    verificar("O administrador não consegue rebaixar o próprio perfil", perfil == "administrador", perfil)

    r = colab.post(
        f"/usuarios/{ids['colab']}/editar",
        data={"nome": "Teste Colaborador", "email": USUARIOS["colab"][1], "perfil": "administrador", "csrf_token": token(colab)},
    )
    verificar("Colaborador não se promove a administrador (403)", r.status_code == 403, r.status_code)

    r = admin.post(f"/usuarios/{ids['colab2']}/alternar", data={"csrf_token": token(admin)})
    verificar("Administrador desativa um usuário (302)", r.status_code == 302, r.status_code)
    r = colab2.get("/dashboard")
    verificar(
        "O usuário desativado é barrado na hora, mesmo logado",
        r.status_code == 302 and "/login" in r.headers.get("Location", ""),
        r.status_code,
    )

    # ------------------------------------------------------------------
    secao("11. Cabeçalhos de segurança")
    r = app.test_client().get("/login")
    verificar("X-Content-Type-Options: nosniff", r.headers.get("X-Content-Type-Options") == "nosniff")
    verificar("X-Frame-Options: DENY", r.headers.get("X-Frame-Options") == "DENY")
    verificar("Referrer-Policy definido", bool(r.headers.get("Referrer-Policy")))
    verificar("Content-Security-Policy definido", "default-src 'self'" in r.headers.get("Content-Security-Policy", ""))
    verificar("Páginas HTML não ficam em cache (no-store)", "no-store" in r.headers.get("Cache-Control", ""))
    verificar("Cookie de sessão é HttpOnly e SameSite", "HttpOnly" in (app.test_client().get("/login").headers.get("Set-Cookie", "HttpOnly") ) and app.config["SESSION_COOKIE_SAMESITE"] == "Lax")

    # ------------------------------------------------------------------
    secao("12. Limite de tentativas de login (força bruta)")
    limiter.enabled = True
    try:
        limiter.reset()
    except Exception:
        pass
    c = app.test_client()
    t = token(c, "/login")
    codigos = [
        c.post("/login", data={"email": "teste_limite@apae.teste", "senha": "errada", "csrf_token": t}).status_code
        for _ in range(7)
    ]
    verificar("Depois de 5 tentativas erradas o sistema bloqueia (429)", 429 in codigos, codigos)
    limiter.enabled = False


def main():
    print("Preparando dados de teste...")
    limpar()
    ids = criar_usuarios()
    limiter.enabled = False  # os testes de login em série não podem ser barrados antes da hora

    try:
        executar(ids)
    except Exception:
        print("\n[ERRO] O script parou por um problema inesperado:\n")
        traceback.print_exc()
        resultados.append(False)
    finally:
        print("\nLimpando dados de teste...")
        limpar()

    total = len(resultados)
    passaram = sum(resultados)
    print(f"\n{passaram} de {total} verificações passaram.")
    if passaram == total:
        print("Tudo certo: o sistema está se comportando como esperado.")
    else:
        print("Há falhas. Copie as linhas [FALHA] e envie para análise.")
        sys.exit(1)


main()