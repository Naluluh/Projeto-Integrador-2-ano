# Consultas dos endereços
"""Model responsável pelos endereços dos clientes."""

from database import get_db


# Busca o endereço de um usuário
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


# Atualiza o endereço
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


# Cadastra o endereço
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

# Devolve o endereço mais recente do usuário
def ultimo_endereco(usuario_id):
    """Retorna o endereço mais recente do usuário (ou None)."""
    return get_db().execute(
        """
        SELECT *
        FROM enderecos
        WHERE usuario_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (usuario_id,)
    ).fetchone()


# Devolve o id do endereço do usuário
def end_id(usuario_id):
    endereco = ultimo_endereco(usuario_id)
    return endereco["id"] if endereco else None