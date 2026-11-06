"""Model responsável pelos endereços dos clientes."""

from database import get_db


def endereco_por_usuario(usuario_id):

    db = get_db()

    return db.execute(
        """
        SELECT *
        FROM enderecos
        WHERE usuario_id = ?
        """,
        (usuario_id,)
    ).fetchall()


def atualizar(
    endereco_id,
    usuario_id,
    cep,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    pais
):

    db = get_db()

    db.execute("""
        UPDATE enderecos
        SET
            cep = ?,
            logradouro = ?,
            numero = ?,
            complemento = ?,
            bairro = ?,
            cidade = ?,
            estado = ?,
            pais = ?
        WHERE id = ? AND usuario_id = ?
    """, (
        cep,
        logradouro,
        numero,
        complemento,
        bairro,
        cidade,
        estado,
        pais,
        endereco_id,
        usuario_id
    ))

    db.commit()


def criar(
    usuario_id,
    cep,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    pais
):
    """Cadastra o endereço de um usuário."""

    db = get_db()

    db.execute(
        """
        INSERT INTO enderecos (
            usuario_id,
            cep,
            logradouro,
            numero,
            complemento,
            bairro,
            cidade,
            estado,
            pais
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            cep,
            logradouro,
            numero,
            complemento,
            bairro,
            cidade,
            estado,
            pais
        )
    )

    db.commit()