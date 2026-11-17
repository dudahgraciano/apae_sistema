document.addEventListener("DOMContentLoaded", function () {
    // Mostrar / ocultar senha
    var botaoVer = document.getElementById("verSenha");
    var campoSenha = document.getElementById("senha");

    if (botaoVer && campoSenha) {
        botaoVer.addEventListener("click", function () {
            var visivel = campoSenha.type === "text";
            campoSenha.type = visivel ? "password" : "text";
            botaoVer.textContent = visivel ? "Mostrar" : "Ocultar";
            botaoVer.setAttribute("aria-pressed", visivel ? "false" : "true");
            botaoVer.setAttribute("aria-label", visivel ? "Mostrar senha" : "Ocultar senha");
        });
    }

    // Menu lateral no celular
    var menu = document.getElementById("menu");
    var botaoMenu = document.getElementById("menuBotao");

    if (menu && botaoMenu) {
        botaoMenu.addEventListener("click", function () {
            var aberto = menu.classList.toggle("aberto");
            botaoMenu.textContent = aberto ? "Fechar" : "Menu";
        });
    }

    // Evita envio duplicado: depois do primeiro clique o botão fica em "Aguarde".
    document.querySelectorAll("form").forEach(function (form) {
        if (form.id === "formEnvio" || form.classList.contains("form-excluir")) { return; }
        form.addEventListener("submit", function () {
            var botao = form.querySelector("button[type=submit]");
            if (botao && !botao.disabled) {
                botao.dataset.textoOriginal = botao.textContent;
                botao.textContent = "Aguarde…";
                setTimeout(function () { botao.disabled = true; }, 0);
            }
        });
    });

    // Se o usuário voltar pela seta do navegador, os botões voltam ao normal.
    window.addEventListener("pageshow", function (evento) {
        if (!evento.persisted) { return; }
        document.querySelectorAll("button[data-texto-original]").forEach(function (botao) {
            botao.textContent = botao.dataset.textoOriginal;
            botao.disabled = false;
        });
    });
});