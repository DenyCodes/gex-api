import logging
import hashlib
import time
import requests
import json
import traceback
from django.conf import settings
from django.utils import timezone
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
    def _build_contents(products):
        """Monta o array 'contents' no formato exigido pela Meta CAPI."""
        if not products or not isinstance(products, list):
            return []
        contents = []
        for item in products:
            if isinstance(item, dict):
                entry = {}
                entry['id'] = str(item.get('id') or item.get('sku') or item.get('name', ''))
                entry['quantity'] = int(item.get('quantity', 1))
                price = item.get('item_price') or item.get('price', 0)
                try:
                    entry['item_price'] = float(price)
                except (ValueError, TypeError):
                    entry['item_price'] = 0.0
                contents.append(entry)
        return contents

    @staticmethod
    def send(event_model: CapiEvent, lead: Lead, amount=0.0, test_code=None,
             external_id=None, products=None, currency='BRL', order_id=None,
             content_name=None):
        """
        Envia o evento para a Meta Conversions API (CAPI).
        Segue as specs: https://developers.facebook.com/docs/marketing-api/conversions-api
        """

        if not FB_ACCESS_TOKEN or not FB_PIXEL_ID:
            logger.error("Credenciais do Facebook (settings.py) estão vazias.")
            return {"error": "Missing credentials"}

        # 1. USER DATA — Máximo de campos para melhor Event Match Quality
        user_data = {
            "em": [FacebookCAPIService.hash_data(lead.email)],
            "ph": [FacebookCAPIService.hash_data(lead.phone)],
            "fn": [FacebookCAPIService.hash_data(lead.first_name)],
            "ln": [FacebookCAPIService.hash_data(lead.last_name)],
            "zp": [FacebookCAPIService.hash_data(lead.zip_code)],
            "ct": [FacebookCAPIService.hash_data(lead.city)],
            "st": [FacebookCAPIService.hash_data(lead.state)],
            "country": [FacebookCAPIService.hash_data('br')],
            "client_ip_address": event_model.ip_address,
            "client_user_agent": event_model.user_agent,
            "fbp": lead.fbp,
            "fbc": lead.fbc,
            "external_id": [FacebookCAPIService.hash_data(external_id)] if external_id else [],
        }

        # Limpeza de chaves vazias/nulas
        user_data = {k: v for k, v in user_data.items() if v and (isinstance(v, list) and v[0] or not isinstance(v, list))}

        # 2. CUSTOM DATA — Completo conforme specs da Meta
        custom_data = {
            "currency": currency or "BRL",
            "value": float(amount) if amount else 0.0,
        }

        # contents: array de produtos com id, quantity, item_price
        contents = FacebookCAPIService._build_contents(products)
        if contents:
            custom_data["contents"] = contents
            custom_data["content_type"] = "product"
            custom_data["num_items"] = sum(c.get('quantity', 1) for c in contents)
        elif products and isinstance(products, list):
            # Fallback: content_ids se não tiver dados completos
            content_ids = [str(p.get('id') or p.get('name', '')) for p in products if isinstance(p, dict)]
            if content_ids:
                custom_data["content_ids"] = content_ids
                custom_data["content_type"] = "product"

        if order_id:
            custom_data["order_id"] = str(order_id)

        if content_name:
            custom_data["content_name"] = str(content_name)

        # 3. SERVER EVENT
        event_payload = {
            "event_name": event_model.event_name,
            "event_time": int(time.time()),
            "action_source": "website",
            "event_source_url": event_model.source_url,
            "user_data": user_data,
            "custom_data": custom_data,
            "event_id": event_model.event_id,
        }

        payload = {"data": [event_payload]}

        if test_code:
            payload["test_event_code"] = test_code

        try:
            url = f"https://graph.facebook.com/v21.0/{FB_PIXEL_ID}/events?access_token={FB_ACCESS_TOKEN}"

            logger.info(f"Meta CAPI: {event_model.event_name} | R$ {amount} | order_id={order_id}")

            response = requests.post(url, json=payload, timeout=10)
            response_data = response.json()

            if response.status_code == 200:
                event_model.fb_status = 'SENT'
                logger.info(f"Meta CAPI SENT: {event_model.event_id}")
            else:
                event_model.fb_status = 'ERROR'
                logger.error(f"Meta CAPI ERROR {response.status_code}: {response_data}")

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
    BACKEND INTELIGENTE: Limpa dados, Salva Lead (com classificação) e Envia CAPI.
    """
    try:
        print("\n--- INICIANDO PROCESSAMENTO INTELIGENTE (BACKEND) ---")
        
        # 1. ESTRATÉGIA DE PRIORIDADE (FALLBACK)
        raw_email = (data.get('email') or data.get('customer_email') or data.get('client_email') or data.get('customer', {}).get('email'))
        raw_phone = (data.get('shipping_phone') or data.get('billing_phone') or data.get('customer_phone') or data.get('phone') or data.get('customer', {}).get('phone'))
        
        # Captura a classificação de origem (Lead vs Abandono)
        lead_source = data.get('lead_source', 'lead')

        raw_first_name = (data.get('shipping_first_name') or data.get('billing_first_name') or data.get('first_name') or data.get('customer', {}).get('first_name'))
        raw_last_name = (data.get('shipping_last_name') or data.get('billing_last_name') or data.get('last_name') or data.get('customer', {}).get('last_name'))
        
        raw_zip = data.get('shipping_zip') or data.get('billing_zip') or data.get('zip_code')
        raw_city = data.get('city') or data.get('billing_city') or data.get('shipping_city')
        raw_state = data.get('state') or data.get('billing_state') or data.get('shipping_state')

        # 2. LIMPEZA (NORMALIZAÇÃO)
        email = DataNormalizer.normalize_email(raw_email)
        phone = DataNormalizer.normalize_phone(raw_phone)
        
        if not raw_first_name:
             full_name = data.get('name') or data.get('client_name') or data.get('customer', {}).get('name')
             first_name, last_name = DataNormalizer.split_name(full_name)
        else:
             first_name = raw_first_name
             last_name = raw_last_name

        raw_val = data.get('value') or data.get('order_amount') or data.get('total_price') or 0
        amount = DataNormalizer.normalize_amount(raw_val)
        if amount and amount > 10000: amount = amount / 100.0

        if not email: 
            print(f"❌ ERRO: Nenhum email válido encontrado.")
            return {"status": "error", "detail": "Email required"}

        # 3. UPSERT LEAD (Salva no Banco com a Classificação)
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
                'lead_source': lead_source, 
                'updated_at': timezone.now()
            }
        )

        # 4. DEFINIÇÃO DO EVENTO
        raw_type = str(data.get('event_type', '')).lower()
        status_cp = str(data.get('status', '')).lower()
        financial_status = str(data.get('financial_status', '')).lower()

        if 'purchase' in raw_type or 'paid' in status_cp or financial_status == 'paid':
            event_name = 'Purchase'
        elif 'cart' in raw_type or 'abandono' in raw_type or lead_source == 'abandonment':
            event_name = 'InitiateCheckout'
        else:
            event_name = 'Lead'

        # 4.1. CRIAR/ATUALIZAR ORDER (para compras)
        if event_name == 'Purchase':
            cartpanda_id = (data.get('cartpanda_id') or data.get('order_id') or
                           data.get('id') or data.get('unique_key'))
            if cartpanda_id:
                products = data.get('products', [])
                if isinstance(products, str):
                    product_name = data.get('product_name') or data.get('product', '')
                    products = [{'name': product_name}] if product_name else []

                Order.objects.update_or_create(
                    cartpanda_id=str(cartpanda_id),
                    defaults={
                        'lead': lead,
                        'status': status_cp or financial_status or 'paid',
                        'amount': amount or 0,
                        'currency': data.get('currency', 'BRL'),
                        'products': products,
                        'payment_method': data.get('payment_method') or data.get('gateway', ''),
                    }
                )
                print(f"📦 ORDER criada/atualizada: {cartpanda_id} - R$ {amount}")

        # 5. DEDUPLICAÇÃO
        order_id = data.get('order_id') or data.get('id') or data.get('unique_key')
        
        if order_id:
            event_id = f"order_{order_id}"
            external_id = str(order_id)
        else:
            event_id = f"evt_{int(time.time())}_{lead.id}"
            external_id = str(lead.id)

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

        # 7. PREPARAR DADOS DE PRODUTO PARA CAPI
        products = data.get('products', [])
        if not products or not isinstance(products, list):
            product_name = data.get('product_name') or data.get('product', '')
            if product_name:
                products = [{'id': product_name, 'name': product_name, 'quantity': 1, 'item_price': float(amount or 0)}]

        content_name = data.get('product_name') or data.get('product', '')
        currency = data.get('currency', 'BRL')

        test_code = data.get('test_event_code')

        fb_resp = FacebookCAPIService.send(
            event_model=capi_event,
            lead=lead,
            amount=amount,
            test_code=test_code,
            external_id=external_id,
            products=products,
            currency=currency,
            order_id=order_id,
            content_name=content_name,
        )

        return {
            "status": "success",
            "lead_id": str(lead.id),
            "source": lead_source,
            "event": event_name,
            "fb_status": fb_resp.get('status', 'unknown')
        }

    except Exception as e:
        logger.error(f"Erro process_event: {e}")
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}