from config import Config


def test_limites_de_upload_configurados():
    assert Config.LIMITE_FOTO_MB == 15
    assert Config.LIMITE_VIDEO_MB == 300
    assert Config.MAX_CONTENT_LENGTH == 512 * 1024 * 1024


def test_extensoes_permitidas():
    assert Config.EXTENSOES_FOTO == {"jpg", "jpeg", "png", "webp"}
    assert Config.EXTENSOES_VIDEO == {"mp4", "mov", "webm"}
    assert "exe" not in Config.EXTENSOES_FOTO | Config.EXTENSOES_VIDEO


def test_cookie_de_sessao_protegido():
    assert Config.SESSION_COOKIE_HTTPONLY is True
    assert Config.SESSION_COOKIE_SAMESITE == "Lax"