document.addEventListener("DOMContentLoaded", function () {
    var botoes = Array.prototype.slice.call(document.querySelectorAll(".g-botao"));
    var lb = document.getElementById("lb");
    if (!lb || !botoes.length) { return; }

    var palco = document.getElementById("lbPalco");
    var fechar = document.getElementById("lbFechar");
    var anterior = document.getElementById("lbAnt");
    var proximo = document.getElementById("lbProx");
    var contador = document.getElementById("lbContador");
    var atividade = document.getElementById("lbAtividade");
    var meta = document.getElementById("lbMeta");
    var nome = document.getElementById("lbNome");
    var abrir = document.getElementById("lbAbrir");
    var baixar = document.getElementById("lbBaixar");
    var formExcluir = document.getElementById("lbExcluir");

    var atual = -1;
    var quemAbriu = null;
    var toqueInicial = null;

    function limparPalco() {
        var video = palco.querySelector("video");
        if (video) {
            video.pause();
            video.removeAttribute("src");
            video.load();
        }
        palco.innerHTML = "";
    }

    function mostrar(indice) {
        atual = indice;
        var item = botoes[indice];
        limparPalco();

        if (item.dataset.tipo === "video") {
            var video = document.createElement("video");
            video.controls = true;
            video.preload = "metadata";
            video.src = item.dataset.arquivo;
            palco.appendChild(video);
        } else {
            var imagem = document.createElement("img");
            imagem.alt = "Fotografia da atividade " + item.dataset.atividade;
            imagem.src = item.dataset.arquivo;
            palco.appendChild(imagem);
        }

        contador.textContent = (indice + 1) + " de " + botoes.length;
        atividade.textContent = item.dataset.atividade;
        meta.textContent = item.dataset.meta;
        nome.textContent = item.dataset.nome;
        abrir.href = item.dataset.atividadeUrl;
        baixar.href = item.dataset.baixar;

        if (item.dataset.excluir) {
            formExcluir.action = item.dataset.excluir;
            formExcluir.hidden = false;
        } else {
            formExcluir.hidden = true;
        }

        anterior.disabled = indice === 0;
        proximo.disabled = indice === botoes.length - 1;
    }

    function abrirVisualizador(indice, origem) {
        quemAbriu = origem;
        lb.hidden = false;
        document.body.classList.add("lb-aberto");
        mostrar(indice);
        fechar.focus();
    }

    function fecharVisualizador() {
        limparPalco();
        lb.hidden = true;
        document.body.classList.remove("lb-aberto");
        atual = -1;
        if (quemAbriu) { quemAbriu.focus(); }
    }

    function ir(passo) {
        var novo = atual + passo;
        if (novo >= 0 && novo < botoes.length) { mostrar(novo); }
    }

    botoes.forEach(function (botao, indice) {
        botao.addEventListener("click", function () {
            abrirVisualizador(indice, botao);
        });
    });

    fechar.addEventListener("click", fecharVisualizador);
    anterior.addEventListener("click", function () { ir(-1); });
    proximo.addEventListener("click", function () { ir(1); });

    // Clicar no fundo escuro (fora da imagem) também fecha.
    palco.addEventListener("click", function (evento) {
        if (evento.target === palco) { fecharVisualizador(); }
    });

    document.addEventListener("keydown", function (evento) {
        if (lb.hidden) { return; }

        if (evento.key === "Escape") {
            fecharVisualizador();
        } else if (evento.key === "ArrowLeft") {
            ir(-1);
        } else if (evento.key === "ArrowRight") {
            ir(1);
        } else if (evento.key === "Tab") {
            // Mantém o foco dentro do visualizador enquanto ele está aberto.
            var focaveis = Array.prototype.slice.call(
                lb.querySelectorAll("button:not([disabled]), a[href], video[controls]")
            ).filter(function (el) { return el.offsetParent !== null; });
            if (!focaveis.length) { return; }
            var primeiro = focaveis[0];
            var ultimo = focaveis[focaveis.length - 1];
            if (evento.shiftKey && document.activeElement === primeiro) {
                evento.preventDefault();
                ultimo.focus();
            } else if (!evento.shiftKey && document.activeElement === ultimo) {
                evento.preventDefault();
                primeiro.focus();
            }
        }
    });

    // Deslizar o dedo no celular
    palco.addEventListener("touchstart", function (evento) {
        toqueInicial = evento.changedTouches[0].clientX;
    }, { passive: true });

    palco.addEventListener("touchend", function (evento) {
        if (toqueInicial === null) { return; }
        var diferenca = evento.changedTouches[0].clientX - toqueInicial;
        toqueInicial = null;
        if (Math.abs(diferenca) > 60) { ir(diferenca > 0 ? -1 : 1); }
    }, { passive: true });

    // Confirmação antes de excluir
    formExcluir.addEventListener("submit", function (evento) {
        if (!window.confirm("Excluir este arquivo? Esta ação não pode ser desfeita.")) {
            evento.preventDefault();
        }
    });
});