# Script que apaga o banco local e enche com dados de exemplo
"""Reset de demonstração do Sabor & Clic (banco SQLite local).

ATENÇÃO: apaga TODOS os dados do banco local e cria dados de exemplo
(contas, categorias, ingredientes, pratos, perfis, endereços e pedidos).

Uso:
    python popular_demo.py [caminho/do/arquivo_de_credenciais.txt]

Sem argumento, procura "relatorio_credenciais_reset.txt" ao lado deste
arquivo. Cada conta é criada com senha temporária (a pessoa troca no
primeiro login). As senhas ficam só no .txt: não são escritas aqui.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

from app import app
from config import INSTANCE_DIR
from database import get_db
from utils import gerar_senha_temporaria

BASE = Path(__file__).resolve().parent
ARQUIVO_PADRAO = BASE / "relatorio_credenciais_reset.txt"

FOTO_USUARIO = "images/fotos_perfil/usuarios/template_usuarios.jpeg"
FOTO_CATEGORIA = "images/fotos_perfil/categorias/template_categorias.jpeg"
FOTO_PRODUTO = "images/fotos_perfil/produtos/template_produtos.jpeg"

# Filhas primeiro, para respeitar as chaves estrangeiras.
TABELAS = [
    "itens_pedido_substituicoes", "login_tentativas", "imagens",
    "perfis_categorias", "perfis", "itens_pedido", "pedidos",
    "reserva_dias", "reservas",
    "produto_ingrediente_alternativas", "produto_ingredientes",
    "produto_chefs", "enderecos", "produtos", "ingredientes",
    "categorias", "usuarios",
]

CATEGORIAS = [
    "Italiana", "Brasileira", "Japonesa", "Massas", "Sobremesas",
    "Carnes", "Saladas", "Frutos do Mar", "Lanches", "Bebidas",
]

# Contas que completam as 10 pessoas quando o .txt tem só as 8 originais.
# As senhas são geradas na hora e gravadas em instance/credenciais_extras.txt.
USUARIOS_EXTRAS = [
    {"nome": "Lucas Ribeiro", "usuario": "chef.lucas", "cargo": "cozinheiro"},
    {"nome": "Fernanda Rocha", "usuario": "cliente.fernanda", "cargo": "cliente"},
]

INGREDIENTES = [
    ("Tomate", "kg", 35), ("Cebola", "kg", 20), ("Alho", "kg", 8),
    ("Manjericão", "maço", 12), ("Farinha de trigo", "kg", 40),
    ("Mussarela", "kg", 18), ("Parmesão", "kg", 7),
    ("Arroz arbóreo", "kg", 15), ("Peito de frango", "kg", 22),
    ("Cogumelo", "kg", 10), ("Azeite", "litro", 12), ("Macarrão", "kg", 25),
    ("Molho de soja", "litro", 8), ("Arroz japonês", "kg", 18),
    ("Salmão", "kg", 9), ("Alface", "unidade", 25), ("Batata", "kg", 30),
    ("Creme de leite", "litro", 12), ("Chocolate", "kg", 10),
    ("Açúcar", "kg", 25), ("Carne bovina", "kg", 25), ("Camarão", "kg", 8),
    ("Limão", "kg", 10), ("Pão de hambúrguer", "unidade", 60),
    ("Feijão", "kg", 30), ("Arroz branco", "kg", 40), ("Leite", "litro", 40),
    ("Morango", "kg", 10), ("Ovo", "unidade", 120), ("Laranja", "kg", 20),
]

# nome, descrição, categoria, preço (centavos), preparo, índice do chef,
# ingredientes. Chefs (pela ordem das contas): 0 Mariana, 1 Rafael,
# 2 Beatriz, 3 Lucas.
PRATOS = [
    ("Spaghetti ao pomodoro", "Massa com molho de tomate e manjericão.",
     "Italiana", 3890,
     "Cozinhe a massa e finalize no molho de tomate com azeite e manjericão.",
     0, [("Macarrão", 0.18), ("Tomate", 0.20), ("Alho", 0.01),
         ("Manjericão", 0.05)]),
    ("Risoto de cogumelos", "Arroz arbóreo cremoso com cogumelos.",
     "Italiana", 5290,
     "Refogue cebola, acrescente arroz e caldo aos poucos; finalize com parmesão.",
     0, [("Arroz arbóreo", 0.16), ("Cogumelo", 0.12), ("Cebola", 0.03),
         ("Parmesão", 0.02)]),
    ("Pizza marguerita individual",
     "Massa, tomate, mussarela e manjericão.", "Massas", 3590,
     "Abra a massa, cubra e asse até dourar.",
     0, [("Farinha de trigo", 0.18), ("Tomate", 0.12),
         ("Mussarela", 0.12), ("Manjericão", 0.03)]),
    ("Nhoque ao sugo", "Nhoque servido com molho de tomate.",
     "Massas", 4490, "Cozinhe o nhoque e envolva no molho de tomate.",
     0, [("Batata", 0.22), ("Farinha de trigo", 0.08), ("Tomate", 0.15)]),
    ("Yakisoba de legumes",
     "Macarrão salteado com legumes e molho de soja.", "Japonesa", 3990,
     "Salteie os ingredientes em fogo alto e misture o molho.",
     1, [("Macarrão", 0.16), ("Cebola", 0.03), ("Molho de soja", 0.03),
         ("Alface", 0.02)]),
    ("Salmão grelhado", "Salmão grelhado com arroz japonês.",
     "Japonesa", 6490,
     "Grelhe o salmão e sirva com arroz japonês cozido.",
     1, [("Salmão", 0.18), ("Arroz japonês", 0.12), ("Azeite", 0.01)]),
    ("Camarão ao alho e óleo", "Camarões salteados no alho com azeite.",
     "Frutos do Mar", 6890,
     "Doure o alho no azeite, salteie os camarões e finalize com limão.",
     1, [("Camarão", 0.20), ("Alho", 0.02), ("Azeite", 0.02),
         ("Limão", 0.03)]),
    ("Arroz cremoso de camarão", "Arroz arbóreo com camarões e parmesão.",
     "Frutos do Mar", 7290,
     "Refogue o camarão, junte o arroz e o caldo aos poucos até ficar cremoso.",
     1, [("Arroz arbóreo", 0.15), ("Camarão", 0.15), ("Alho", 0.01),
         ("Parmesão", 0.02)]),
    ("Salada da casa", "Salada fresca com molho de azeite.",
     "Saladas", 2290,
     "Higienize e corte os ingredientes; tempere na hora de servir.",
     1, [("Alface", 0.10), ("Tomate", 0.08), ("Azeite", 0.01)]),
    ("Salada caprese", "Tomate, mussarela e manjericão com azeite.",
     "Saladas", 2790,
     "Fatie o tomate e a mussarela, alterne e finalize com manjericão e azeite.",
     1, [("Tomate", 0.15), ("Mussarela", 0.10), ("Manjericão", 0.02),
         ("Azeite", 0.01)]),
    ("Frango cremoso", "Frango com molho suave e acompanhamento.",
     "Brasileira", 4290,
     "Sele o frango e prepare o molho com creme de leite e temperos.",
     2, [("Peito de frango", 0.20), ("Creme de leite", 0.08),
         ("Alho", 0.01)]),
    ("Prato feito da casa", "Arroz, feijão, ovo frito e batata frita.",
     "Brasileira", 3290,
     "Cozinhe o arroz e o feijão, frite o ovo e as batatas e monte o prato.",
     2, [("Arroz branco", 0.15), ("Feijão", 0.10), ("Ovo", 1),
         ("Batata", 0.12)]),
    ("Brownie de chocolate", "Brownie macio de chocolate.",
     "Sobremesas", 1890,
     "Misture os ingredientes e asse até formar uma crosta fina.",
     2, [("Chocolate", 0.08), ("Açúcar", 0.05), ("Farinha de trigo", 0.04)]),
    ("Mousse de morango", "Mousse leve de morango com creme de leite.",
     "Sobremesas", 1790,
     "Bata o morango com o açúcar, misture ao creme de leite e leve à geladeira.",
     2, [("Morango", 0.10), ("Creme de leite", 0.08), ("Açúcar", 0.03)]),
    ("Suco de laranja", "Suco natural de laranja, sem açúcar.",
     "Bebidas", 1190, "Esprema as laranjas e sirva gelado.",
     2, [("Laranja", 0.60)]),
    ("Limonada cremosa", "Limonada batida com leite, cremosa e gelada.",
     "Bebidas", 1390,
     "Bata o limão com o leite e o açúcar e coe antes de servir.",
     2, [("Limão", 0.20), ("Leite", 0.15), ("Açúcar", 0.03)]),
    ("Bife acebolado", "Bife grelhado com cebola e batatas.",
     "Carnes", 4890,
     "Grelhe o bife, doure a cebola e sirva com as batatas fritas.",
     3, [("Carne bovina", 0.25), ("Cebola", 0.06), ("Batata", 0.20)]),
    ("Medalhão ao molho de cogumelos",
     "Medalhão de carne com molho cremoso de cogumelos.",
     "Carnes", 6290,
     "Sele o medalhão e finalize com cogumelos e creme de leite.",
     3, [("Carne bovina", 0.22), ("Cogumelo", 0.08),
         ("Creme de leite", 0.06)]),
    ("Hambúrguer artesanal", "Pão, hambúrguer, queijo, tomate e alface.",
     "Lanches", 3490,
     "Grelhe o hambúrguer, derreta o queijo e monte o lanche.",
     3, [("Pão de hambúrguer", 1), ("Carne bovina", 0.15),
         ("Mussarela", 0.04), ("Tomate", 0.04), ("Alface", 0.02)]),
    ("Sanduíche de frango", "Frango grelhado com queijo e salada no pão.",
     "Lanches", 2990,
     "Grelhe o frango e monte o sanduíche com queijo e salada.",
     3, [("Pão de hambúrguer", 1), ("Peito de frango", 0.12),
         ("Mussarela", 0.04), ("Alface", 0.02)]),
]

# prato, ingrediente principal, alternativa, quantidade da alternativa
ALTERNATIVAS = [
    ("Risoto de cogumelos", "Parmesão", "Mussarela", 0.02),
    ("Salada caprese", "Mussarela", "Parmesão", 0.04),
    ("Sanduíche de frango", "Mussarela", "Parmesão", 0.03),
]

PERFIS = [
    ("Técnica em Gastronomia",
     "Especialista em massas e cozinha italiana.", "5 anos"),
    ("Gastronomia",
     "Experiência em cozinha oriental, frutos do mar e saladas.", "7 anos"),
    ("Curso profissional de cozinha",
     "Atuação em pratos brasileiros, sobremesas e bebidas.", "4 anos"),
    ("Churrasqueiro e cozinheiro",
     "Carnes na brasa, hambúrgueres e lanches artesanais.", "6 anos"),
]

# cliente (índice), itens [(prato, quantidade)], status, dias atrás.
# Todos os pratos de um pedido são do mesmo cozinheiro (como no app).
PEDIDOS = [
    (0, [("Spaghetti ao pomodoro", 2)], "entregue", 9),
    (1, [("Frango cremoso", 1), ("Brownie de chocolate", 2)], "entregue", 8),
    (2, [("Salmão grelhado", 1), ("Salada da casa", 1)], "entregue", 6),
    (3, [("Brownie de chocolate", 3)], "preparado", 5),
    (4, [("Hambúrguer artesanal", 2), ("Sanduíche de frango", 1)],
     "entregue", 4),
    (0, [("Risoto de cogumelos", 1), ("Nhoque ao sugo", 1)], "atrasado", 3),
    (1, [("Camarão ao alho e óleo", 2)], "preparado", 2),
    (2, [("Bife acebolado", 1), ("Medalhão ao molho de cogumelos", 1)],
     "espera", 1),
    (3, [("Suco de laranja", 2), ("Prato feito da casa", 2)], "espera", 1),
    (4, [("Pizza marguerita individual", 2)], "cancelado", 0),
]


# Lê as contas do arquivo de texto
def ler_credenciais(caminho):
    """Lê o .txt (blocos Nome / Usuário / Cargo / Senha inicial)."""

    campos = {"nome": "nome", "usuário": "usuario", "usuario": "usuario",
              "cargo": "cargo", "senha inicial": "senha"}
    pessoas, atual = [], {}

    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        if ":" not in linha:
            continue

        chave, _, valor = linha.partition(":")
        chave = campos.get(chave.strip().lower())

        if chave is None:
            continue

        if chave == "nome" and atual:
            pessoas.append(atual)
            atual = {}

        atual[chave] = valor.strip()

    if atual:
        pessoas.append(atual)

    for p in pessoas:
        if set(p) != {"nome", "usuario", "cargo", "senha"}:
            raise ValueError(f"Conta incompleta no arquivo: {p.get('usuario')}")

    usuarios = [p["usuario"].lower() for p in pessoas]
    if len(usuarios) != len(set(usuarios)):
        raise ValueError("Há nomes de usuário repetidos no arquivo.")

    return pessoas


# Apaga tudo e cria os dados de exemplo
def popular(db, pessoas):
    for tabela in TABELAS:
        db.execute(f"DELETE FROM {tabela}")

    ids = {}
    for p in pessoas:
        ids[p["usuario"]] = db.execute(
            """INSERT INTO usuarios
               (nome, usuario, senha_hash, cargo, foto_url, senha_temporaria)
               VALUES (?, ?, ?, ?, ?, TRUE)""",
            (p["nome"], p["usuario"], generate_password_hash(p["senha"]),
             p["cargo"], FOTO_USUARIO)
        ).lastrowid

    chefs = [ids[p["usuario"]] for p in pessoas if p["cargo"] == "cozinheiro"]
    clientes = [ids[p["usuario"]] for p in pessoas if p["cargo"] == "cliente"]

    cats = {
        nome: db.execute(
            "INSERT INTO categorias (nome, foto_url) VALUES (?, ?)",
            (nome.upper(), FOTO_CATEGORIA)
        ).lastrowid
        for nome in CATEGORIAS
    }

    ingr = {
        nome: db.execute(
            "INSERT INTO ingredientes (nome, unidade, estoque) VALUES (?, ?, ?)",
            (nome, unidade, estoque)
        ).lastrowid
        for nome, unidade, estoque in INGREDIENTES
    }

    produtos = {}          # nome -> id
    chef_do_prato = {}     # nome -> id do cozinheiro
    categorias_do_chef = {i: [] for i in range(len(chefs))}

    for nome, desc, cat, preco, preparo, chef_idx, receita in PRATOS:
        pid = db.execute(
            """INSERT INTO produtos
               (nome, descricao, categoria_id, preco_centavos,
                modo_preparo, foto_url)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nome, desc, cats[cat], preco, preparo, FOTO_PRODUTO)
        ).lastrowid
        produtos[nome] = pid
        chef_do_prato[nome] = chefs[chef_idx]

        # Quem faz o prato é responsável pela categoria dele (o app mantém as duas listas iguais)
        if cat not in categorias_do_chef[chef_idx]:
            categorias_do_chef[chef_idx].append(cat)

        db.execute("INSERT INTO produto_chefs (produto_id, chef_id) VALUES (?, ?)",
                   (pid, chefs[chef_idx]))

        for ingrediente, qtd in receita:
            db.execute(
                """INSERT INTO produto_ingredientes
                   (produto_id, ingrediente_id, quantidade) VALUES (?, ?, ?)""",
                (pid, ingr[ingrediente], qtd))

    for prato, principal, alternativo, qtd in ALTERNATIVAS:
        db.execute(
            """INSERT INTO produto_ingrediente_alternativas
               (produto_id, ingrediente_principal_id,
                ingrediente_alternativo_id, quantidade) VALUES (?, ?, ?, ?)""",
            (produtos[prato], ingr[principal], ingr[alternativo], qtd))

    for i, chef_id in enumerate(chefs):
        formacao, bio, exp = PERFIS[i]
        perfil_id = db.execute(
            """INSERT INTO perfis (formacao, biografia, experiencia, usuario_id)
               VALUES (?, ?, ?, ?)""", (formacao, bio, exp, chef_id)).lastrowid
        for cat in categorias_do_chef[i]:
            db.execute(
                "INSERT INTO perfis_categorias (categoria_id, perfil_id) VALUES (?, ?)",
                (cats[cat], perfil_id))

    ruas = ["Rua das Flores", "Avenida Paulista", "Rua Augusta",
            "Rua Oscar Freire", "Alameda Santos"]
    enderecos = [
        db.execute(
            """INSERT INTO enderecos (usuario_id, cep, logradouro, numero,
               bairro, cidade, estado, pais)
               VALUES (?, ?, ?, ?, 'Centro', 'São Paulo', 'SP', 'Brasil')""",
            (cliente_id, f"01{i}00-000", ruas[i % len(ruas)],
             str(100 + 10 * i))).lastrowid
        for i, cliente_id in enumerate(clientes)
    ]

    precos = {p[0]: p[3] for p in PRATOS}
    agora = datetime.now(timezone.utc)

    for cliente_idx, itens, status, dias in PEDIDOS:
        total = sum(precos[n] * q for n, q in itens)
        quando = (agora - timedelta(days=dias, hours=dias)).strftime(
            "%Y-%m-%d %H:%M:%S")
        cozinheiros = {chef_do_prato[n] for n, _ in itens}
        assert len(cozinheiros) == 1, "Pedido com mais de um cozinheiro"

        pedido_id = db.execute(
            """INSERT INTO pedidos (usuario_id, endereco_id, status,
               total_centavos, chef_id, criado_em, atualizado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (clientes[cliente_idx], enderecos[cliente_idx], status, total,
             cozinheiros.pop(), quando, quando)).lastrowid

        for nome, qtd in itens:
            db.execute(
                """INSERT INTO itens_pedido (pedido_id, produto_id,
                   produto_nome, preco_unitario_centavos, quantidade,
                   subtotal_centavos) VALUES (?, ?, ?, ?, ?, ?)""",
                (pedido_id, produtos[nome], nome, precos[nome], qtd,
                 precos[nome] * qtd))

    db.commit()

    return (len(pessoas), len(CATEGORIAS), len(INGREDIENTES), len(PRATOS),
            len(PEDIDOS))


# Acrescenta as contas extras que faltam
def completar_com_extras(pessoas):
    """Acrescenta as contas extras que ainda não estão no .txt.

    Devolve (lista completa, lista só das contas novas).
    """
    existentes = {p["usuario"].lower() for p in pessoas}
    novas = [
        {**extra, "senha": gerar_senha_temporaria(16)}
        for extra in USUARIOS_EXTRAS
        if extra["usuario"].lower() not in existentes
    ]

    return pessoas + novas, novas


# Roda o reset de demonstração
def executar(caminho, confirmar=True):
    pessoas, novas = completar_com_extras(ler_credenciais(caminho))

    if len([p for p in pessoas if p["cargo"] == "cozinheiro"]) < 4 or \
       len([p for p in pessoas if p["cargo"] == "cliente"]) < 5:
        raise ValueError(
            "São necessários ao menos 4 cozinheiros e 5 clientes "
            "(o .txt + as contas extras).")

    with app.app_context():
        print("\nATENÇÃO: isto apagará TODOS os dados do banco local:")
        print(" ", app.config["DATABASE_URL"])

        if confirmar and input('Para continuar, digite exatamente "RESETAR O BANCO": ') \
                != "RESETAR O BANCO":
            print("Operação cancelada. Nada foi alterado.")
            return

        db = get_db()

        try:
            resumo = popular(db, pessoas)
        except Exception:
            db.rollback()
            raise

    print("\nReset concluído. Contas: %d | Categorias: %d | Ingredientes: %d "
          "| Pratos: %d | Pedidos: %d" % resumo)
    print("Todas as contas pedem troca de senha no primeiro login.")

    if novas:
        arquivo = INSTANCE_DIR / "credenciais_extras.txt"
        arquivo.write_text(
            "\n\n".join(
                f"Nome: {p['nome']}\nUsuário: {p['usuario']}\n"
                f"Cargo: {p['cargo']}\nSenha inicial: {p['senha']}"
                for p in novas) + "\n",
            encoding="utf-8")
        print(f"Senhas das {len(novas)} contas extras: {arquivo}")
        print("Guarde em local privado e apague depois de usar.")


if __name__ == "__main__":
    try:
        executar(sys.argv[1] if len(sys.argv) > 1 else ARQUIVO_PADRAO)
    except Exception as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        sys.exit(1)
