# agent_sales/models.py

from django.db import models
import uuid

class Evento(models.Model):
    """
    Armazena os detalhes de cada evento (shows, peças, jogos) cadastrado no sistema.
    A IA consultará esta tabela para informar preços, horários e vagas aos clientes.
    """
    nome = models.CharField(max_length=200, verbose_name="Nome do Evento")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição do Evento")
    data_horario = models.DateTimeField(verbose_name="Data e Horário do Evento")
    local = models.CharField(max_length=250, verbose_name="Local do Evento")
    
    # Preço unitário do ingresso para este evento específico
    preco_base = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Base (R$)")
    
    # Controle de estoque de ingressos
    vagas_totais = models.PositiveIntegerField(verbose_name="Capacidade Máxima de Vagas")
    vagas_disponiveis = models.PositiveIntegerField(verbose_name="Vagas Ainda Disponíveis")
    
    # Permite desativar um evento manualmente sem precisar deletá-lo do histórico do banco
    ativo = models.BooleanField(default=True, verbose_name="Evento Ativo para Vendas")

    def __str__(self):
        # Exibe o nome do evento ao invés de 'Evento Object (1)' no painel admin
        return self.nome

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"


class Pedido(models.Model):
    """
    Controla o fluxo financeiro e o status de cada transação de compra iniciada pelo cliente via IA.
    """
    STATUS_CHOICES = [
        ('PENDENTE', 'Aguardando Pagamento'),
        ('PAGO', 'Pago / Confirmado'),
        ('CANCELADO', 'Cancelado / Expirado'),
    ]
    
    # Identificadores do cliente vindos do canal de atendimento (Ex: WhatsApp)
    cliente_whatsapp = models.CharField(max_length=30, verbose_name="WhatsApp do Comprador")
    cliente_nome = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nome Fornecido pelo Cliente")
    
    # Relacionamento: Se o evento for deletado, impede a remoção caso existam pedidos atrelados (PROTECT)
    evento = models.ForeignKey(Evento, on_delete=models.PROTECT, verbose_name="Evento Selecionado")
    
    quantidade = models.PositiveIntegerField(default=1, verbose_name="Quantidade de Ingressos")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total da Compra (R$)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', verbose_name="Status do Pedido")
    
    # Armazena o ID retornado pela API do gateway de pagamento (Mercado Pago, Efí, etc.) para conciliação via Webhook
    id_transacao_pagamento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Código da Transação na API")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora da Criação")

    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente_whatsapp} ({self.status})"

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"


class BilheteEletronico(models.Model):
    """
    O ingresso digital gerado e enviado ao cliente após a confirmação do pagamento do Pedido.
    Utiliza UUID para garantir que cada ingresso tenha um identificador único impossível de fraudar.
    """
    # Se o pedido for cancelado ou deletado do sistema, remove os bilhetes vinculados em cascata (CASCADE)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="bilhetes", verbose_name="Pedido de Origem")
    
    # Gera um hash único no padrão UUID4 (Ex: 4b2b8c2d-1a2b...) para servir de QR Code ou código verificador
    codigo_unico = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Código de Validação Único")
    
    # Controle de portaria para checar se o ingresso já deu entrada no evento
    utilizado = models.BooleanField(default=False, verbose_name="Ingresso Já Utilizado?")
    data_utilizacao = models.DateTimeField(blank=True, null=True, verbose_name="Data/Hora da Entrada")

    def __str__(self):
        return f"Bilhete {self.codigo_unico} - Pedido #{self.pedido.id}"

    class Meta:
        verbose_name = "Bilhete Eletrônico"
        verbose_name_plural = "Bilhetes Eletrônicos"


class HistoricoConversaIA(models.Model):
    """
    Garante a persistência da 'memória de contexto' da IA. Guarda o histórico estruturado
    em formato JSON para que o agente saiba o que foi conversado em turnos anteriores com cada número.
    """
    # Cada número de WhatsApp tem apenas um registro de histórico de conversa ativo no banco
    cliente_whatsapp = models.CharField(max_length=30, unique=True, verbose_name="WhatsApp do Cliente")
    
    # Campo JSON para armazenar a lista de mensagens no padrão da OpenAI: [{"role": "user", "content": "..."}, ...]
    historico_json = models.JSONField(default=list, verbose_name="Histórico da Conversa em JSON")
    ultima_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Última Mensagem Trocada")

    def __str__(self):
        return f"Memória IA: {self.cliente_whatsapp}"

    class Meta:
        verbose_name = "Histórico de Conversa da IA"
        verbose_name_plural = "Históricos de Conversa da IA"