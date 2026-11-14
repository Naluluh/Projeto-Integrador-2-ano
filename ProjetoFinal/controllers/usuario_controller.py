# Rotas de gerenciamento de usuários

"""Controller responsável pelo gerenciamento de funcionários."""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from sqlalchemy.exc import IntegrityError

from werkzeug.security import generate_password_hash

from models import usuario_model as usuario_model
from utils import administrador_required
from utils import gerar_senha_temporaria
from utils import salvar_imagem
from utils import validar_nova_senha


# Blueprint dos funcionários
usuario_bp = Blueprint(
    "usuario",
    __name__,
    url_prefix="/usuarios"
)


# Lista os usuários
@usuario_bp.get("")
@administrador_required
def listar():

    usuarios = usuario_model.listar()

    return render_template(
        "usuario.html",
        usuarios=usuarios
    )


# Cadastra um usuário
@usuario_bp.route(
    "/novo",
    methods=("GET", "POST")
)
@administrador_required
def novo():

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        nome_usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        senha = request.form.get(
            "senha",
            ""
        )

        confirmacao = request.form.get(
            "confirmar_senha",
            ""
        )

        cargo = request.form.get(
            "cargo",
            ""
        ).strip()

        # Cargos que o admin pode criar
        cargos_permitidos = {
            "cliente",
            "cozinheiro",
            "administrador"
        }

        # Validação dos campos
        erro_senha = validar_nova_senha(senha, confirmacao)

        if (
            len(nome) < 2
            or len(nome_usuario) < 3
            or cargo not in cargos_permitidos
        ):
            flash(
                "Preencha todos os campos corretamente.",
                "erro"
            )

        elif erro_senha:
            flash(erro_senha, "erro")

        else:

            try:

                # Foto vai pro banco
                foto_url = salvar_imagem(
                    request.files.get("foto_perfil")
                ) or "images/fotos_perfil/usuarios/template_usuarios.jpeg"

                # Guarda a senha em hash
                senha_hash = generate_password_hash(
                    senha
                )

                usuario_model.criar(
                    nome,
                    nome_usuario,
                    senha_hash,
                    cargo,
                    foto_url
                )

                flash(
                    "Funcionário cadastrado com sucesso.",
                    "sucesso"
                )

                # O cozinheiro cadastra o próprio perfil no primeiro login.
                return redirect(
                    url_for("usuario.listar")
                )

            except ValueError as erro:

                # Erros de validação do model
                flash(
                    str(erro),
                    "erro"
                )

            except IntegrityError:

                # Usuário repetido (UNIQUE)
                flash(
                    "Esse nome de usuário já está em uso.",
                    "erro"
                )

    return render_template(
        "usuario_form.html",
        usuario=None
    )


# Edita um usuário
@usuario_bp.route(
    "/<int:usuario_id>/editar",
    methods=("GET", "POST")
)
@administrador_required
def editar(usuario_id):

    usuario = usuario_model.buscar(
        usuario_id
    )

    # Não achou: 404
    if usuario is None:
        abort(404)

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        nome_usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        senha = request.form.get(
            "senha",
            ""
        )

        confirmacao = request.form.get(
            "confirmar_senha",
            ""
        )

        cargo = request.form.get(
            "cargo",
            ""
        ).strip()

        # Cargos permitidos
        cargos_permitidos = {
            "cliente",
            "cozinheiro",
            "administrador"
        }

        # Campos obrigatórios
        if (
            len(nome) < 2
            or len(nome_usuario) < 3
            or cargo not in cargos_permitidos
        ):
            flash(
                "Preencha nome, usuário e cargo corretamente.",
                "erro"
            )

        else:

            try:

                # Nova foto (opcional), guardada no banco.
                foto_url = salvar_imagem(
                    request.files.get("foto_perfil")
                )

                # Se veio senha nova, gera outro hash
                if senha:

                    erro_senha = validar_nova_senha(senha, confirmacao)

                    if erro_senha:
                        raise ValueError(erro_senha)

                    senha_hash = generate_password_hash(
                        senha
                    )

                else:

                    # Mantém a senha antiga
                    senha_hash = usuario[
                        "senha_hash"
                    ]

                usuario_model.atualizar(
                    usuario_id,
                    nome,
                    nome_usuario,
                    senha_hash,
                    cargo,
                    foto_url
                )

                flash(
                    "Funcionário atualizado com sucesso.",
                    "sucesso"
                )

                return redirect(
                    url_for("usuario.listar")
                )

            except ValueError as erro:

                flash(
                    str(erro),
                    "erro"
                )

            except IntegrityError:

                # Usuário repetido (UNIQUE)
                flash(
                    "Esse nome de usuário já está em uso.",
                    "erro"
                )

        return render_template(
            "usuario_form.html",
            usuario=usuario
        )

    return render_template(
        "usuario_form.html",
        usuario=usuario
    )


# Exclui um usuário
@usuario_bp.post(
    "/<int:usuario_id>/excluir"
)
@administrador_required
def excluir(usuario_id):

    usuario = usuario_model.buscar(
        usuario_id
    )

    if usuario is None:
        abort(404)

    # Admin não pode excluir a própria conta
    if usuario_id == session.get(
        "usuario_id"
    ):

        flash(
            "Você não pode excluir o funcionário atualmente logado.",
            "erro"
        )

        return redirect(
            url_for("usuario.listar")
        )

    try:
        usuario_model.excluir(
            usuario_id
        )

    except IntegrityError:

        # O usuário possui pedidos registrados.
        flash(
            "Este usuário possui pedidos registrados e não pode ser excluído.",
            "erro"
        )

        return redirect(
            url_for("usuario.listar")
        )

    flash(
        "Funcionário excluído com sucesso.",
        "sucesso"
    )

    return redirect(
        url_for("usuario.listar")
    )


# Gera uma senha temporária para o usuário
@usuario_bp.post(
    "/<int:usuario_id>/redefinir-senha"
)
@administrador_required
def redefinir_senha(usuario_id):
    """Gera uma senha temporária (atende "esqueci minha senha")."""

    usuario = usuario_model.buscar(usuario_id)

    if usuario is None:
        abort(404)

    if usuario_id == session.get("usuario_id"):
        flash(
            "Para trocar a sua própria senha use a opção Alterar senha.",
            "erro"
        )

        return redirect(url_for("usuario.listar"))

    senha_temporaria = gerar_senha_temporaria()

    # A pessoa será obrigada a trocar a senha no próximo login.
    usuario_model.atualizar_senha(
        usuario_id,
        generate_password_hash(senha_temporaria),
        temporaria=True
    )

    # A senha é exibida só nesta resposta (não fica guardada em lugar nenhum).
    return render_template(
        "senha_temporaria.html",
        usuario=usuario,
        senha=senha_temporaria
    )
