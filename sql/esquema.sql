
-- AUDITORIO PLATA
-- Base de datos Oracle

CREATE TABLE eventos (
    id NUMBER PRIMARY KEY,
    nombre VARCHAR2(150) NOT NULL,
    aforo NUMBER DEFAULT 20000 NOT NULL,
    emitidos NUMBER DEFAULT 0 NOT NULL,
    CONSTRAINT ck_aforo CHECK (
        aforo > 0 AND
        emitidos >= 0 AND
        emitidos <= aforo
    )
);

CREATE SEQUENCE seq_folio
START WITH 1
INCREMENT BY 1
NOCYCLE;

CREATE TABLE boletos (
    folio NUMBER PRIMARY KEY,
    evento_id NUMBER NOT NULL,
    solicitud_id VARCHAR2(36) UNIQUE NOT NULL,
    fecha_emision TIMESTAMP WITH TIME ZONE
        DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_evento
        FOREIGN KEY (evento_id)
        REFERENCES eventos(id)
);

CREATE TABLE bitacora (
    id NUMBER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    solicitud_id VARCHAR2(36),
    hilo_id VARCHAR2(100),
    hora_envio TIMESTAMP WITH TIME ZONE,
    hora_respuesta TIMESTAMP WITH TIME ZONE,
    folio NUMBER,
    estado VARCHAR2(20) NOT NULL,
    detalle VARCHAR2(500),
    CONSTRAINT ck_estado CHECK (
        estado IN ('EXITO', 'RECHAZO', 'ERROR')
    )
);

INSERT INTO eventos (id, nombre, aforo, emitidos)
VALUES (1, 'Concierto Navideño', 20000, 0);

COMMIT;