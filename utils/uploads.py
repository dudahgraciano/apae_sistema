import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

TAMANHO_MINIATURA = (480, 480)

MIME_POR_EXTENSAO = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
}

FORMATO_PILLOW = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
}


class ErroUpload(Exception):
    """Erro de validação com mensagem pronta para o usuário."""


def extensao_do_arquivo(nome):
    if "." not in nome:
        return ""
    return nome.rsplit(".", 1)[1].lower()


def limpar_nome_original(nome):
    """Mantém só o nome do arquivo, sem pastas, e limita o tamanho."""
    nome = nome.replace("\\", "/").split("/")[-1]
    nome = "".join(c for c in nome if c.isprintable()).strip()
    return nome[:200] or "arquivo"


def pasta_do_tipo(config, tipo):
    return Path(config["UPLOAD_FOLDER"]) / ("fotos" if tipo == "foto" else "videos")


def pasta_miniaturas(config):
    pasta = Path(config["UPLOAD_FOLDER"]) / "miniaturas"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def tipo_pela_extensao(config, extensao):
    if extensao in config["EXTENSOES_FOTO"]:
        return "foto"
    if extensao in config["EXTENSOES_VIDEO"]:
        return "video"
    return None


def assinatura_de_video_valida(inicio, extensao):
    """Confere os primeiros bytes do arquivo de vídeo."""
    if extensao in ("mp4", "mov"):
        # Arquivos MP4/MOV trazem a palavra 'ftyp' nos bytes 4 a 8.
        return inicio[4:8] == b"ftyp"
    if extensao == "webm":
        # WebM (Matroska) começa com 1A 45 DF A3.
        return inicio[:4] == b"\x1a\x45\xdf\xa3"
    return False


def salvar_foto(arquivo, config):
    extensao = extensao_do_arquivo(arquivo.filename)
    formato = FORMATO_PILLOW[extensao]
    nome_arquivo = f"{uuid.uuid4().hex}.{extensao}"
    pasta = pasta_do_tipo(config, "foto")
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / nome_arquivo

    try:
        arquivo.stream.seek(0)
        imagem = Image.open(arquivo.stream)
        imagem.load()  # força a leitura completa: falha se o arquivo estiver corrompido
        imagem = ImageOps.exif_transpose(imagem)  # corrige a rotação de fotos de celular

        if formato == "JPEG" and imagem.mode not in ("RGB", "L"):
            imagem = imagem.convert("RGB")

        # Regravar a imagem descarta metadados (EXIF, GPS) e qualquer conteúdo escondido.
        if formato == "JPEG":
            imagem.save(destino, formato, quality=90, optimize=True)
        else:
            imagem.save(destino, formato)

        miniatura = imagem.copy()
        miniatura.thumbnail(TAMANHO_MINIATURA)
        if miniatura.mode not in ("RGB", "L"):
            miniatura = miniatura.convert("RGB")
        miniatura.save(pasta_miniaturas(config) / f"{nome_arquivo.rsplit('.', 1)[0]}.jpg",
                       "JPEG", quality=80, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        if destino.exists():
            destino.unlink()
        raise ErroUpload("não é uma imagem válida ou o arquivo está danificado.")

    return {
        "nome_arquivo": nome_arquivo,
        "tipo": "foto",
        "mime_type": MIME_POR_EXTENSAO[extensao],
        "tamanho_bytes": destino.stat().st_size,
    }


def salvar_video(arquivo, config):
    extensao = extensao_do_arquivo(arquivo.filename)
    arquivo.stream.seek(0)
    inicio = arquivo.stream.read(16)
    if not assinatura_de_video_valida(inicio, extensao):
        raise ErroUpload("o conteúdo não corresponde a um vídeo válido.")

    nome_arquivo = f"{uuid.uuid4().hex}.{extensao}"
    pasta = pasta_do_tipo(config, "video")
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / nome_arquivo

    arquivo.stream.seek(0)
    arquivo.save(destino)

    return {
        "nome_arquivo": nome_arquivo,
        "tipo": "video",
        "mime_type": MIME_POR_EXTENSAO[extensao],
        "tamanho_bytes": destino.stat().st_size,
    }


def tamanho_do_arquivo(arquivo):
    arquivo.stream.seek(0, 2)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(0)
    return tamanho


def processar_arquivo(arquivo, config):
    """Valida e grava um arquivo enviado. Devolve os dados para o banco.

    Levanta ErroUpload com mensagem em português se algo estiver errado.
    """
    nome = limpar_nome_original(arquivo.filename or "")
    extensao = extensao_do_arquivo(nome)
    tipo = tipo_pela_extensao(config, extensao)

    if tipo is None:
        permitidos = sorted(config["EXTENSOES_FOTO"] | config["EXTENSOES_VIDEO"])
        raise ErroUpload(
            "formato não aceito. Use: " + ", ".join(e.upper() for e in permitidos) + "."
        )

    tamanho = tamanho_do_arquivo(arquivo)
    if tamanho == 0:
        raise ErroUpload("o arquivo está vazio.")

    limite_mb = config["LIMITE_FOTO_MB"] if tipo == "foto" else config["LIMITE_VIDEO_MB"]
    if tamanho > limite_mb * 1024 * 1024:
        raise ErroUpload(
            f"o arquivo é grande demais (limite de {limite_mb} MB para "
            f"{'fotografias' if tipo == 'foto' else 'vídeos'})."
        )

    arquivo.filename = nome
    dados = salvar_foto(arquivo, config) if tipo == "foto" else salvar_video(arquivo, config)
    dados["nome_original"] = nome
    return dados


def apagar_arquivos(config, nomes_arquivos):
    """Remove do disco os arquivos (e miniaturas) com os nomes informados."""
    for nome in nomes_arquivos:
        base = nome.rsplit(".", 1)[0]
        extensao = extensao_do_arquivo(nome)
        tipo = "foto" if extensao in config["EXTENSOES_FOTO"] else "video"
        for caminho in (
            pasta_do_tipo(config, tipo) / nome,
            Path(config["UPLOAD_FOLDER"]) / "miniaturas" / f"{base}.jpg",
        ):
            try:
                caminho.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass