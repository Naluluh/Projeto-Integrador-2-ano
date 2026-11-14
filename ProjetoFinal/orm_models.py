# Descreve as tabelas do banco
"""Esquema do banco de dados (SQLAlchemy declarativo).

Estas classes descrevem as tabelas do Sabor & Clic. O arquivo `database.py`
usa `Base.metadata.create_all()` para criar as tabelas na primeira execução
(Neon/PostgreSQL na Vercel, SQLite local). Se a tabela já existir, nada é alterado.

Observação: os valores em dinheiro ficam em centavos (inteiros) e as datas
ficam como texto UTC ("AAAA-MM-DD HH:MM:SS"), exibidas em horário de Brasília
pelo filtro |datahora (ver utils.py).
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    Text,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import usa_postgres


class Base(DeclarativeBase):
    pass


# Data/hora padrão (texto UTC "AAAA-MM-DD HH:MM:SS", igual no SQLite e no Postgres)
if usa_postgres():
    _AGORA = text("to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')")
else:
    _AGORA = text("CURRENT_TIMESTAMP")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    usuario: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(Text, nullable=False)
    foto_url: Mapped[str | None] = mapped_column(Text)
    cargo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=_AGORA
    )

    # Senha temporária: obriga a trocar no login
    senha_temporaria: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )

    # Quando pediu "esqueci minha senha" (segundos desde 1970)
    reset_solicitado_em: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        CheckConstraint(
            "cargo IN ('cliente','cozinheiro','administrador')",
            name="ck_usuarios_cargo",
        ),
    )


# Usuário único, sem diferenciar maiúsculas
Index("ux_usuarios_usuario_lower", func.lower(Usuario.__table__.c.usuario), unique=True)


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    foto_url: Mapped[str | None] = mapped_column(Text)


Index("ux_categorias_nome_lower", func.lower(Categoria.__table__.c.nome), unique=True)


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    categoria_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categorias.id", ondelete="CASCADE"), nullable=False
    )
    foto_url: Mapped[str | None] = mapped_column(Text)
    preco_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    modo_preparo: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=_AGORA
    )

    # Prato visível ou oculto para clientes e cozinheiros
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )

    __table_args__ = (
        CheckConstraint("preco_centavos >= 0", name="ck_produtos_preco"),
    )


class ProdutoChef(Base):
    __tablename__ = "produto_chefs"

    produto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("produtos.id", ondelete="CASCADE"), primary_key=True
    )
    chef_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )


class Endereco(Base):
    __tablename__ = "enderecos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    cep: Mapped[str] = mapped_column(Text, nullable=False)
    logradouro: Mapped[str] = mapped_column(Text, nullable=False)
    numero: Mapped[str] = mapped_column(Text, nullable=False)
    complemento: Mapped[str | None] = mapped_column(Text)
    bairro: Mapped[str] = mapped_column(Text, nullable=False)
    cidade: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False)
    pais: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'Brasil'")
    )


class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    unidade: Mapped[str] = mapped_column(Text, nullable=False)
    estoque: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("0")
    )
    armazenado_em: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=_AGORA
    )


class ProdutoIngrediente(Base):
    __tablename__ = "produto_ingredientes"

    produto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("produtos.id", ondelete="CASCADE"), primary_key=True
    )
    ingrediente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredientes.id", ondelete="CASCADE"), primary_key=True
    )
    quantidade: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_prod_ingr_quantidade"),
    )


class ProdutoIngredienteAlternativa(Base):
    __tablename__ = "produto_ingrediente_alternativas"

    produto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ingrediente_principal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ingrediente_alternativo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredientes.id", ondelete="CASCADE"), nullable=False
    )
    quantidade: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint(
            "produto_id",
            "ingrediente_principal_id",
            "ingrediente_alternativo_id",
        ),
        ForeignKeyConstraint(
            ["produto_id", "ingrediente_principal_id"],
            [
                "produto_ingredientes.produto_id",
                "produto_ingredientes.ingrediente_id",
            ],
            ondelete="CASCADE",
        ),
        CheckConstraint("quantidade > 0", name="ck_alt_quantidade"),
        CheckConstraint(
            "ingrediente_principal_id <> ingrediente_alternativo_id",
            name="ck_alt_diferente",
        ),
    )


class Reserva(Base):
    """Reserva de uma bancada (categoria) com um cozinheiro, por dias."""

    __tablename__ = "reservas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )
    categoria_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categorias.id"), nullable=False
    )
    chef_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )

    # Datas em texto "AAAA-MM-DD" (o período vai de data_inicio até data_fim)
    data_inicio: Mapped[str] = mapped_column(Text, nullable=False)
    data_fim: Mapped[str] = mapped_column(Text, nullable=False)
    pessoas: Mapped[int] = mapped_column(Integer, nullable=False)
    telefone: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    observacoes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'confirmada'")
    )
    criado_em: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=_AGORA
    )

    __table_args__ = (
        CheckConstraint("pessoas > 0", name="ck_reservas_pessoas"),
        CheckConstraint(
            "status IN ('confirmada', 'cancelada')", name="ck_reservas_status"
        ),
        CheckConstraint("data_fim >= data_inicio", name="ck_reservas_datas"),
    )


class ReservaDia(Base):
    """Um dia ocupado de uma bancada.

    A chave primária (bancada + dia) impede, no próprio banco, que duas
    reservas ocupem a mesma bancada no mesmo dia.
    """

    __tablename__ = "reserva_dias"

    categoria_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categorias.id"), primary_key=True
    )
    data: Mapped[str] = mapped_column(Text, primary_key=True)
    reserva_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reservas.id", ondelete="CASCADE"), nullable=False
    )


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )
    endereco_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("enderecos.id")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'espera'")
    )
    total_centavos: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    chef_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )
    criado_em: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=_AGORA
    )
    atualizado_em: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=_AGORA
    )

    # Reserva (bancada + cozinheiro) a que o pedido pertence, se houver
    reserva_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("reservas.id", ondelete="SET NULL")
    )

    __table_args__ = (
        CheckConstraint("total_centavos >= 0", name="ck_pedidos_total"),
    )


class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False
    )
    produto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("produtos.id"), nullable=False
    )
    produto_nome: Mapped[str] = mapped_column(Text, nullable=False)
    preco_unitario_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal_centavos: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("preco_unitario_centavos >= 0", name="ck_itens_preco"),
        CheckConstraint("quantidade > 0", name="ck_itens_quantidade"),
        CheckConstraint("subtotal_centavos >= 0", name="ck_itens_subtotal"),
    )


class ItemPedidoSubstituicao(Base):
    """Quais porções do item foram feitas com ingrediente alternativo."""

    __tablename__ = "itens_pedido_substituicoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_pedido_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("itens_pedido.id", ondelete="CASCADE"), nullable=False
    )
    ingrediente_original: Mapped[str] = mapped_column(Text, nullable=False)
    ingrediente_alternativo: Mapped[str] = mapped_column(Text, nullable=False)
    unidade: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    porcoes: Mapped[int] = mapped_column(Integer, nullable=False)
    quantidade: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("porcoes > 0", name="ck_subst_porcoes"),
        CheckConstraint("quantidade >= 0", name="ck_subst_quantidade"),
    )


class Perfil(Base):
    __tablename__ = "perfis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    formacao: Mapped[str | None] = mapped_column(Text)
    biografia: Mapped[str] = mapped_column(Text, nullable=False)
    experiencia: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )


class PerfilCategoria(Base):
    __tablename__ = "perfis_categorias"

    categoria_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categorias.id", ondelete="CASCADE"), primary_key=True
    )
    perfil_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("perfis.id", ondelete="CASCADE"), primary_key=True
    )


class Imagem(Base):
    """Fotos enviadas pelos usuários (guardadas no próprio banco)."""

    __tablename__ = "imagens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    dados: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    criado_em: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=_AGORA
    )


class LoginTentativa(Base):
    """Controle de tentativas de login (proteção contra força bruta)."""

    __tablename__ = "login_tentativas"

    chave: Mapped[str] = mapped_column(Text, primary_key=True)
    tentativas: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    atualizado_em: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    bloqueado_ate: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
