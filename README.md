# Acervo APAE: Espírito Santo do Pinhal

**MVP:** plataforma web para centralizar, organizar e consultar fotografias e vídeos das atividades da APAE, substituindo as pastas soltas do Google Drive.

Sistema web para guardar, organizar e consultar fotografias e vídeos das atividades da APAE de Espírito Santo do Pinhal. Projeto de Software desenvolvido para a faculdade.

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

