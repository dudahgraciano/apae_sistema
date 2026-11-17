import os
import re
import sys
from getpass import getpass

import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def conectar():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
        connect_timeout=5,
    )


def main():
    print("=== Cadastro do primeiro administrador ===\n")

    nome = input("Nome completo: ").strip()
    if len(nome) < 3:
        print("Nome muito curto.")
        sys.exit(1)

    email = input("E-mail: ").strip().lower()
    if not PADRAO_EMAIL.match(email):
        print("E-mail inválido.")
        sys.exit(1)

    senha = getpass("Senha (mínimo 8 caracteres): ")
    confirmacao = getpass("Repita a senha: ")

    if len(senha) < 8:
        print("A senha precisa ter pelo menos 8 caracteres.")
        sys.exit(1)
    if senha != confirmacao:
        print("As senhas não conferem.")
        sys.exit(1)

    senha_hash = generate_password_hash(senha)

    try:
        conexao = conectar()
    except Exception as erro:
        print(f"Não foi possível conectar ao banco: {erro}")
        sys.exit(1)

    try:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if cursor.fetchone():
                print("Já existe um usuário com este e-mail.")
                sys.exit(1)

            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha_hash, perfil) "
                "VALUES (%s, %s, %s, 'administrador')",
                (nome, email, senha_hash),
            )
        conexao.commit()
        print("\nAdministrador criado com sucesso.")
    finally:
        conexao.close()


if __name__ == "__main__":
    main()