//finalizar pedido

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
        boxNova.style.display = 'block'; // Mostra o input
    } else {
        boxNova.style.display = 'none';  // Esconde o input
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

