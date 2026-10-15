//finalizar pedido

document.getElementById('registrar_pedido').addEventListener('click', registrar_pedido)

function registrar_pedido(event){
    event.preventDefault();
    document.getElementById('confirmacao_pedido').style.display = "flex";
}

document.getElementById('cancelar_pedido').addEventListener('click', cancelar_pedido)

function cancelar_pedido(event){
    event.preventDefault();
    document.getElementById('confirmacao_pedido').style.display = "none";
}