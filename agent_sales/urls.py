# agent_sales/urls.py

from django.urls import path
from .views import WebhookMensagemView
from .openai_service import responder_cliente_com_ia
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def testar_ia_link(request):
    if request.method == 'POST':
        mensagem_usuario = request.POST.get('mensagem_usuario', '').strip()
        if not mensagem_usuario:
            mensagem_usuario = "Quais shows estão disponíveis e valores?"
        historico = request.session.get('sandbox_historico', [])
    else:
        mensagem_usuario = "Quais shows estão disponíveis e valores?"
        historico = []
        request.session['sandbox_historico'] = []

    resposta = responder_cliente_com_ia("+5527999999999", mensagem_usuario, historico)

    historico.append({"role": "user", "content": mensagem_usuario})
    historico.append({"role": "assistant", "content": resposta})
    request.session['sandbox_historico'] = historico[-10:]

    html_customizado = f"""
    <html>
        <head>
            <title>Console do Agente Virtual - TicketPro</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; background-color: #0f172a; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; box-sizing: border-box;">
            
            <div style="width: 100%; max-width: 720px; min-height: 80vh; background: #1e293b; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); display: flex; flex-direction: column; overflow: hidden; border: 1px solid #334155;">
                
                <div style="background-color: #0f172a; padding: 18px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #334155;">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div style="width: 42px; height: 42px; background: linear-gradient(135deg, #3b82f6, #1d4ed8); border-radius: 10px; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);">
                            <span style="color: white; font-weight: bold; font-size: 20px;">⚡</span>
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 16px; color: #f8fafc; letter-spacing: -0.3px;">Smart Agent Pro</div>
                            <div style="font-size: 12px; color: #10b981; margin-top: 2px; display: flex; align-items: center; gap: 5px;">
                                <span style="width: 6px; height: 6px; background-color: #10b981; border-radius: 50%; display: inline-block;"></span> 
                                Groq Engine Active
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <a href="" style="color: #94a3b8; text-decoration: none; font-size: 11px; font-weight: 600; padding: 4px 10px; border: 1px solid #334155; border-radius: 20px;">Reiniciar</a>
                        <div style="background: #334155; color: #94a3b8; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.5px;">
                            Sandbox
                        </div>
                    </div>
                </div>

                <div style="flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 20px; background-color: #0f172a;">
                    
                    <div style="align-self: flex-end; width: 100%; max-width: 85%;">
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 6px; text-align: right; font-weight: 500;">MENSAGEM RECEBIDA</div>
                        <div style="background-color: #1e293b; color: #e2e8f0; padding: 14px 18px; border-radius: 12px 12px 0px 12px; font-size: 15px; border: 1px solid #334155; line-height: 1.5; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            {mensagem_usuario}
                        </div>
                    </div>

                    <div style="align-self: flex-start; width: 100%; max-width: 95%;">
                        <div style="font-size: 11px; color: #3b82f6; margin-bottom: 6px; font-weight: 600; letter-spacing: 0.5px;">RESPOSTA DO ASSISTENTE</div>
                        <div style="background: linear-gradient(180deg, #1e293b, #1e293b); color: #f1f5f9; padding: 18px; border-radius: 12px; border-left: 4px solid #3b82f6; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 15px; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155;">
                            <pre style="font-family: inherit; font-size: inherit; white-space: pre-wrap; margin: 0; line-height: 1.6; color: #f1f5f9;">{resposta}</pre>
                        </div>
                    </div>

                </div>

                <form method="POST" action="" style="background-color: #1e293b; padding: 12px 20px; display: flex; align-items: center; gap: 12px; border-top: 1px solid #334155; margin: 0;">
                    <input type="text" name="mensagem_usuario" placeholder="" autofocus style="flex: 1; background: #0f172a; padding: 12px 16px; border-radius: 8px; font-size: 15px; color: #f8fafc; border: 1px solid #334155; outline: none;">
                    <button type="submit" style="background: #3b82f6; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 14px;">Enviar</button>
                </form>

            </div>
        </body>
    </html>
    """
    return HttpResponse(html_customizado)


app_name = 'agent_sales'

urlpatterns = [
    path('webhook/', WebhookMensagemView.as_view(), name='webhook_mensagem'),
    path('testar/', testar_ia_link, name='testar_ia'),
]