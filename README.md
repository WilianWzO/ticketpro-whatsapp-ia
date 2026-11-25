# 🎟️ TicketPro — Agente de Vendas Automatizado no WhatsApp com IA

Sistema backend desenvolvido em **Python** e **Django** que integra a **WhatsApp Cloud API (Meta)** a modelos de linguagem (**Groq / LLMs**) utilizando **Function Calling** para automatizar o atendimento, consulta de eventos, controle de estoque e emissão de bilhetes eletrônicos em tempo real.

## 🚀 Funcionalidades

- **Catálogo Dinâmico:** Consulta automática aos eventos ativos cadastrados no banco de dados com preços, datas, locais e vagas disponíveis.
- **Atendimento Conversacional com IA:** Interpretação natural da intenção do cliente e fluxo guiado de escolha de eventos e quantidade de ingressos.
- **Fechamento Automatizado (Function Calling):** Execução segura de funções Python no banco de dados para registrar pedidos (`Pedido`), abater vagas em tempo real e gerar códigos únicos de bilhetes (`BilheteEletronico`).
- **Integração Oficial via Webhooks:** Recebimento e envio de mensagens em tempo real através da Meta Cloud API.

## 🛠️ Tecnologias Utilizadas

- **Linguagem & Framework:** Python 3, Django
- **Inteligência Artificial:** Groq API (LLMs com suporte a Tool/Function Calling)
- **Mensageria:** WhatsApp Cloud API (Meta for Developers)
- **Banco de Dados:** SQLite (ambiente de desenvolvimento)
- **Infraestrutura Local & Segurança:** `ngrok`, `python-dotenv`, requisições HTTP nativas (`urllib`)

## ⚙️ Como Executar Localmente

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/WilianWzO/ticketpro-whatsapp-ia.git]
   cd ticketpro-whatsapp-ia
