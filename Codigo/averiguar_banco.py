import sqlite3

conexao = sqlite3.connect("instance/restaurantev2.db")

produtos = conexao.execute(
    "SELECT * FROM produtos"
).fetchall()

categorias = conexao.execute(
    "SELECT * FROM categorias"
).fetchall()

print("PRODUTOS:")
for produto in produtos:
    print(dict(produto) if hasattr(produto, "keys") else produto)

print("\nCATEGORIAS:")
for categoria in categorias:
    print(categoria)

    resultado = conexao.execute("""
    SELECT
        produtos.*,
        categorias.nome AS categoria_nome
    FROM produtos
    JOIN categorias
        ON produtos.categoria_id = categorias.id
    WHERE produtos.nome LIKE ?
       OR categorias.nome LIKE ?
    ORDER BY produtos.nome COLLATE NOCASE
""", ("%%", "%%")).fetchall()

print("\nRESULTADO DA CONSULTA:")
for produto in resultado:
    print(produto)