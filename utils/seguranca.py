import re

SENHAS_FRACAS = {
    "1234567890", "12345678910", "abcdefghij", "senha12345", "senha123456",
    "password123", "qwertyuiop", "1q2w3e4r5t", "a1b2c3d4e5", "123456789a",
    "admin12345", "apae123456", "mudar12345", "trocar12345",
}


def avaliar_senha(senha):
    """Devolve a lista de problemas da senha (vazia se estiver boa)."""
    erros = []

    if len(senha) < 10:
        erros.append("A senha precisa ter pelo menos 10 caracteres.")
    elif len(senha) > 128:
        erros.append("A senha pode ter no máximo 128 caracteres.")
    else:
        if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
            erros.append("Use letras e números na senha.")
        if len(set(senha)) < 5:
            erros.append("A senha tem caracteres repetidos demais.")
        if senha.lower() in SENHAS_FRACAS:
            erros.append("Essa senha é muito comum. Escolha outra.")

    return erros