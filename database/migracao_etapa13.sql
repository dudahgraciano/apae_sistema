USE apae_sistema;

CREATE TABLE IF NOT EXISTS registros (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id    INT UNSIGNED NULL,
    usuario_nome  VARCHAR(120) NULL,
    acao          VARCHAR(40) NOT NULL,
    detalhe       VARCHAR(500) NULL,
    ip            VARCHAR(45) NULL,
    criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_registros_data (criado_em),
    KEY idx_registros_acao (acao),
    KEY idx_registros_usuario (usuario_id),

    CONSTRAINT fk_registros_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;