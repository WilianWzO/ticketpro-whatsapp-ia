# agent_sales/admin.py

from django.contrib import admin
from .models import Evento, Pedido, BilheteEletronico, HistoricoConversaIA

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    # Colunas que aparecerão na tabela de listagem de eventos
    list_display = ('nome', 'data_horario', 'local', 'preco_base', 'vagas_disponiveis', 'ativo')
    # Barra lateral de filtros para agilizar a navegação do administrador
    list_filter = ('ativo', 'data_horario')
    # Permite buscar eventos digitando parte do nome ou do local na barra de busca
    search_fields = ('nome', 'local')

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente_whatsapp', 'evento', 'quantidade', 'valor_total', 'status', 'criado_em')
    list_filter = ('status', 'criado_em')
    search_fields = ('cliente_whatsapp', 'cliente_nome')

@admin.register(BilheteEletronico)
class BilheteEletronicoAdmin(admin.ModelAdmin):
    list_display = ('codigo_unico', 'pedido', 'utilizado', 'data_utilizacao')
    list_filter = ('utilizado',)
    # Permite buscar o bilhete pelo UUID completo ou pelo número do cliente associado ao pedido
    search_fields = ('codigo_unico', 'pedido__cliente_whatsapp')

@admin.register(HistoricoConversaIA)
class HistoricoConversaIAAdmin(admin.ModelAdmin):
    list_display = ('cliente_whatsapp', 'ultima_atualizacao')
    search_fields = ('cliente_whatsapp',)