document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("formEnvio");
    if (!form) { return; }

    var input = document.getElementById("arquivos");
    var area = document.getElementById("areaEnvio");
    var lista = document.getElementById("listaEnvio");
    var botao = document.getElementById("botaoEnviar");
    var progresso = document.getElementById("progresso");
    var barra = document.getElementById("progressoBarra");
    var textoProgresso = document.getElementById("progressoTexto");
    var mensagem = document.getElementById("envioMensagem");
    var autorizacao = document.getElementById("autorizacao");
    autorizacao.addEventListener("change", function () { atualizarLista(); });

    var LIMITE_FOTO = 15 * 1024 * 1024;
    var LIMITE_VIDEO = 300 * 1024 * 1024;
    var LIMITE_TOTAL = 512 * 1024 * 1024;
    var FOTOS = ["jpg", "jpeg", "png", "webp"];
    var VIDEOS = ["mp4", "mov", "webm"];

    var selecionados = [];
    var enviando = false;

    function extensao(nome) {
        var partes = nome.split(".");
        return partes.length > 1 ? partes.pop().toLowerCase() : "";
    }

    function formatarTamanho(bytes) {
        if (bytes >= 1024 * 1024) { return (bytes / (1024 * 1024)).toFixed(1).replace(".", ",") + " MB"; }
        return Math.max(1, Math.round(bytes / 1024)) + " KB";
    }

    function problemaDoArquivo(arquivo) {
        var ext = extensao(arquivo.name);
        if (FOTOS.indexOf(ext) !== -1) {
            if (arquivo.size > LIMITE_FOTO) { return "Fotografia acima de 15 MB."; }
        } else if (VIDEOS.indexOf(ext) !== -1) {
            if (arquivo.size > LIMITE_VIDEO) { return "Vídeo acima de 300 MB."; }
        } else {
            return "Formato não aceito.";
        }
        if (arquivo.size === 0) { return "Arquivo vazio."; }
        return "";
    }

    function mostrarMensagem(html, ehErro) {
        mensagem.hidden = false;
        mensagem.className = "envio-mensagem" + (ehErro ? " erro" : "");
        mensagem.innerHTML = html;
    }

    function escapar(texto) {
        var div = document.createElement("div");
        div.textContent = texto;
        return div.innerHTML;
    }

    function atualizarLista() {
        lista.innerHTML = "";
        var validos = 0;
        var total = 0;

        selecionados.forEach(function (arquivo, indice) {
            var problema = problemaDoArquivo(arquivo);
            if (!problema) { validos += 1; total += arquivo.size; }

            var item = document.createElement("li");
            item.className = "envio-item";

            var nome = document.createElement("span");
            nome.className = "envio-item-nome";
            nome.textContent = arquivo.name;

            var lado = document.createElement("span");
            var tamanho = document.createElement("span");
            tamanho.className = "envio-item-tamanho";
            tamanho.textContent = formatarTamanho(arquivo.size);
            var retirar = document.createElement("button");
            retirar.type = "button";
            retirar.className = "envio-item-retirar";
            retirar.textContent = "Retirar";
            retirar.disabled = enviando;
            retirar.addEventListener("click", function () {
                selecionados.splice(indice, 1);
                atualizarLista();
            });
            lado.appendChild(tamanho);
            lado.appendChild(retirar);

            item.appendChild(nome);
            item.appendChild(lado);

            if (problema) {
                var aviso = document.createElement("span");
                aviso.className = "envio-item-problema";
                aviso.textContent = problema + " Retire este arquivo para continuar.";
                item.appendChild(aviso);
            }
            lista.appendChild(item);
        });

        var todosValidos = validos === selecionados.length;
        var dentroDoLimite = total <= LIMITE_TOTAL;

        if (!dentroDoLimite) {
            mostrarMensagem("O total dos arquivos passa de 512 MB. Envie menos arquivos de cada vez.", true);
        } else if (mensagem.className.indexOf("erro") !== -1 && !enviando && selecionados.length) {
            mensagem.hidden = true;
        }

        botao.disabled = enviando || !selecionados.length || !todosValidos || !dentroDoLimite || !autorizacao.checked;        botao.textContent = selecionados.length > 1
            ? "Enviar " + selecionados.length + " arquivos"
            : "Enviar arquivos";
    }

    function adicionar(arquivos) {
        Array.prototype.forEach.call(arquivos, function (novo) {
            var repetido = selecionados.some(function (a) {
                return a.name === novo.name && a.size === novo.size && a.lastModified === novo.lastModified;
            });
            if (!repetido) { selecionados.push(novo); }
        });
        mensagem.hidden = true;
        atualizarLista();
    }

    input.addEventListener("change", function () {
        adicionar(input.files);
        input.value = "";
    });

    ["dragenter", "dragover"].forEach(function (nome) {
        area.addEventListener(nome, function (evento) {
            evento.preventDefault();
            area.classList.add("arrastando");
        });
    });
    ["dragleave", "drop"].forEach(function (nome) {
        area.addEventListener(nome, function (evento) {
            evento.preventDefault();
            area.classList.remove("arrastando");
        });
    });
    area.addEventListener("drop", function (evento) {
        if (evento.dataTransfer && evento.dataTransfer.files) {
            adicionar(evento.dataTransfer.files);
        }
    });

    form.addEventListener("submit", function (evento) {
        evento.preventDefault();
        if (enviando || !selecionados.length || !autorizacao.checked) { return; }
        var dados = new FormData();
        dados.append("csrf_token", form.querySelector("input[name=csrf_token]").value);
        dados.append("autorizacao", "1");
        selecionados.forEach(function (arquivo) { dados.append("arquivos", arquivo); });

        var xhr = new XMLHttpRequest();
        xhr.open("POST", form.action);
        xhr.setRequestHeader("X-CSRFToken", form.querySelector("input[name=csrf_token]").value);

        enviando = true;
        progresso.hidden = false;
        barra.style.width = "0%";
        textoProgresso.textContent = "0%";
        mensagem.hidden = true;
        atualizarLista();

        xhr.upload.addEventListener("progress", function (e) {
            if (e.lengthComputable) {
                var pct = Math.round((e.loaded / e.total) * 100);
                barra.style.width = pct + "%";
                textoProgresso.textContent = pct >= 100 ? "Salvando…" : pct + "%";
            }
        });

        xhr.addEventListener("load", function () {
            var resposta = {};
            try { resposta = JSON.parse(xhr.responseText); } catch (e) { resposta = {}; }

            enviando = false;

            if (xhr.status === 200) {
                if (resposta.falhas && resposta.falhas.length) {
                    var itens = resposta.falhas.map(function (f) {
                        return "<li>" + escapar(f.nome) + ": " + escapar(f.motivo) + "</li>";
                    }).join("");
                    mostrarMensagem(
                        resposta.enviados.length + " enviado(s). Estes não puderam ser enviados:<ul>" + itens + "</ul>",
                        true
                    );
                    selecionados = [];
                    progresso.hidden = true;
                    atualizarLista();
                    setTimeout(function () { window.location.href = resposta.destino; }, 4000);
                } else {
                    window.location.href = resposta.destino;
                }
                return;
            }

            var texto = resposta.erro || "Não foi possível enviar. Tente novamente.";
            if (resposta.falhas && resposta.falhas.length) {
                texto += "<ul>" + resposta.falhas.map(function (f) {
                    return "<li>" + escapar(f.nome) + ": " + escapar(f.motivo) + "</li>";
                }).join("") + "</ul>";
            } else {
                texto = escapar(texto);
            }
            if (xhr.status === 400 && resposta.falhas && resposta.falhas.length && !resposta.erro) {
                texto = "Nenhum arquivo foi enviado:" + texto.replace(/^Não foi possível enviar\. Tente novamente\./, "");
            }
            progresso.hidden = true;
            mostrarMensagem(texto, true);
            atualizarLista();
        });

        xhr.addEventListener("error", function () {
            enviando = false;
            progresso.hidden = true;
            mostrarMensagem("A conexão falhou durante o envio. Verifique a internet e tente de novo.", true);
            atualizarLista();
        });

        xhr.send(dados);
    });

    atualizarLista();
});