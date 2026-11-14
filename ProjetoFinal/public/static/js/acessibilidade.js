// Lembra as escolhas de tema e daltonismo entre as páginas
/*
    Acessibilidade
    Tema escuro e daltonismo ficam no CSS (style2.css). Aqui só:
    1. lembra a escolha entre as páginas (localStorage)
    2. fecha o painel com Esc ou clicando fora
    Sem JavaScript tudo funciona na página atual, só não lembra a escolha.
*/
(function () {
    "use strict";

    var raiz = document.documentElement;
    var CHAVE_TEMA = "saborclic-tema";
    var CHAVE_DALTONISMO = "saborclic-daltonismo";

    // Lê um valor salvo no navegador
    function ler(chave) {
        try { return localStorage.getItem(chave); } catch (e) { return null; }
    }

    // Salva (ou apaga) um valor no navegador
    function gravar(chave, valor) {
        try {
            if (valor === null) { localStorage.removeItem(chave); }
            else { localStorage.setItem(chave, valor); }
        } catch (e) { /* armazenamento bloqueado: segue sem memória */ }
    }

    // Aplica a escolha salva no <html> (roda antes da página ser desenhada).
    function aplicar() {
        var tema = ler(CHAVE_TEMA);
        var filtro = ler(CHAVE_DALTONISMO);

        if (tema === "escuro") { raiz.setAttribute("data-tema", "escuro"); }
        else { raiz.removeAttribute("data-tema"); }

        if (filtro && filtro !== "nenhum") { raiz.setAttribute("data-daltonismo", filtro); }
        else { raiz.removeAttribute("data-daltonismo"); }
    }

    aplicar();

    document.addEventListener("DOMContentLoaded", function () {
        var widget = document.querySelector("[data-a11y]");
        if (!widget) { return; }

        // Marca no painel as opções que estão salvas.
        var tema = ler(CHAVE_TEMA) || "claro";
        var filtro = ler(CHAVE_DALTONISMO) || "nenhum";

        var radioTema = widget.querySelector('input[name="a11y-tema"][value="' + tema + '"]');
        var radioFiltro = widget.querySelector('input[name="a11y-daltonismo"][value="' + filtro + '"]');
        if (radioTema) { radioTema.checked = true; }
        if (radioFiltro) { radioFiltro.checked = true; }

        // Guarda a opção escolhida.
        widget.addEventListener("change", function (evento) {
            var campo = evento.target;
            if (campo.name === "a11y-tema") { gravar(CHAVE_TEMA, campo.value); }
            if (campo.name === "a11y-daltonismo") { gravar(CHAVE_DALTONISMO, campo.value); }
            aplicar();
        });

        // "Restaurar padrão": o navegador volta os radios, aqui limpamos a memória.
        widget.addEventListener("reset", function () {
            gravar(CHAVE_TEMA, null);
            gravar(CHAVE_DALTONISMO, null);
            setTimeout(aplicar, 0);
        });

        // Esc fecha o painel e devolve o foco ao botão.
        widget.addEventListener("keydown", function (evento) {
            if (evento.key === "Escape" && widget.open) {
                widget.open = false;
                widget.querySelector("summary").focus();
            }
        });

        // Clique fora fecha o painel.
        document.addEventListener("click", function (evento) {
            if (widget.open && !widget.contains(evento.target)) { widget.open = false; }
        });
    });
})();
