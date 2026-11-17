// Configuração Supabase (Usando a chave anônima publicável e proxy Vercel para estabilidade de rede)
let supabaseUrl = 'https://wkmbkipygdjinlezlftt.supabase.co';

// Se estiver em produção (não-local), usa o proxy da Vercel para evitar bloqueios de provedores/firewalls
if (window.location.protocol.startsWith('http') && window.location.hostname !== '127.0.0.1' && window.location.hostname !== 'localhost') {
    supabaseUrl = window.location.origin + '/supabase';
}

const supabaseKey = 'sb_publishable__ArqbbdwN_zbCqkrRDcPXA_ZEKrmwYV';
let supabaseClient = null;

try {
    if (window.supabase && window.supabase.createClient) {
        supabaseClient = window.supabase.createClient(supabaseUrl, supabaseKey);
    } else {
        console.warn("SDK do Supabase não carregado. Verifique a conexão com a internet.");
    }
} catch (e) {
    console.error("Erro ao inicializar Supabase:", e);
}

// Utilitário para exibir mensagens de status
function showStatus(message, type = 'loading') {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.className = ''; // Reset classes
    
    let icon = '';
    if (type === 'error') {
        icon = '<i class="ph ph-warning-circle"></i>';
        statusDiv.classList.add('status-error');
    } else if (type === 'success') {
        icon = '<i class="ph ph-check-circle"></i>';
        statusDiv.classList.add('status-success');
    } else if (type === 'ai') {
        icon = '<i class="ph ph-brain ph-spin"></i>';
        statusDiv.classList.add('ai-processing');
    } else {
        icon = '<i class="ph ph-spinner-gap ph-spin"></i>';
        statusDiv.classList.add('status-loading');
    }

    statusDiv.innerHTML = icon + ' ';
    const texto = document.createElement('span');
    texto.textContent = message; // textContent: mensagem nunca é interpretada como HTML
    statusDiv.appendChild(texto);
    statusDiv.style.display = 'block';
}

function clearStatus() {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.innerHTML = '';
    statusDiv.className = '';
    statusDiv.style.display = 'none';
}

// Funções de Autenticação (Mock Seguro Básico)
window.fazerLogin = function () {
    const user = document.getElementById('userLogin').value.trim().toLowerCase();
    const pass = document.getElementById('passLogin').value.trim();

    // Verificação simples usando base64 para evitar credenciais em texto puro no código
    // admin = YWRtaW4= | 1234 = MTIzNA==
    if (btoa(user) === 'YWRtaW4=' && btoa(pass) === 'MTIzNA==') {
        const loginScreen = document.getElementById('loginScreen');
        const dashboardScreen = document.getElementById('dashboardScreen');
        
        loginScreen.classList.add('fade-out');
        
        setTimeout(() => {
            loginScreen.style.display = 'none';
            dashboardScreen.style.display = 'block';
            setTimeout(() => dashboardScreen.classList.add('fade-in'), 50);
            window.alternarPaineis();
        }, 400);
    } else {
        alert("Usuário ou senha incorretos.");
    }
}

window.sair = function () {
    const loginScreen = document.getElementById('loginScreen');
    const dashboardScreen = document.getElementById('dashboardScreen');
    
    dashboardScreen.classList.remove('fade-in');
    dashboardScreen.classList.add('fade-out');
    
    setTimeout(() => {
        dashboardScreen.style.display = 'none';
        dashboardScreen.classList.remove('fade-out');
        
        loginScreen.style.display = 'block';
        setTimeout(() => {
            loginScreen.classList.remove('fade-out');
            loginScreen.classList.add('fade-in');
        }, 50);
        
        // Limpar inputs
        document.getElementById('userLogin').value = '';
        document.getElementById('passLogin').value = '';
    }, 400);
}

// Alternância de UI baseada na categoria
window.alternarPaineis = function () {
    const cat = document.getElementById('category').value;
    
    const panels = ['boxLaboratorio', 'boxImagem', 'boxOutros'];
    panels.forEach(p => document.getElementById(p).classList.remove('active'));

    if (cat === 'Laboratoriais') {
        document.getElementById('boxLaboratorio').classList.add('active');
    } else if (cat === 'Imagem') {
        document.getElementById('boxImagem').classList.add('active');
    } else {
        document.getElementById('boxOutros').classList.add('active');
    }
    window.cancelarConferencia();
}

// Atualização de nome do arquivo no input customizado
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    
    if(fileInput && fileNameDisplay) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                fileNameDisplay.textContent = e.target.files[0].name;
            } else {
                fileNameDisplay.textContent = 'Clique para anexar PDF';
            }
            window.cancelarConferencia();
        });
    }
    
    // Botões (sem onclick no HTML, para a política de segurança bloquear scripts injetados)
    document.getElementById('btnLogin').addEventListener('click', () => window.fazerLogin());
    document.getElementById('btnSair').addEventListener('click', () => window.sair());
    document.getElementById('category').addEventListener('change', () => window.alternarPaineis());
    document.getElementById('sendBtn').addEventListener('click', () => window.sendFile());
    document.getElementById('btnAdicionarExame').addEventListener('click', () => window.adicionarExameManual());
    document.getElementById('btnCancelarConferencia').addEventListener('click', () => window.cancelarConferencia());

    // Suporte a "Enter" no login
    document.getElementById('passLogin')?.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') window.fazerLogin();
    });
});

// ---------------------------------------------------------------------------
// Conferência dos valores lidos
//
// Nada do que a leitura automática encontra vai direto para o paciente:
// o laboratório vê cada valor ao lado da linha original do PDF e confirma.
// ---------------------------------------------------------------------------

const TAMANHO_MAXIMO_PDF = 10 * 1024 * 1024; // mesmo limite da API

const CAMPOS_MANUAIS = [
    { id: 'valHemo', nome: 'Hemoglobina', uni: 'g/dL', ref: '12 - 17' },
    { id: 'valLeuco', nome: 'Leucócitos', uni: '/mm³', ref: '4000 - 11000' },
    { id: 'valGlico', nome: 'Glicose', uni: 'mg/dL', ref: '70 - 99' },
    { id: 'valPota', nome: 'Potássio', uni: 'mEq/L', ref: '3.5 - 5.1' },
];

let emConferencia = false;

function criar(tag, atributos = {}, texto = '') {
    const el = document.createElement(tag);
    Object.entries(atributos).forEach(([chave, valor]) => el.setAttribute(chave, valor));
    if (texto) el.textContent = texto;
    return el;
}

function rotuloBotao() {
    const btn = document.getElementById('sendBtn');
    const lab = document.getElementById('category').value === 'Laboratoriais';
    if (emConferencia) {
        btn.innerHTML = '<i class="ph ph-check-circle"></i> Confirmar e enviar';
    } else if (lab) {
        btn.innerHTML = '<i class="ph ph-magnifying-glass"></i> Ler PDF e conferir';
    } else {
        btn.innerHTML = '<i class="ph ph-paper-plane-tilt"></i> Enviar e Processar';
    }
}

function adicionarLinhaConferencia(dado) {
    const tr = criar('tr');
    if (dado.suspeito) tr.classList.add('linha-suspeita');

    const incluir = criar('input', { type: 'checkbox', 'aria-label': 'Incluir este exame' });
    incluir.checked = true;
    incluir.className = 'conf-incluir';
    tr.appendChild(criar('td')).appendChild(incluir);

    const tdNome = tr.appendChild(criar('td'));
    if (dado.novo) {
        tdNome.appendChild(criar('input', { type: 'text', class: 'conf-nome', placeholder: 'Nome do exame', maxlength: '60' }));
    } else {
        const nome = criar('span', { class: 'conf-nome' }, dado.nome);
        nome.dataset.nome = dado.nome;
        tdNome.appendChild(nome);
    }

    const tdValor = tr.appendChild(criar('td'));
    const valor = criar('input', { type: 'number', step: 'any', class: 'conf-valor', 'aria-label': 'Valor' });
    valor.value = dado.valor ?? '';
    tdValor.appendChild(valor);

    const tdUni = tr.appendChild(criar('td'));
    if (dado.novo) {
        tdUni.appendChild(criar('input', { type: 'text', class: 'conf-uni', placeholder: 'Unidade', maxlength: '15' }));
    } else {
        const uni = criar('span', { class: 'conf-uni' }, dado.uni || '');
        tdUni.appendChild(uni);
    }

    const tdOrigem = tr.appendChild(criar('td', { class: 'conf-origem' }));
    tdOrigem.dataset.ref = dado.ref || '';
    if (dado.origem === 'digitado') {
        tdOrigem.appendChild(criar('span', { class: 'selo selo-manual' }, 'Digitado por você'));
    } else if (dado.novo) {
        tdOrigem.appendChild(criar('span', { class: 'selo selo-manual' }, 'Adicionado por você'));
    } else {
        tdOrigem.appendChild(criar('code', {}, dado.linha || ''));
        if (dado.suspeito) {
            tdOrigem.appendChild(criar('span', { class: 'selo selo-alerta' }, 'Valor fora do esperado. Confira no laudo.'));
        }
    }

    document.getElementById('corpoConferencia').appendChild(tr);
}

function mostrarConferencia(dados, aviso) {
    const corpo = document.getElementById('corpoConferencia');
    corpo.replaceChildren();
    dados.forEach(adicionarLinhaConferencia);

    const avisoEl = document.getElementById('avisoConferencia');
    avisoEl.textContent = aviso || '';
    avisoEl.style.display = aviso ? 'block' : 'none';

    document.getElementById('boxConferencia').style.display = 'block';
    emConferencia = true;
    rotuloBotao();
}

window.adicionarExameManual = function () {
    adicionarLinhaConferencia({ novo: true });
};

window.cancelarConferencia = function () {
    const box = document.getElementById('boxConferencia');
    if (!box) return;
    box.style.display = 'none';
    document.getElementById('corpoConferencia').replaceChildren();
    emConferencia = false;
    rotuloBotao();
};

// Lê a tabela de conferência. Devolve { dados } ou { erro }.
function coletarConferencia() {
    const dados = [];
    for (const tr of document.querySelectorAll('#corpoConferencia tr')) {
        if (!tr.querySelector('.conf-incluir').checked) continue;

        const nomeEl = tr.querySelector('.conf-nome');
        const uniEl = tr.querySelector('.conf-uni');
        const nome = (nomeEl.dataset.nome || nomeEl.value || '').trim();
        const uni = (uniEl.value ?? uniEl.textContent ?? '').trim();
        const bruto = tr.querySelector('.conf-valor').value.trim();
        const valor = Number(bruto);

        if (!nome && !bruto) continue; // linha nova deixada em branco
        if (!nome) return { erro: 'Há um exame sem nome na conferência.' };
        if (!bruto || !Number.isFinite(valor)) return { erro: `Informe um valor numérico para "${nome}" ou desmarque o exame.` };

        dados.push({ nome, valor, uni, ref: tr.querySelector('.conf-origem').dataset.ref || '' });
    }
    return { dados };
}

async function lerPdfNoServidor(file) {
    const formData = new FormData();
    formData.append('file', file);
    const resposta = await fetch('/api/process-pdf', { method: 'POST', body: formData });
    if (!resposta.ok) {
        let detalhe = '';
        try { detalhe = (await resposta.json()).detail || ''; } catch { /* resposta sem JSON */ }
        throw new Error(detalhe || `Não foi possível ler o PDF (erro ${resposta.status}).`);
    }
    return resposta.json();
}

async function salvarExame({ patientId, category, file, payloadJSON }) {
    showStatus('Salvando documento de forma segura...', 'loading');

    const nomeLimpo = file.name.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-zA-Z0-9.]/g, '_');
    const fileName = `${Date.now()}_${nomeLimpo}`;

    const { error: uploadError } = await supabaseClient.storage.from('laudos').upload(fileName, file);
    if (uploadError) throw new Error('Erro ao fazer upload: ' + uploadError.message);

    const { data: urlData } = supabaseClient.storage.from('laudos').getPublicUrl(fileName);

    const { error: dbError } = await supabaseClient
        .from('exames')
        .insert([{
            paciente_id: patientId,
            url_laudo: urlData.publicUrl,
            categoria: category,
            nome_arquivo: file.name,
            dados_estruturados: payloadJSON
        }]);
    if (dbError) throw dbError;
}

function limparFormulario() {
    document.getElementById('fileInput').value = '';
    document.getElementById('fileNameDisplay').textContent = 'Clique para anexar PDF';
    document.getElementById('patientId').value = '';
    document.querySelectorAll('.json-item input').forEach(i => i.value = '');
    if (document.getElementById('pacsLink')) document.getElementById('pacsLink').value = '';
    window.cancelarConferencia();
}

// Fluxo principal de envio
window.sendFile = async function () {
    const btn = document.getElementById('sendBtn');
    let patientId = document.getElementById('patientId').value.trim();
    const category = document.getElementById('category').value;
    const file = document.getElementById('fileInput').files[0];
    const pacsUrl = document.getElementById('pacsLink') ? document.getElementById('pacsLink').value.trim() : '';

    if (!file) {
        showStatus('Anexe o laudo PDF.', 'error');
        return;
    }
    if (file.size > TAMANHO_MAXIMO_PDF) {
        showStatus('O PDF passa do limite de 10 MB.', 'error');
        return;
    }
    if (patientId && !/^\d{5,10}$/.test(patientId)) {
        showStatus('O ID do paciente deve ter só números (5 a 10 dígitos).', 'error');
        return;
    }
    if (pacsUrl && !/^https:\/\//i.test(pacsUrl)) {
        showStatus('O link do PACS precisa começar com https://', 'error');
        return;
    }
    if (!supabaseClient) {
        showStatus('Conexão com o banco de dados offline. Verifique a internet.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="ph ph-spinner-gap ph-spin"></i> Processando...';
    clearStatus();

    try {
        // ----- Exames laboratoriais: passo 2, o laboratório já conferiu -----
        if (category === 'Laboratoriais' && emConferencia) {
            if (!patientId) throw new Error('Digite o ID do paciente.');
            const { dados, erro } = coletarConferencia();
            if (erro) throw new Error(erro);

            await salvarExame({ patientId, category, file, payloadJSON: dados });
            showStatus(`Transmitido com sucesso (${dados.length} ${dados.length === 1 ? 'valor conferido' : 'valores conferidos'}).`, 'success');
            limparFormulario();
            setTimeout(() => clearStatus(), 5000);
            return;
        }

        // ----- Leitura do PDF no servidor (quando falta alguma informação) -----
        let extraido = null;
        let falhaLeitura = '';
        const precisaLer = category === 'Laboratoriais' || !patientId || (category === 'Imagem' && !pacsUrl);
        if (precisaLer) {
            showStatus('Lendo o PDF...', 'ai');
            try {
                extraido = await lerPdfNoServidor(file);
            } catch (apiError) {
                console.error('Falha ao extrair dados:', apiError);
                falhaLeitura = apiError.message;
            }
        }

        if (!patientId && extraido && extraido.patientId) {
            patientId = extraido.patientId;
            document.getElementById('patientId').value = patientId; // mostra na tela para conferência
        }

        // ----- Exames laboratoriais: passo 1, mostrar para conferência -----
        if (category === 'Laboratoriais') {
            const lidos = ((extraido && extraido.dadosClinicos) || []).filter(d => d.tipo === 'lab');
            const linhas = [];

            // O que foi digitado à mão sempre vale mais do que a leitura automática.
            const digitados = new Set();
            CAMPOS_MANUAIS.forEach(campo => {
                const valor = document.getElementById(campo.id).value.trim();
                if (valor) {
                    digitados.add(campo.nome);
                    linhas.push({ nome: campo.nome, valor, uni: campo.uni, ref: campo.ref, origem: 'digitado' });
                }
            });
            lidos.filter(d => !digitados.has(d.nome)).forEach(d => linhas.push(d));

            let aviso = '';
            if (falhaLeitura) aviso = `A leitura automática falhou (${falhaLeitura}). Adicione os valores à mão.`;
            else if (extraido && extraido.semTexto) aviso = 'Este PDF é uma imagem escaneada, sem texto para ler. Adicione os valores à mão.';
            else if (lidos.length === 0) aviso = 'Nenhum exame conhecido foi encontrado neste PDF. Adicione os valores à mão, se quiser.';
            else if (lidos.some(d => d.suspeito)) aviso = 'Há valores fora do esperado, marcados em amarelo. Confira no laudo.';

            mostrarConferencia(linhas, aviso);
            clearStatus();
            if (!patientId) showStatus('Não achei o ID do paciente no PDF. Digite antes de confirmar.', 'error');
            document.getElementById('boxConferencia').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            return;
        }

        // ----- Demais categorias -----
        if (!patientId) {
            throw new Error(falhaLeitura
                ? 'Não foi possível ler o PDF para achar o ID do paciente. Digite manualmente.'
                : "Não foi possível encontrar o 'ID do Paciente' no PDF. Digite manualmente.");
        }

        let payloadJSON = [];
        if (category === 'Imagem') {
            const pacs = ((extraido && extraido.dadosClinicos) || []).find(d => d.tipo === 'pacs');
            if (pacsUrl) {
                payloadJSON = [{ tipo: 'pacs', url: pacsUrl }];
            } else if (pacs) {
                payloadJSON = [{ tipo: 'pacs', usuario: pacs.usuario || '', senha: pacs.senha || '', url: pacs.url || '' }];
            }
        }

        await salvarExame({ patientId, category, file, payloadJSON });
        showStatus('Transmitido com sucesso!', 'success');
        limparFormulario();
        setTimeout(() => clearStatus(), 5000);

    } catch (error) {
        showStatus(error.message, 'error');
    } finally {
        btn.disabled = false;
        rotuloBotao();
    }
};
