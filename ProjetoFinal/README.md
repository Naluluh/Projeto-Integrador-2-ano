# Sabor & Clic — Vercel + Neon

Flask + SQLAlchemy. Na Vercel usa o banco **Neon (PostgreSQL)**; sem `DATABASE_URL`
roda com SQLite local (`instance/sabor_e_clic.db`), como antes.

## Subir na Vercel

1. Coloque o conteúdo desta pasta na raiz de um repositório do GitHub.
2. Na Vercel: **Add New > Project**, escolha o repositório (framework Flask é detectado sozinho).
3. Crie o banco no Neon (ou **Storage > Neon** na própria Vercel, que já cria `DATABASE_URL`).
4. Em **Settings > Environment Variables** defina:
   - `DATABASE_URL`: string de conexão do Neon (aceita `postgresql://...?sslmode=require`)
   - `SECRET_KEY`: texto longo e aleatório
   - `ADMIN_SENHA_INICIAL` (opcional): senha do primeiro login do admin
5. **Deploy**. As tabelas e o usuário `admin` são criados no primeiro acesso.

Primeiro login: usuário `admin`, senha `admin123` (ou `ADMIN_SENHA_INICIAL`).
O sistema pede para trocar a senha na hora.

## O que mudou para a Vercel

- `config.py`: lê `DATABASE_URL` (troca `postgresql://` por `postgresql+psycopg://`), exige `SECRET_KEY` e cookie seguro na Vercel.
- `database.py`: conexão sem pool (serverless) e ajuste automático do SQL para Postgres (`?`, `GROUP_CONCAT`, ids novos, `norm()`).
- `orm_models.py`: padrões de data/booleano que funcionam no Postgres.
- `utils.py`: pega o IP real pelo `X-Forwarded-For` na Vercel (bloqueio de login por IP).
- `static/` foi para `public/static/` (a Vercel serve essa pasta direto; os links `/static/...` não mudam).
- `requirements.txt` ganhou `psycopg[binary]`; `.python-version` fixa o Python 3.12.

As fotos enviadas já ficam no banco, então nada é gravado em disco.

## Rodar local

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Para testar local contra o Neon, defina `DATABASE_URL` e `SECRET_KEY` antes (veja `.env.example`).

## Dados de demonstração

`python popular_demo.py` **apaga tudo** do banco apontado por `DATABASE_URL`
(ou do SQLite local) e cria exemplos. Use com cuidado.
