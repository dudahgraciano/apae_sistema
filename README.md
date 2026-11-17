# Acervo APAE: Espírito Santo do Pinhal

Sistema web para guardar, organizar e consultar fotografias e vídeos das atividades da APAE de Espírito Santo do Pinhal. Projeto de Software desenvolvido para a faculdade.

**Tecnologias:** HTML5, CSS3, JavaScript, Python (Flask) e MariaDB (XAMPP).

## Funcionalidades

- Login com senha em hash, limite de tentativas e proteção CSRF
- Dashboard com totais e atividades recentes
- Cadastro, edição, busca e exclusão de atividades (turma, categoria, data e descrição)
- Envio de várias fotografias e vídeos de uma vez, com barra de progresso
- Galeria com filtros, busca e visualizador em tela cheia
- Gerenciamento de usuários com três perfis de acesso
- Registro de ações (auditoria) e confirmação de autorização de uso de imagem (LGPD)
- Testes automáticos de segurança e funcionamento

## Perfis de acesso

| Perfil | O que pode |
|---|---|
| Administrador | Tudo, incluindo usuários e registros de ações |
| Colaborador | Cadastra atividades, envia arquivos, edita e exclui o que cadastrou |
| Visualizador | Apenas consulta a galeria e as atividades |

## Instalação em um computador novo (Windows)

1. Instale o **Python 3.10 ou superior** (marque "Add Python to PATH") e o **XAMPP**.
2. Baixe ou clone este repositório, por exemplo em `C:\projetos\apae_sistema`.
3. Abra o terminal na pasta e crie o ambiente virtual:

   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. No **XAMPP Control Panel**, inicie o **Apache** e o **MySQL**.
5. Abra `http://localhost/phpmyadmin`, aba **SQL**, e execute, nesta ordem:
   - o conteúdo de `database/schema.sql` (troque a senha do usuário `apae_app`);
   - o conteúdo de `database/migracao_etapa13.sql`.
6. Crie o arquivo `.env` na raiz com:

   ```text
   SECRET_KEY=<gere com: python -c "import secrets; print(secrets.token_hex(32))">
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=apae_app
   DB_PASSWORD=<a mesma senha do schema.sql>
   DB_NAME=apae_sistema
   ```

7. Crie o primeiro administrador:

   ```powershell
   python criar_admin.py
   ```

## Como executar

```powershell
venv\Scripts\Activate.ps1
python app.py
```

Abra `http://127.0.0.1:5000` no navegador. Deixe o terminal aberto enquanto usar o sistema.

## Testes automáticos

Com o MySQL ligado:

```powershell
python testes_automaticos.py
```

O script cria dados de teste, verifica permissões, segurança e uploads, e apaga tudo no final.

## Estrutura do projeto

```text
app.py              aplicação Flask
config.py           configurações
extensions.py       banco de dados, CSRF e limite de tentativas
routes/             rotas (login, atividades, mídias, usuários, registros)
utils/              decoradores, upload seguro, auditoria e senhas
templates/          páginas HTML (Jinja2)
static/             CSS, JavaScript, fontes e imagens
database/           scripts SQL
uploads/            arquivos enviados (pasta privada, fora do Git)
```

## Segurança e LGPD

- Senhas guardadas apenas como hash
- Consultas parametrizadas (proteção contra SQL Injection)
- Token CSRF em todos os formulários
- Upload validado pelo conteúdo real do arquivo, com nome aleatório e remoção de metadados (EXIF/GPS) das fotos
- Arquivos entregues apenas a usuários logados (a pasta `uploads/` não é pública)
- Cabeçalhos de segurança e política de conteúdo (CSP)
- Registro de quem enviou, editou ou excluiu cada item

## Backup

Copie regularmente, em conjunto:

- o banco `apae_sistema` (phpMyAdmin → Exportar);
- a pasta `uploads/`.

## Antes de usar na instituição

- Defina senha para o usuário `root` do MariaDB.
- Use HTTPS e mude `SESSION_COOKIE_SECURE` para `True` em `config.py`.
- Não exponha o phpMyAdmin nem a porta 3306 para fora do computador.
- Guarde os termos de autorização de uso de imagem assinados.