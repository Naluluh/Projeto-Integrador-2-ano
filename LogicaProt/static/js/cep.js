const cepInput = document.getElementById("cep");

cepInput.addEventListener("blur", buscarCep);

async function buscarCep() {

    const cep = cepInput.value.replace(/\D/g, "");

    if (cep.length !== 8) {
        return;
    }

    try {

        const resposta = await fetch(
            `https://viacep.com.br/ws/${cep}/json/`
        );

        const dados = await resposta.json();

        if (dados.erro) {
            alert("CEP não encontrado.");
            return;
        }

        document.getElementById("logradouro").value =
            dados.logradouro || "";

        document.getElementById("bairro").value =
            dados.bairro || "";

        document.getElementById("cidade").value =
            dados.localidade || "";

        document.getElementById("estado").value =
            dados.uf || "";

    } catch (erro) {

        console.error("Erro ao consultar o CEP:", erro);

        alert("Não foi possível consultar o CEP.");
    }
}