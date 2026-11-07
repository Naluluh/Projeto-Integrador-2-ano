#categorias.model

from database import get_db

def pegar_categorias():
    lista = get_db().execute('''
        SELECT * from categorias''').fetchall()

    if lista is None:
        return []

    return lista

def id_categoria(categoria):
    busca = get_db().execute('''
    SELECT * FROM produtos
    WHERE categoria_id = ?
    ''', (categoria,)).fetchone()

    if busca is None:
        return None
    
    return busca['id']

def mostrar_produtos(c):
    categoria = id_categoria(c)

    if categoria is None:
        return []

    return get_db().execute('''
    SELECT * from produtos
    WHERE categoria_id = ?
    ''', (categoria,)).fetchall()

def nome_categoria(id):
    pesquisa = get_db().execute('''
        SELECT * FROM categorias
        WHERE id = ?
        ''', (id,)).fetchone()
    
    if pesquisa is None:
        return None
        
    return pesquisa['nome']