#categorias_model

from database import get_db

def pegar_categorias():
    lista = get_db().execute('''
        SELECT * from categorias''').fetchall()

    if lista is None:
        return []

    return lista

def id_categoria(categoria):
    busca = get_db().execute("""
        SELECT id FROM categorias
        WHERE id = ?""", 
        (categoria,)).fetchone()

    if busca is None:
        return None

    return busca["id"]

def mostrar_produtos(c, incluir_inativos=False):
    categoria = id_categoria(c)

    if categoria is None:
        return []

    # Pratos indisponíveis ficam ocultos, exceto para o administrador.
    return get_db().execute('''
    SELECT * from produtos
    WHERE categoria_id = ?
    AND (ativo OR ?)
    ORDER BY nome
    ''', (categoria, bool(incluir_inativos))).fetchall()

def nome_categoria(id):
    pesquisa = get_db().execute('''
        SELECT * FROM categorias
        WHERE id = ?
        ''', (id,)).fetchone()
    
    if pesquisa is None:
        return None
        
    return pesquisa['nome']

def criar_categoria(nome, img_url=None):
    db = get_db()
    nome = nome.strip().upper()

    if not nome:
        raise ValueError("Informe o nome da categoria.")

    if not img_url:
        img_url = "images/fotos_perfil/categorias/template_categorias.jpeg"

    db.execute("""
        INSERT INTO categorias (nome, foto_url)
        VALUES (?, ?)
        ON CONFLICT(nome) DO NOTHING
    """, (nome, img_url))

    db.commit()

    categoria = db.execute("""
        SELECT id
        FROM categorias
        WHERE nome = ?
    """, (nome,)).fetchone()

    return categoria["id"]

def atualizar(categoria_id, nome, img_url=None):
    db = get_db()
    nome = nome.strip().upper()

    if not nome:
        raise ValueError("Informe o nome da categoria.")

    if img_url:
        db.execute("""
            UPDATE categorias
            SET nome = ?, foto_url = ?
            WHERE id = ?
        """, (nome, img_url, categoria_id))
    else:
        db.execute("""
            UPDATE categorias
            SET nome = ?
            WHERE id = ?
        """, (nome, categoria_id))

    db.commit()
