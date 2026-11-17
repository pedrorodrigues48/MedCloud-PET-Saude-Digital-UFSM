// Página de QR code: abre o site (e o download do app) direto pela câmera do celular.

const LINK_APK = 'https://github.com/tiaginhoeumesmo-oss/medcloud-app/releases/download/v1.0.0/prontuario-app.apk';

function desenharQr(canvas, texto) {
    const qr = qrcode(0, 'M'); // 0 = tamanho automático; M = tolera 15% de dano na impressão
    qr.addData(texto);
    qr.make();

    const modulos = qr.getModuleCount();
    const margem = 4; // zona de silêncio exigida pelo padrão
    const escala = Math.max(4, Math.floor(880 / (modulos + margem * 2)));
    const lado = (modulos + margem * 2) * escala;

    canvas.width = lado;
    canvas.height = lado;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, lado, lado);
    ctx.fillStyle = '#000000';
    for (let linha = 0; linha < modulos; linha++) {
        for (let coluna = 0; coluna < modulos; coluna++) {
            if (qr.isDark(linha, coluna)) {
                ctx.fillRect((coluna + margem) * escala, (linha + margem) * escala, escala, escala);
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Usa o endereço em que a página está aberta: funciona em qualquer domínio, sem configurar nada.
    const site = window.location.origin + '/';
    desenharQr(document.getElementById('qrSite'), site);
    document.getElementById('textoSite').textContent = site.replace(/^https?:\/\//, '').replace(/\/$/, '');

    desenharQr(document.getElementById('qrApp'), LINK_APK);

    document.getElementById('btnImprimir').addEventListener('click', () => window.print());
});
