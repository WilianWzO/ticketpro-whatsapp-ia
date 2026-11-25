# agent_sales/views.py

import os
import json
import urllib.request
import urllib.error
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .models import HistoricoConversaIA
from .openai_service import responder_cliente_com_ia


def enviar_mensagem_whatsapp(telefone_destino: str, texto_resposta: str):
    """Envia a resposta gerada pela IA de volta para o WhatsApp via Meta Graph API."""
    access_token = os.getenv("WHATSAPP_TOKEN") or os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if not access_token or not phone_number_id:
        print("ERRO: WHATSAPP_TOKEN ou WHATSAPP_PHONE_NUMBER_ID não configurados no .env")
        return

    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone_destino,
        "type": "text",
        "text": {"body": texto_resposta},
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print("WhatsApp enviado com sucesso:", resp.status)
    except urllib.error.HTTPError as e:
        print("Erro ao enviar mensagem para o WhatsApp:", e.code, e.read().decode("utf-8"))


@method_decorator(csrf_exempt, name='dispatch')
class WebhookMensagemView(View):
    """
    Webhook oficial compatível com a Meta WhatsApp Cloud API e testes locais.
    """

    def get(self, request):
        """Validação do Webhook exigida pela Meta ao clicar em 'Verificar e salvar'."""
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "ticketpro_token_123")
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == verify_token:
            return HttpResponse(challenge, content_type="text/plain", status=200)

        return HttpResponse("Token de verificação inválido.", status=403)

    def post(self, request):
        try:
            dados = json.loads(request.body)

            # 1. Payload oficial da Meta WhatsApp Cloud API
            if dados.get("object") == "whatsapp_business_account":
                for entry in dados.get("entry", []):
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        mensagens = value.get("messages", [])

                        for msg in mensagens:
                            if msg.get("type") == "text":
                                whatsapp_cliente = msg.get("from")
                                mensagem_usuario = msg.get("text", {}).get("body", "")

                                memoria, _ = HistoricoConversaIA.objects.get_or_create(
                                    cliente_whatsapp=whatsapp_cliente,
                                    defaults={"historico_json": []}
                                )
                                historico_anterior = memoria.historico_json

                                resposta_ia = responder_cliente_com_ia(
                                    whatsapp_cliente, mensagem_usuario, historico_anterior
                                )

                                historico_anterior.append({"role": "user", "content": mensagem_usuario})
                                historico_anterior.append({"role": "assistant", "content": resposta_ia})
                                memoria.historico_json = historico_anterior[-20:]
                                memoria.save()

                                enviar_mensagem_whatsapp(whatsapp_cliente, resposta_ia)

                return HttpResponse("EVENT_RECEIVED", status=200)

            # 2. Compatibilidade com testes locais diretos (JSON simples)
            whatsapp_cliente = dados.get("whatsapp")
            mensagem_usuario = dados.get("mensagem")

            if not whatsapp_cliente or not mensagem_usuario:
                return JsonResponse({"erro": "Parâmetros 'whatsapp' e 'mensagem' são obrigatórios."}, status=400)

            memoria, _ = HistoricoConversaIA.objects.get_or_create(
                cliente_whatsapp=whatsapp_cliente,
                defaults={"historico_json": []}
            )
            historico_anterior = memoria.historico_json

            resposta_ia = responder_cliente_com_ia(whatsapp_cliente, mensagem_usuario, historico_anterior)

            historico_anterior.append({"role": "user", "content": mensagem_usuario})
            historico_anterior.append({"role": "assistant", "content": resposta_ia})
            memoria.historico_json = historico_anterior[-20:]
            memoria.save()

            return JsonResponse({
                "status": "sucesso",
                "cliente": whatsapp_cliente,
                "resposta_agente": resposta_ia
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido enviado na requisição."}, status=400)
        except Exception as e:
            return JsonResponse({"erro": f"Erro interno no servidor: {str(e)}"}, status=500)