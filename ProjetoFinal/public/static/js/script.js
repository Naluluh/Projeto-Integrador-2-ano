// Comportamentos das páginas: pedido, senha, alertas, sessão, reserva e CSRF
// Finalizar pedido

// Abre a janela de confirmação do pedido
function registrar_pedido(event){
    event.preventDefault();
    document.getElementById('confirmacao_pedido').style.display = "flex";
}

// Fecha a janela de confirmação do pedido
function cancelar_pedido(event){
    event.preventDefault();
    document.getElementById('confirmacao_pedido').style.display = "none";
}

const btnRegistrar = document.getElementById('registrar_pedido');
const btnCancelar = document.getElementById('cancelar_pedido');

if (btnRegistrar) btnRegistrar.addEventListener('click', registrar_pedido);
if (btnCancelar) btnCancelar.addEventListener('click', cancelar_pedido);

// Mostra ou esconde as especificações de um item
function ger_espec(event, num, acao){
    event.preventDefault();

    if(acao==0){
        document.getElementById(`especific${num}`).style.display = "flex";
    }
    else{
        document.getElementById(`especific${num}`).style.display = "none";
    }
}

// Mostra o campo de nova categoria quando ela é escolhida
function verificarCategoria(valor) {
    const boxNova = document.getElementById('boxNovaCategoria');
    if (valor === '__nova__') {
        boxNova.style.display = 'block';
    } else {
        boxNova.style.display = 'none';
    }
}

// Cadastra uma categoria nova sem recarregar a página
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

// Avisa se a confirmação é diferente da senha
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

    // Marca que a pessoa está usando a página e avisa o servidor
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


// Formulário de reserva: mostra só os cozinheiros da bancada escolhida e os dias já ocupados
(function () {
    const form = document.getElementById('form-reserva');

    if (!form) return;

    const bancadas = JSON.parse(form.dataset.bancadas || '[]');
    const selBancada = document.getElementById('categoria_id');
    const selChef = document.getElementById('chef_id');
    const aviso = document.getElementById('dias-ocupados');

    // Mostra os cozinheiros da bancada escolhida e os dias ocupados
    function atualizar() {
        const bancada = bancadas.find(function (b) { return String(b.id) === selBancada.value; });
        const escolhido = selChef.value || form.dataset.chefEscolhido;

        selChef.innerHTML = '';

        if (!bancada) {
            selChef.add(new Option('Escolha a bancada primeiro', ''));
            aviso.textContent = '';
            return;
        }

        if (bancada.chefs.length === 0) {
            selChef.add(new Option('Nenhum cozinheiro nesta bancada', ''));
        } else {
            selChef.add(new Option('Escolha o cozinheiro', ''));
        }

        bancada.chefs.forEach(function (c) {
            selChef.add(new Option(c.nome, c.id, false, String(c.id) === String(escolhido)));
        });

        if (bancada.ocupados.length) {
            const datas = bancada.ocupados.slice(0, 12).map(function (d) {
                return d.split('-').reverse().join('/');
            });
            aviso.textContent = 'Dias já reservados: ' + datas.join(', ') + (bancada.ocupados.length > 12 ? '…' : '');
        } else {
            aviso.textContent = 'Nenhum dia reservado nesta bancada por enquanto.';
        }
    }

    selBancada.addEventListener('change', function () {
        form.dataset.chefEscolhido = '';
        selChef.value = '';
        atualizar();
    });

    atualizar();
})();


// Manda o token CSRF em todo fetch que altera dados no mesmo site
(function () {
    const meta = document.querySelector('meta[name="csrf-token"]');

    if (!meta || !window.fetch) return;

    const fetchOriginal = window.fetch;

    window.fetch = function (url, opcoes) {
        opcoes = opcoes || {};
        const metodo = (opcoes.method || 'GET').toUpperCase();

        if (metodo !== 'GET' && metodo !== 'HEAD') {
            const cabecalhos = new Headers(opcoes.headers || {});
            cabecalhos.set('X-CSRF-Token', meta.content);
            opcoes.headers = cabecalhos;
        }

        return fetchOriginal.call(this, url, opcoes);
    };
})();
