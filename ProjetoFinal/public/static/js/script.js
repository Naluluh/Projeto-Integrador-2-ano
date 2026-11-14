// Finalizar pedido

function registrar_pedido(event){
    event.preventDefault();
    document.getElementById('confirmacao_pedido').style.display = "flex";
}

function cancelar_pedido(event){
    event.preventDefault();
    document.getElementById('confirmacao_pedido').style.display = "none";
}

const btnRegistrar = document.getElementById('registrar_pedido');
const btnCancelar = document.getElementById('cancelar_pedido');

if (btnRegistrar) btnRegistrar.addEventListener('click', registrar_pedido);
if (btnCancelar) btnCancelar.addEventListener('click', cancelar_pedido);

function ger_espec(event, num, acao){
    event.preventDefault();

    if(acao==0){
        document.getElementById(`especific${num}`).style.display = "flex";
    }
    else{
        document.getElementById(`especific${num}`).style.display = "none";
    }
}

function verificarCategoria(valor) {
    const boxNova = document.getElementById('boxNovaCategoria');
    if (valor === '__nova__') {
        boxNova.style.display = 'block';
    } else {
        boxNova.style.display = 'none';
    }
}

async function cadastrarCategoriaAsync() {
    const inputNome = document.getElementById('nomeNovaCategoria');
    const nomeCategoria = inputNome.value.trim();

    if (!nomeCategoria) {
        alert('Digite o nome da categoria!');
        return;
    }

    try {
        const response = await fetch('/categorias/api/categorias', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                nome: nomeCategoria
            })
        });

        if (response.ok) {
            const novaCategoria = await response.json();

            const select = document.getElementById('categoria_select');

            const novaOpcao = document.createElement('option');

            novaOpcao.value = novaCategoria.id;
            novaOpcao.textContent = novaCategoria.nome;
            novaOpcao.selected = true;

            select.appendChild(novaOpcao);

            inputNome.value = '';

            document.getElementById('boxNovaCategoria').style.display = 'none';

            alert('Categoria cadastrada com sucesso!');

        } else {
            const erro = await response.json();
            alert(erro.mensagem || 'Erro ao cadastrar categoria.');
        }

        } catch (err) {
        console.error('Erro na requisição:', err);
        alert('Erro ao conectar com o servidor.');
    }
}



/* ====================================================
   SENHAS: mostrar/ocultar, requisitos e confirmação
   ==================================================== */

// Botões "Mostrar/Ocultar".
document.querySelectorAll('.ver-senha').forEach(function (botao) {
    botao.addEventListener('click', function () {
        const campo = document.getElementById(botao.dataset.alvo);
        const mostrar = campo.type === 'password';

        campo.type = mostrar ? 'text' : 'password';
        botao.textContent = mostrar ? 'Ocultar' : 'Mostrar';
        botao.setAttribute('aria-pressed', mostrar ? 'true' : 'false');
    });
});

// Mesma regra do servidor (utils.validar_senha).
function verificarRegrasSenha(senha) {
    return {
        tamanho: senha.length >= 8 && senha.length <= 32 && !/\s/.test(senha),
        minuscula: /[a-z]/.test(senha),
        maiuscula: /[A-Z]/.test(senha),
        numero: /[0-9]/.test(senha),
        simbolo: /[!-\/:-@\[-`{-~]/.test(senha)
    };
}

function conferirConfirmacao(campoConfirma) {
    const senha = document.getElementById(campoConfirma.dataset.confirmaSenha);
    const aviso = document.querySelector(
        '[data-erro-de="' + campoConfirma.id + '"]'
    );
    const diferente = campoConfirma.value !== '' && campoConfirma.value !== senha.value;
    const mensagem = diferente ? 'As senhas não são iguais.' : '';

    campoConfirma.setCustomValidity(mensagem);
    if (aviso) aviso.textContent = mensagem;
}

document.querySelectorAll('[data-valida-senha]').forEach(function (campo) {
    const lista = document.querySelector('[data-regras-de="' + campo.id + '"]');

    campo.addEventListener('input', function () {
        const resultado = verificarRegrasSenha(campo.value);
        let todas = true;

        if (lista) {
            lista.querySelectorAll('li').forEach(function (item) {
                const ok = resultado[item.dataset.regra];
                item.classList.toggle('ok', ok);
                if (!ok) todas = false;
            });
        }

        // Campo vazio é permitido quando não é obrigatório (editar usuário).
        campo.setCustomValidity(
            campo.value === '' || todas ? '' : 'A senha não cumpre os requisitos.'
        );

        // Revalida a confirmação quando a senha muda.
        document.querySelectorAll(
            '[data-confirma-senha="' + campo.id + '"]'
        ).forEach(conferirConfirmacao);
    });
});

document.querySelectorAll('[data-confirma-senha]').forEach(function (campo) {
    campo.addEventListener('input', function () { conferirConfirmacao(campo); });
});


/* ====================================================
   MENSAGENS (flash): botão de fechar
   ==================================================== */

document.querySelectorAll('.fechar-alerta').forEach(function (botao) {
    botao.addEventListener('click', function () {
        botao.closest('.alerta').remove();
    });
});


/* ====================================================
   INATIVIDADE: encerra a sessão após 30 minutos parado
   ==================================================== */

(function () {
    const corpo = document.body;

    if (!corpo.dataset.logado) return;

    const limiteMs = Number(corpo.dataset.inatividade) * 1000;
    let ultimaAtividade = Date.now();
    let ultimoPing = Date.now();

    function registrarAtividade() {
        ultimaAtividade = Date.now();

        // Avisa o servidor (no máx. 1x por minuto) para ele não encerrar a
        // sessão de quem está digitando sem enviar nada.
        if (ultimaAtividade - ultimoPing > 60 * 1000) {
            ultimoPing = ultimaAtividade;
            fetch('/sessao/ping', { method: 'POST', credentials: 'same-origin' })
                .catch(function () {});
        }
    }

    ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(function (nome) {
        document.addEventListener(nome, registrarAtividade, { passive: true });
    });

    // Passou o limite sem atividade: recarrega; o servidor leva ao login.
    setInterval(function () {
        if (Date.now() - ultimaAtividade >= limiteMs) {
            window.location.reload();
        }
    }, 15 * 1000);
})();
