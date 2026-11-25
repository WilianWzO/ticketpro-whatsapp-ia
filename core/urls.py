# core/urls.py

from django.contrib import admin
# ADICIONADO: O 'include' precisa estar importado aqui ao lado do 'path'
from django.urls import path, include

urlpatterns = [
    # Rota padrão para acessar o painel administrativo do Django
    path('admin/', admin.site.urls),
    
    # Inclui todas as rotas de venda do agente inteligente sob o prefixo '/api/sales/'
    path('api/sales/', include('agent_sales.urls')),
]