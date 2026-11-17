document.addEventListener("DOMContentLoaded", function () {
    // Contador de caracteres da descrição
    var descricao = document.getElementById("descricao");
    var contador = document.getElementById("contador");

    if (descricao && contador) {
        var atualizar = function () {
            contador.textContent = descricao.value.length + " de 3000 caracteres";
        };
        descricao.addEventListener("input", atualizar);
        atualizar();
    }

    // Confirmação antes de excluir
    var formsExcluir = document.querySelectorAll(".form-excluir");
    formsExcluir.forEach(function (form) {
        form.addEventListener("submit", function (evento) {
            var mensagem = form.getAttribute("data-confirmar") || "Tem certeza que deseja excluir?";
            if (!window.confirm(mensagem)) {
                evento.preventDefault();
            }
        });
    });
});