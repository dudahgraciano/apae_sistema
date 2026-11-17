-- =====================================================================
-- Sistema APAE - Espírito Santo do Pinhal
-- Estrutura do banco de dados (MariaDB)
-- Pode ser executado mais de uma vez sem apagar dados existentes.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS apae_sistema
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE apae_sistema;

-- ---------------------------------------------------------------------
-- Usuários (colaboradores da APAE)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nome        VARCHAR(120) NOT NULL,
    email       VARCHAR(150) NOT NULL,
    senha_hash  VARCHAR(255) NOT NULL,
    perfil      ENUM('administrador', 'colaborador', 'visualizador')
                NOT NULL DEFAULT 'colaborador',
    ativo       TINYINT(1) NOT NULL DEFAULT 1,
    criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_usuarios_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Turmas (lista fixa usada no formulário e nos filtros)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS turmas (
    id     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nome   VARCHAR(100) NOT NULL,
    ativa  TINYINT(1) NOT NULL DEFAULT 1,

    PRIMARY KEY (id),
    UNIQUE KEY uq_turmas_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Categorias das atividades (lista fixa)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categorias (
    id     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nome   VARCHAR(100) NOT NULL,
    ativa  TINYINT(1) NOT NULL DEFAULT 1,

    PRIMARY KEY (id),
    UNIQUE KEY uq_categorias_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Atividades realizadas na instituição
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atividades (
    id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nome             VARCHAR(150) NOT NULL,
    descricao        TEXT NULL,
    data_realizacao  DATE NOT NULL,
    turma_id         INT UNSIGNED NOT NULL,
    categoria_id     INT UNSIGNED NOT NULL,
    usuario_id       INT UNSIGNED NOT NULL,
    criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                     ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_atividades_data (data_realizacao),
    KEY idx_atividades_nome (nome),
    KEY idx_atividades_turma (turma_id),
    KEY idx_atividades_categoria (categoria_id),
    KEY idx_atividades_usuario (usuario_id),

    -- RESTRICT: não permite apagar turma, categoria ou usuário que
    -- já estejam em uso (o sistema desativa em vez de apagar).
    CONSTRAINT fk_atividades_turma
        FOREIGN KEY (turma_id) REFERENCES turmas (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_atividades_categoria
        FOREIGN KEY (categoria_id) REFERENCES categorias (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_atividades_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Mídias (fotografias e vídeos) vinculadas a uma atividade
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS midias (
    id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
    atividade_id   INT UNSIGNED NOT NULL,
    nome_original  VARCHAR(255) NOT NULL,
    nome_arquivo   VARCHAR(64) NOT NULL,
    tipo           ENUM('foto', 'video') NOT NULL,
    mime_type      VARCHAR(100) NOT NULL,
    tamanho_bytes  BIGINT UNSIGNED NOT NULL,
    enviado_por    INT UNSIGNED NOT NULL,
    enviado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_midias_nome_arquivo (nome_arquivo),
    KEY idx_midias_atividade (atividade_id),
    KEY idx_midias_tipo (tipo),

    -- CASCADE: ao excluir uma atividade, suas mídias são removidas do banco.
    CONSTRAINT fk_midias_atividade
        FOREIGN KEY (atividade_id) REFERENCES atividades (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_midias_usuario
        FOREIGN KEY (enviado_por) REFERENCES usuarios (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Dados iniciais (INSERT IGNORE: não duplica se rodar de novo)
-- ---------------------------------------------------------------------
INSERT IGNORE INTO turmas (nome) VALUES
    ('Estimulação Precoce'),
    ('Educação Infantil'),
    ('Ensino Fundamental'),
    ('Educação de Jovens e Adultos'),
    ('Oficina de Artes');

INSERT IGNORE INTO categorias (nome) VALUES
    ('Atividade Pedagógica'),
    ('Arte e Cultura'),
    ('Esporte e Lazer'),
    ('Passeio e Visita'),
    ('Festa e Comemoração'),
    ('Terapêutica'),
    ('Oficina'),
    ('Outros');

-- ---------------------------------------------------------------------
-- Usuário do banco usado pelo sistema (princípio do menor privilégio).
-- TROQUE a senha abaixo e use a mesma no arquivo .env
-- ---------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'apae_app'@'localhost' IDENTIFIED BY 'Apae@Dev2026';
ALTER USER 'apae_app'@'localhost' IDENTIFIED BY 'Apae@Dev2026';
GRANT SELECT, INSERT, UPDATE, DELETE ON apae_sistema.* TO 'apae_app'@'localhost';
FLUSH PRIVILEGES;