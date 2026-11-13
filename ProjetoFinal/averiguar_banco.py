import sqlite3

conexao = sqlite3.connect("instance/restaurantev2.db")

conexao.execute("""
    UPDATE categorias
    SET foto_url = 'images/fotos_perfil/categorias/template_categorias.jpeg'
    WHERE foto_url = 'images/fotos_perfil/categorias/template_categorias.webp'
""")

conexao.commit()
conexao.close()

print("Caminhos das categorias atualizados!")