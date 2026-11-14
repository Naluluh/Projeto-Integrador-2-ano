# Consultas e regras das reservas de bancada
import secrets
from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError

from database import get_db
from utils import hoje_brasilia


class BancadaOcupada(Exception):
    """A bancada já está reservada em algum dos dias pedidos."""

    # Guarda os dias que já estão ocupados
    def __init__(self, dias):
        super().__init__("Bancada ocupada")
        self.dias = dias


# Lista as datas (texto AAAA-MM-DD) de inicio até fim
def dias_do_periodo(inicio, fim):
    dia = date.fromisoformat(inicio)
    ultimo = date.fromisoformat(fim)
    dias = []

    while dia <= ultimo:
        dias.append(dia.isoformat())
        dia += timedelta(days=1)

    return dias


# Dias do período em que a bancada já está reservada
def dias_ocupados(categoria_id, inicio, fim):
    linhas = get_db().execute("""
        SELECT data FROM reserva_dias
        WHERE categoria_id = ? AND data >= ? AND data <= ?
        ORDER BY data
    """, (categoria_id, inicio, fim)).fetchall()

    return [linha["data"] for linha in linhas]


# Cria a reserva e ocupa os dias. Se algum dia já estiver ocupado, levanta BancadaOcupada
def criar(cliente_id, categoria_id, chef_id, inicio, fim,
          pessoas, telefone, email, observacoes):
    db = get_db()

    ocupados = dias_ocupados(categoria_id, inicio, fim)

    if ocupados:
        raise BancadaOcupada(ocupados)

    try:
        # O código definitivo depende do id, então começa com um provisório
        cursor = db.execute("""
            INSERT INTO reservas (
                codigo, cliente_id, categoria_id, chef_id,
                data_inicio, data_fim, pessoas, telefone, email, observacoes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "tmp-" + secrets.token_hex(6), cliente_id, categoria_id, chef_id,
            inicio, fim, pessoas, telefone, email, observacoes
        ))

        reserva_id = cursor.lastrowid

        db.execute(
            "UPDATE reservas SET codigo = ? WHERE id = ?",
            (f"RSV-{reserva_id:04d}", reserva_id)
        )

        for dia in dias_do_periodo(inicio, fim):
            db.execute("""
                INSERT INTO reserva_dias (categoria_id, data, reserva_id)
                VALUES (?, ?, ?)
            """, (categoria_id, dia, reserva_id))

        db.commit()

    except IntegrityError:
        # Alguém reservou o mesmo dia ao mesmo tempo
        db.rollback()
        raise BancadaOcupada(dias_ocupados(categoria_id, inicio, fim))

    return reserva_id


_SELECT = """
    SELECT
        r.*,
        c.nome AS bancada_nome,
        cli.nome AS cliente_nome,
        chef.nome AS chef_nome
    FROM reservas AS r
    INNER JOIN categorias AS c ON c.id = r.categoria_id
    INNER JOIN usuarios AS cli ON cli.id = r.cliente_id
    INNER JOIN usuarios AS chef ON chef.id = r.chef_id
"""


# Uma reserva pelo id
def buscar(reserva_id):
    return get_db().execute(
        _SELECT + " WHERE r.id = ?", (reserva_id,)
    ).fetchone()


# Reservas do cliente, as mais novas primeiro
def listar_do_cliente(cliente_id):
    return get_db().execute(
        _SELECT + " WHERE r.cliente_id = ? ORDER BY r.data_inicio DESC, r.id DESC",
        (cliente_id,)
    ).fetchall()


# Reservas em que o cozinheiro foi escolhido
def listar_do_chef(chef_id):
    return get_db().execute(
        _SELECT + " WHERE r.chef_id = ? ORDER BY r.data_inicio DESC, r.id DESC",
        (chef_id,)
    ).fetchall()


# Todas as reservas, com filtros opcionais (data, status e cliente ou código)
def listar_todas(data=None, status=None, busca=None):
    sql = _SELECT + " WHERE 1 = 1"
    params = []

    if data:
        sql += " AND r.data_inicio <= ? AND r.data_fim >= ?"
        params += [data, data]

    if status in ("confirmada", "cancelada"):
        sql += " AND r.status = ?"
        params.append(status)

    if busca:
        sql += " AND (norm(cli.nome) LIKE norm(?) OR norm(r.codigo) LIKE norm(?))"
        params += [f"%{busca}%", f"%{busca}%"]

    sql += " ORDER BY r.data_inicio DESC, r.id DESC"

    return get_db().execute(sql, tuple(params)).fetchall()


# Cancela a reserva e libera os dias da bancada
def cancelar(reserva_id):
    db = get_db()

    db.execute("DELETE FROM reserva_dias WHERE reserva_id = ?", (reserva_id,))
    db.execute(
        "UPDATE reservas SET status = 'cancelada' WHERE id = ?", (reserva_id,)
    )
    db.commit()


# Bancadas que têm reserva ativa na data
def bancadas_ocupadas_em(data):
    linhas = get_db().execute(
        "SELECT categoria_id FROM reserva_dias WHERE data = ?", (data,)
    ).fetchall()

    return {linha["categoria_id"] for linha in linhas}


# Dias já reservados da bancada a partir de uma data (para avisar na tela)
def dias_reservados_a_partir(categoria_id, data):
    linhas = get_db().execute("""
        SELECT data FROM reserva_dias
        WHERE categoria_id = ? AND data >= ?
        ORDER BY data
    """, (categoria_id, data)).fetchall()

    return [linha["data"] for linha in linhas]


# Pedidos feitos dentro da reserva
def pedidos_da_reserva(reserva_id):
    return get_db().execute("""
        SELECT id, status, total_centavos, criado_em
        FROM pedidos
        WHERE reserva_id = ?
        ORDER BY id DESC
    """, (reserva_id,)).fetchall()


# Pratos da bancada que o cozinheiro prepara
def produtos_da_reserva(reserva):
    return get_db().execute("""
        SELECT p.*
        FROM produtos AS p
        INNER JOIN produto_chefs AS pc ON pc.produto_id = p.id
        WHERE p.categoria_id = ? AND pc.chef_id = ? AND p.ativo
        ORDER BY p.nome
    """, (reserva["categoria_id"], reserva["chef_id"])).fetchall()


# Só reserva confirmada e que ainda não terminou aceita pedidos
def aceita_pedidos(reserva):
    return (
        reserva["status"] == "confirmada"
        and reserva["data_fim"] >= hoje_brasilia().isoformat()
    )


# Status que aparece na tela (a reserva muda sozinha conforme os dias passam)
def status_exibido(reserva):
    if reserva["status"] == "cancelada":
        return "cancelada"

    hoje = hoje_brasilia().isoformat()

    if reserva["data_fim"] < hoje:
        return "concluída"

    if reserva["data_inicio"] <= hoje:
        return "em andamento"

    return "confirmada"
