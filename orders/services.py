import logging
import hashlib
import time
import requests
import json
import traceback
from django.conf import settings
from .models import Lead, Order, CapiEvent
# Importamos o normalizador para limpar telefones e emails
from .data_transformers import DataNormalizer 

logger = logging.getLogger(__name__)

FB_ACCESS_TOKEN = getattr(settings, 'FACEBOOK_ACCESS_TOKEN', None)
FB_PIXEL_ID = getattr(settings, 'FACEBOOK_PIXEL_ID', None)

class FacebookCAPIService:
    @staticmethod
    def hash_data(data):
        """Normaliza e cria o Hash SHA256 exigido pelo Facebook"""
        if not data: 
            return None
        # Remove espaços, converte para minúsculo e gera hash
        clean_data = str(data).strip().lower()
        return hashlib.sha256(clean_data.encode('utf-8')).hexdigest()

    @staticmethod
    def send(event_model: CapiEvent, lead: Lead, amount=0.0, test_code=None, external_id=None):
        """Envia o evento gravado no banco para a API do Facebook"""
        
        if not FB_ACCESS_TOKEN or not FB_PIXEL_ID: 
            logger.error("Credenciais do Facebook não configuradas.")
            return {"error": "Missing credentials"}

        # 1. Monta os User Data (Dados do Cliente)
        user_data = {
            "em": [FacebookCAPIService.hash_data(lead.email)],
            "ph": [FacebookCAPIService.hash_data(lead.phone)],
            "fn": [FacebookCAPIService.hash_data(lead.first_name)],
            "ln": [FacebookCAPIService.hash_data(lead.last_name)],
            "zp": [FacebookCAPIService.hash_data(lead.zip_code)],
            "ct": [FacebookCAPIService.hash_data(lead.city)],
            "st": [FacebookCAPIService.hash_data(lead.state)],
            "country": [FacebookCAPIService.hash_data('br')], # Assumindo BR se não tiver
            
            # IDs Técnicos
            "client_ip_address": event_model.ip_address,
            "client_user_agent": event_model.user_agent,
            "fbp": lead.fbp,
            "fbc": lead.fbc,
            
            # NOVO: Identificação Externa (Aumenta +18% na qualidade)
            "external_id": [FacebookCAPIService.hash_data(external_id)] if external_id else []
        }
        
        # Remove chaves com valores vazios/nulos/listas vazias
        user_data = {k: v for k, v in user_data.items() if v and (isinstance(v, list) and v[0] or not isinstance(v, list))}

        # 2. Monta o Payload do Evento
        event_payload = {
            "event_name": event_model.event_name,
            "event_time": int(time.time()),
            "action_source": "website",
            "event_source_url": event_model.source_url,
            "user_data": user_data,
            "custom_data": {
                "currency": "BRL",
                "value": float(amount),
            },
            "event_id": event_model.event_id # Essencial para DEDUPLICAÇÃO
        }

        # 3. Empacota para envio
        payload = {
            "data": [event_payload],
        }
        
        if test_code:
            payload["test_event_code"] = test_code
            print(f"--> ENVIANDO COM MODO TESTE: {test_code}")

        try:
            # 4. Disparo HTTP Post
            url = f"https://graph.facebook.com/v19.0/{FB_PIXEL_ID}/events?access_token={FB_ACCESS_TOKEN}"
            
            print(f"Enviando request para Meta: {event_model.event_name} - R$ {amount}")
            response = requests.post(url, json=payload, timeout=10)
            
            response_data = response.json()

            # 5. Atualiza o status no Supabase
            if response.status_code == 200:
                event_model.fb_status = 'SENT'
                print("--> SUCESSO META!")
            else:
                event_model.fb_status = 'ERROR'
                print(f"--> ERRO META: {response.status_code} - {response_data}")

            event_model.fb_response = response_data
            event_model.payload = payload 
            event_model.save()
            
            return response_data

        except Exception as e:
            logger.error(f"Erro de conexão com Meta: {e}")
            event_model.fb_status = 'ERROR'
            event_model.fb_response = {"error": str(e)}
            event_model.save()
            return {"error": str(e)}

def process_event(data):
    """
    BACKEND INTELIGENTE:
    Recebe dados brutos de várias fontes (Shipping, Billing, Customer),
    decide qual é o melhor dado, limpa e envia.
    """
    try:
        print("\n--- INICIANDO PROCESSAMENTO INTELIGENTE (BACKEND) ---")
        
        # 1. ESTRATÉGIA DE PRIORIDADE (FALLBACK)
        
        # Email: Email direto > Customer Email > Client Email
        raw_email = (
            data.get('email') or 
            data.get('customer_email') or 
            data.get('client_email') or 
            data.get('customer', {}).get('email')
        )
        
        # Telefone: Entrega > Cobrança > Cadastro > Genérico
        raw_phone = (
            data.get('shipping_phone') or 
            data.get('billing_phone') or 
            data.get('customer_phone') or 
            data.get('phone') or
            data.get('customer', {}).get('phone')
        )
        
        # Nome: Entrega > Cobrança > Cadastro
        raw_first_name = (
            data.get('shipping_first_name') or 
            data.get('billing_first_name') or 
            data.get('first_name') or
            data.get('customer', {}).get('first_name')
        )
        
        raw_last_name = (
            data.get('shipping_last_name') or 
            data.get('billing_last_name') or 
            data.get('last_name') or
            data.get('customer', {}).get('last_name')
        )
        
        # CEP: Entrega > Cobrança > Genérico
        raw_zip = data.get('shipping_zip') or data.get('billing_zip') or data.get('zip_code')
        
        # Cidade/Estado (Adicionado Billing/Cobrança na prioridade)
        raw_city = data.get('city') or data.get('billing_city') or data.get('shipping_city')
        raw_state = data.get('state') or data.get('billing_state') or data.get('shipping_state')

        # 2. LIMPEZA (NORMALIZAÇÃO)
        email = DataNormalizer.normalize_email(raw_email)
        phone = DataNormalizer.normalize_phone(raw_phone)
        
        # Tratamento de Nome
        if not raw_first_name:
             full_name = data.get('name') or data.get('client_name') or data.get('customer', {}).get('name')
             first_name, last_name = DataNormalizer.split_name(full_name)
        else:
             first_name = raw_first_name
             last_name = raw_last_name

        # Tratamento de Valor 
        raw_val = data.get('value') or data.get('order_amount') or data.get('total_price') or 0
        amount = DataNormalizer.normalize_amount(raw_val)
        
        # Correção específica de centavos
        if amount and amount > 10000: 
            amount = amount / 100.0

        # Validação Final Obrigatória
        if not email: 
            print(f"❌ ERRO: Nenhum email válido encontrado nos dados brutos: {data}")
            return {"status": "error", "detail": "Email required (All sources failed)"}

        # 3. UPSERT LEAD (Salva no Banco com dados limpos)
        lead, created = Lead.objects.update_or_create(
            email=email,
            defaults={
                'phone': phone, 
                'first_name': first_name,
                'last_name': last_name,
                'zip_code': DataNormalizer.normalize_amount(raw_zip),
                'city': raw_city,
                'state': raw_state,
                'fbp': data.get('fbp'), 
                'fbc': data.get('fbc'),
            }
        )

        # 4. DEFINIÇÃO DO EVENTO
        raw_type = str(data.get('event_type', '')).lower()
        status_cp = str(data.get('status', '')).lower()
        
        if 'purchase' in raw_type or 'paid' in status_cp:
            event_name = 'Purchase'
        elif 'cart' in raw_type or 'abandono' in raw_type:
            event_name = 'InitiateCheckout'
        else:
            event_name = 'Lead'

        # 5. DEDUPLICAÇÃO E EXTERNAL ID
        order_id = data.get('order_id') or data.get('id') or data.get('unique_key')
        
        if order_id:
            event_id = f"order_{order_id}"
            external_id = str(order_id) # Usa ID do pedido como External ID
        else:
            event_id = f"evt_{int(time.time())}_{lead.id}"
            external_id = str(lead.id) # Usa ID interno como External ID (fallback)

        # 6. SALVA LOG E ENVIA
        capi_event = CapiEvent.objects.create(
            lead=lead,
            event_name=event_name,
            event_id=event_id,
            user_agent=data.get('user_agent') or data.get('client_user_agent'),
            ip_address=data.get('ip_address') or data.get('client_ip_address'),
            source_url=data.get('source_url') or data.get('event_source_url'),
            fb_status='PENDING'
        )

        test_code = data.get('test_event_code')
        
        # Agora passamos o external_id
        fb_resp = FacebookCAPIService.send(
            capi_event, 
            lead, 
            amount, 
            test_code=test_code, 
            external_id=external_id
        )

        return {
            "status": "success",
            "lead_id": str(lead.id),
            "event_id": str(capi_event.id),
            "fb_status": fb_resp.get('status', 'unknown')
        }

    except Exception as e:
        logger.error(f"Erro process_event: {e}")
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}