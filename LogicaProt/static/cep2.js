
// Classe responsável apenas por consultar o ViaCEP
// Espera o botao ser acionado
await formularioEndereco.aguardarConsulta();
class ConsultorCep {
    #urlBase = 'https://viacep.com.br/ws';

    // Remove tudo que não for número
    limpar(cep) {
        return cep.replace(/\D/g, '');
    }

    // Verifica se o CEP tem exatamente 8 dígitos
    ehValido(cep) {
        return this.limpar(cep).length === 8;
    }

    // Consulta a API e devolve os dados, ou null se o CEP não existir
    async consultar(cep) {
        const cepLimpo = this.limpar(cep);

        const resposta = await fetch(`${this.#urlBase}/${cepLimpo}/json/`);
        const dados = await resposta.json();

        if (dados.erro) {
            return null;
        }

        return dados;
    }
}

// Classe responsável por ligar o formulário ao consultor de CEP

class FormularioEndereco {
    #consultor;
    #campos;
    #consultaEmAndamento = null;

    constructor(consultor, ids = {}) {
        this.#consultor = consultor;

        // IDs padrão dos campos (podem ser sobrescritos)
        const idsPadrao = {
            cep: 'cep',
            logradouro: 'logradouro',
            bairro: 'bairro',
            cidade: 'cidade',
            estado: 'estado',
            pais: 'pais'
        };
        const idsFinais = { ...idsPadrao, ...ids };

        // Pega os elementos da página
        this.#campos = {};
        for (const nome in idsFinais) {
            this.#campos[nome] = document.getElementById(idsFinais[nome]);
        }
    }

    // Liga o evento de blur ao campo CEP
    iniciar() {
        if (!this.#campos.cep) {
            return;
        }

        this.#campos.cep.addEventListener('blur', () => {
            this.#consultaEmAndamento = this.#buscarCep();
        });
    }

    // Permite que outro código (ex.: o submit) espere a consulta terminar
    async aguardarConsulta() {
        if (this.#consultaEmAndamento) {
            await this.#consultaEmAndamento;
        }
    }

    // Consulta o CEP e preenche os campos
    async #buscarCep() {
        const valor = this.#campos.cep.value;

        // Campo vazio: não faz nada
        if (valor === '') {
            return;
        }

        if (!this.#consultor.ehValido(valor)) {
            alert('CEP inválido! Digite 8 números.');
            this.limpar();
            return;
        }

        try {
            const dados = await this.#consultor.consultar(valor);

            if (dados === null) {
                alert('CEP não encontrado.');
                this.limpar();
                return;
            }

            this.#preencher(dados);
        } catch (erro) {
            console.error('Erro ao consultar o CEP:', erro);
            alert('Não foi possível consultar o CEP.');
        }
    }

    // Preenche os campos do endereço (ignora os que não existem na página)
    #preencher(dados) {
        this.#definir('logradouro', dados.logradouro || '');
        this.#definir('bairro', dados.bairro || '');
        this.#definir('cidade', dados.localidade || '');
        this.#definir('estado', dados.uf || '');
        this.#definir('pais', 'Brasil');
    }

    // Limpa o CEP e os campos preenchidos
    limpar() {
        this.#definir('cep', '');
        this.#definir('logradouro', '');
        this.#definir('bairro', '');
        this.#definir('cidade', '');
        this.#definir('estado', '');
        this.#definir('pais', '');
    }

    // Atribui valor a um campo, só se ele existir
    #definir(nome, valor) {
        if (this.#campos[nome]) {
            this.#campos[nome].value = valor;
        }
    }
}


// Inicialização

const formularioEndereco = new FormularioEndereco(new ConsultorCep());
formularioEndereco.iniciar();
