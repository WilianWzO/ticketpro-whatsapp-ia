import os
import json
import uuid
import urllib.request
import urllib.error
from dotenv import load_dotenv
from .models import Evento, Pedido, BilheteEletronico

# Carrega as variáveis do arquivo .env (override=True garante que o .env sobrescreva variáveis antigas do sistema)
load_dotenv(override=True)

# Configurações da API da Groq lidas diretamente do ambiente
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"


def obter_modelo_ativo_groq() -> str:
    """
    Consulta automaticamente a API da Groq para descobrir qual modelo de linguagem
    está ativo e habilitado na sua conta, evitando erros de modelo descontinuado.
    """
    req = urllib.request.Request(
        GROQ_MODELS_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "TicketPro/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
            # Extrai a lista de IDs de todos os modelos disponíveis na conta
            ids = [m["id"] for m in dados.get("data", [])]

            # Ordem de preferência dos melhores modelos para chat e chamadas de função (tools)
            preferidos = [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "qwen/qwen3-32b",
                "meta-llama/llama-4-scout-17b-16e-instruct",
            ]
            for mod in preferidos:
                if mod in ids:
                    return mod

            # Caso nenhum dos preferidos esteja na lista, pega o primeiro modelo de texto válido
            for mid in ids:
                if "whisper" not in mid and "guard" not in mid and "tts" not in mid:
                    return mid
    except Exception:
        pass

    # Modelo padrão de fallback caso a consulta de modelos falhe por rede
    return "llama-3.1-8b-instant"


def chamar_groq_api(payload: dict) -> dict:
    """
    Envia uma requisição HTTP POST nativa (via urllib) diretamente para a API da Groq.
    Evita conflitos de biblioteca externa e garante conexão estável no Python 3.14.
    """
    dados = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROQ_URL,
        data=dados,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "TicketPro/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Captura o detalhe exato da resposta da Groq caso ocorra erro HTTP (ex: 401 ou 404)
        detalhe = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Erro Groq ({e.code}): {detalhe}")


def obter_catalogo_eventos() -> str:
    """
    Busca no banco de dados todos os eventos ativos ordenados por data_horario
    e monta o texto numerado (OPÇÃO 1, OPÇÃO 2, OPÇÃO 3...) vinculado ao ID real do banco.
    """
    eventos = Evento.objects.filter(ativo=True).order_by("data_horario")
    if not eventos.exists():
        return "Nenhum evento ativo cadastrado no momento."

    linhas = []
    # enumerate(..., start=1) numera os eventos de 1 em diante para o cliente digitar 1, 2 ou 3
    for indice, ev in enumerate(eventos, start=1):
        data_fmt = ev.data_horario.strftime("%d/%m/%Y às %H:%M") if ev.data_horario else "Data a definir"
        linhas.append(
            f"OPÇÃO {indice} (ID_BANCO={ev.id}): {ev.nome} | Data: {data_fmt} | Local: {ev.local} | "
            f"Valor: R$ {ev.preco_base:.2f} | Vagas disponíveis: {ev.vagas_disponiveis}"
        )
    return "\n".join(linhas)


def criar_pedido_no_banco(cliente_whatsapp: str, evento_id: int, quantidade: int = 1) -> dict:
    """
    Valida a disponibilidade de vagas, registra o Pedido no banco de dados,
    gera cada BilheteEletronico individual, desconta as vagas do Evento e devolve
    o comprovante formatado linha por linha.
    """
    try:
        evento = Evento.objects.get(id=evento_id, ativo=True)
    except Evento.DoesNotExist:
        return {"sucesso": False, "mensagem": "Evento não encontrado ou inativo."}

    # Verifica se há vagas suficientes antes de fechar a compra
    if evento.vagas_disponiveis < quantidade:
        return {
            "sucesso": False,
            "mensagem": f"Vagas insuficientes. Restam apenas {evento.vagas_disponiveis} vagas disponíveis.",
        }

    # Calcula o valor total e cria o registro na tabela Pedido
    valor_total = evento.preco_base * quantidade
    pedido = Pedido.objects.create(
        cliente_whatsapp=cliente_whatsapp,
        evento=evento,
        quantidade=quantidade,
        valor_total=valor_total,
        status="PAGO",
    )

    # Inspeciona os campos reais do model BilheteEletronico para preencher o código sem erro de atributo
    campos_bilhete = {f.name for f in BilheteEletronico._meta.get_fields()}
    codigos = []

    for _ in range(quantidade):
        codigo = str(uuid.uuid4())
        kwargs_bilhete = {"pedido": pedido}

        # Preenche o campo de código apenas se ele existir explicitamente no model
        for nome_campo in ("codigo", "codigo_bilhete", "token", "hash_bilhete", "codigo_validacao"):
            if nome_campo in campos_bilhete:
                kwargs_bilhete[nome_campo] = codigo
                break

        # Salva o bilhete no banco de dados
        bilhete = BilheteEletronico.objects.create(**kwargs_bilhete)

        # Recupera o identificador gerado (seja o ID autoincremento ou UUID automático do model)
        valor_exibir = codigo
        for nome_campo in ("codigo", "codigo_bilhete", "token", "uuid", "id"):
            if hasattr(bilhete, nome_campo) and getattr(bilhete, nome_campo):
                valor_exibir = str(getattr(bilhete, nome_campo))
                break
        codigos.append(valor_exibir)

    # Subtrai a quantidade comprada do estoque de vagas do evento e salva
    evento.vagas_disponiveis -= quantidade
    evento.save()

    # Monta o comprovante final com cada informação separada em sua própria linha
    data_hora_fmt = evento.data_horario.strftime("%d/%m/%Y às %H:%M") if evento.data_horario else "A definir"
    texto_ingresso = "ingresso" if quantidade == 1 else "ingressos"
    codigos_formatados = ", ".join(codigos)

    comprovante = (
        f"Pedido confirmado!\n\n"
        f"Evento: {evento.nome}\n"
        f"Quantidade: {quantidade} {texto_ingresso}\n"
        f"Data e Horário: {data_hora_fmt}\n"
        f"Local: {evento.local}\n"
        f"Valor Total: R$ {valor_total:.2f}\n"
        f"Códigos dos Bilhetes: {codigos_formatados}\n\n"
        f"Obrigado por comprar na TicketPro!"
    )

    return {"sucesso": True, "mensagem": comprovante}


# Definição da ferramenta (Function Calling) que a IA tem permissão para acionar no banco
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "criar_pedido_no_banco",
            "description": "Registra a compra de ingressos no banco de dados e gera o código do bilhete eletrônico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "evento_id": {
                        "type": "integer",
                        "description": "O valor numérico de ID_BANCO do evento escolhido pelo cliente (não confundir com o número da opção 1, 2, 3).",
                    },
                    "quantidade": {
                        "type": "integer",
                        "description": "Quantidade de ingressos solicitada pelo cliente.",
                    },
                },
                "required": ["evento_id", "quantidade"],
            },
        },
    }
]


def responder_cliente_com_ia(cliente_whatsapp: str, mensagem_usuario: str, historico_anterior=None) -> str:
    """
    Orquestra toda a conversa com o cliente:
    1. Obtém o modelo ativo da Groq e o catálogo atualizado do banco.
    2. Envia o prompt de sistema + histórico da sessão + mensagem atual para a IA.
    3. Se a IA decidir fechar a venda (tool_call), executa criar_pedido_no_banco e retorna o comprovante formatado.
    """
    if historico_anterior is None:
        historico_anterior = []

    modelo_ativo = obter_modelo_ativo_groq()
    catalogo = obter_catalogo_eventos()

    # Instruções de comportamento, formatação sem Markdown e mapeamento das opções 1, 2 e 3
    system_prompt = (
        "Você é o assistente virtual oficial da TicketPro, especializado em atendimento e venda de ingressos.\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "1. NUNCA use asteriscos (**), hashtags (#) ou formatação Markdown na resposta. Escreva apenas texto limpo.\n"
        "2. Quando o cliente perguntar sobre shows, eventos, agenda ou valores, liste TODAS as opções abaixo "
        "numeradas (1., 2., 3...), uma por linha, mostrando Nome, Data/Hora, Local e Valor de cada uma, e finalize em uma nova linha dizendo:\n"
        "   Digite o número da opção desejada (1, 2 ou 3) para escolher o evento.\n"
        "3. Se o cliente digitar apenas o número da opção (ex: '1', '2' ou '3') ou o nome do evento:\n"
        "   - '1' corresponde à OPÇÃO 1 (Stand-up Comedy)\n"
        "   - '2' corresponde à OPÇÃO 2 (Festival Vital 2026)\n"
        "   - '3' corresponde à OPÇÃO 3 (Show do Coldplay)\n"
        "   Responda com cada dado separado em sua própria linha:\n"
        "   Evento escolhido: [Nome]\n"
        "   Data e Horário: [Data/Hora]\n"
        "   Local: [Local]\n"
        "   Valor unitário: [Valor]\n"
        "   Quantos ingressos você deseja comprar?\n"
        "4. Assim que o cliente informar a quantidade de ingressos para o evento escolhido (ex: '2', '35', 'quero 2 ingressos'), "
        "chame imediatamente a função `criar_pedido_no_banco` passando o `ID_BANCO` exato daquele evento e a `quantidade`.\n\n"
        f"CATÁLOGO ATUAL DE EVENTOS DISPONÍVEIS:\n{catalogo}"
    )

    # Monta a lista de mensagens combinando regras do sistema, memória da conversa e pergunta atual
    mensagens = [{"role": "system", "content": system_prompt}]
    mensagens.extend(historico_anterior)
    mensagens.append({"role": "user", "content": mensagem_usuario})

    # Primeira chamada para a IA interpretar a intenção do cliente
    resposta = chamar_groq_api(
        {
            "model": modelo_ativo,
            "messages": mensagens,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.2,
            "max_tokens": 1000,
        }
    )

    response_message = resposta["choices"][0]["message"]

    # Verifica se a IA solicitou a execução da função de compra no banco de dados
    if response_message.get("tool_calls"):
        for tool_call in response_message["tool_calls"]:
            if tool_call["function"]["name"] == "criar_pedido_no_banco":
                args = json.loads(tool_call["function"]["arguments"])
                resultado = criar_pedido_no_banco(
                    cliente_whatsapp=cliente_whatsapp,
                    evento_id=int(args.get("evento_id")),
                    quantidade=int(args.get("quantidade", 1)),
                )
                # Retorna diretamente o comprovante já formatado linha por linha pelo Python
                return resultado["mensagem"]

    # Caso seja apenas uma resposta conversacional (listagem de shows ou confirmação da opção), retorna o texto da IA
    return response_message["content"]