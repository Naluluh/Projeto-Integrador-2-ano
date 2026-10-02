"""Testes de integração: executam o mesmo fluxo usado por uma pessoa no navegador."""
import io
import sqlite3

from openpyxl import load_workbook

from app import create_app


def login(client):
    return client.post("/login", data={"usuario": "admin", "senha": "admin123"}, follow_redirects=True)


def test_middleware_redireciona_visitante(client):
    resposta = client.get("/produtos")
    assert resposta.status_code == 302
    assert "/login" in resposta.headers["Location"]


def test_fluxo_completo(client, app):
    resposta = login(client)
    assert "Olá, Administrador" in resposta.get_data(as_text=True)

    resposta = client.post("/produtos/novo", data={
        "nome": "Café", "fabricante": "Serra", "unidade": "pacote",
        "preco": "18,90", "estoque": "10",
    }, follow_redirects=True)
    assert "Produto cadastrado" in resposta.get_data(as_text=True)

    resposta = client.post("/compras/carrinho/adicionar", data={
        "produto_id": "1", "quantidade": "2"
    }, follow_redirects=True)
    assert "R$ 37,80" in resposta.get_data(as_text=True)

    resposta = client.post("/compras/finalizar", follow_redirects=True)
    pagina = resposta.get_data(as_text=True)
    assert "Compra #1" in pagina
    assert "R$ 37,80" in pagina

    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT estoque FROM produtos WHERE id=1").fetchone()[0] == 8
        assert db.execute("SELECT total_centavos FROM compras WHERE id=1").fetchone()[0] == 3780


def test_exportacoes_excel(client):
    login(client)
    for rota, titulo in [("/produtos/exportar", "Produtos"), ("/compras/exportar", "Compras")]:
        resposta = client.get(rota)
        assert resposta.status_code == 200
        assert resposta.headers["Content-Type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        workbook = load_workbook(io.BytesIO(resposta.data))
        assert workbook.active.title == titulo


def test_cadastro_e_login_novo_usuario(client):
    resposta = client.post("/cadastro", data={
        "nome": "Maria Silva", "usuario": "maria", "senha": "senha123"
    }, follow_redirects=True)
    assert "Cadastro realizado" in resposta.get_data(as_text=True)
    resposta = client.post("/login", data={"usuario": "maria", "senha": "senha123"}, follow_redirects=True)
    assert "Olá, Maria Silva" in resposta.get_data(as_text=True)


def test_exclusao_e_edicao_exigem_post_ou_formulario(client):
    login(client)
    assert client.get("/produtos/1/excluir").status_code == 405
    assert client.get("/logout").status_code == 405
