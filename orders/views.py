import logging
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer

from .models import Order, CapiEvent, Lead
from .serializers import OrderSerializer, CapiEventSerializer, LeadSerializer
from .services import process_event

logger = logging.getLogger(__name__)

# --- Serializers inline para documentação dos Webhooks ---

WebhookRequestSerializer = inline_serializer(
    name='WebhookRequest',
    fields={
        'email': drf_serializers.EmailField(help_text='Email do cliente (obrigatório)'),
        'phone': drf_serializers.CharField(required=False, help_text='Telefone (qualquer formato, normalizado para +55)'),
        'first_name': drf_serializers.CharField(required=False, help_text='Primeiro nome'),
        'last_name': drf_serializers.CharField(required=False, help_text='Último nome'),
        'name': drf_serializers.CharField(required=False, help_text='Nome completo (alternativa a first/last_name)'),
        'order_id': drf_serializers.CharField(required=False, help_text='ID do pedido'),
        'value': drf_serializers.FloatField(required=False, help_text='Valor do pedido/carrinho'),
        'product_name': drf_serializers.CharField(required=False, help_text='Nome do produto'),
        'platform': drf_serializers.CharField(required=False, help_text='Plataforma de origem (hotmart, kiwify, cartpanda, etc.)'),
        'event_type': drf_serializers.CharField(required=False, help_text='Tipo do evento (purchase_approved, cart_abandonment, lead)'),
        'status': drf_serializers.CharField(required=False, help_text='Status do pedido (paid, pending, etc.)'),
        'fbp': drf_serializers.CharField(required=False, help_text='Cookie _fbp do Facebook Pixel'),
        'fbc': drf_serializers.CharField(required=False, help_text='Cookie _fbc do Facebook Click ID'),
        'ip_address': drf_serializers.CharField(required=False, help_text='IP do cliente'),
        'user_agent': drf_serializers.CharField(required=False, help_text='User-Agent do navegador'),
        'source_url': drf_serializers.URLField(required=False, help_text='URL de origem do evento'),
        'test_event_code': drf_serializers.CharField(required=False, help_text='Código de teste Meta CAPI (ex: TEST12345)'),
    }
)

WebhookResponseSerializer = inline_serializer(
    name='WebhookResponse',
    fields={
        'status': drf_serializers.ChoiceField(choices=['success', 'error']),
        'lead_id': drf_serializers.UUIDField(help_text='ID do lead criado/atualizado'),
        'source': drf_serializers.CharField(help_text='Classificação: lead, customer, abandonment'),
        'event': drf_serializers.CharField(help_text='Evento enviado ao Meta: Purchase, InitiateCheckout, Lead'),
        'fb_status': drf_serializers.CharField(help_text='Status do envio Meta CAPI'),
    }
)

CartPandaRequestSerializer = inline_serializer(
    name='CartPandaRequest',
    fields={
        'id': drf_serializers.IntegerField(help_text='ID do pedido CartPanda'),
        'order_number': drf_serializers.IntegerField(required=False, help_text='Número do pedido'),
        'financial_status': drf_serializers.ChoiceField(
            choices=['paid', 'pending', 'refunded', 'voided'],
            help_text='Status financeiro do pedido'
        ),
        'total_price': drf_serializers.CharField(help_text='Valor total do pedido'),
        'currency': drf_serializers.CharField(required=False, default='BRL'),
        'gateway': drf_serializers.CharField(required=False, help_text='Meio de pagamento (pix, credit_card, boleto)'),
        'customer': drf_serializers.DictField(help_text='{"email", "first_name", "last_name", "phone"}'),
        'billing_address': drf_serializers.DictField(required=False, help_text='{"zip", "city", "province_code", "phone"}'),
        'line_items': drf_serializers.ListField(help_text='[{"title", "quantity", "price"}]'),
        'topic': drf_serializers.CharField(required=False, help_text='Tipo do evento (order.paid, order.created, etc.)'),
    }
)

HealthResponseSerializer = inline_serializer(
    name='HealthResponse',
    fields={
        'status': drf_serializers.ChoiceField(choices=['healthy', 'unhealthy']),
        'database': drf_serializers.ChoiceField(choices=['connected', 'unknown']),
    }
)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

# --- VIEWSETS ---

@extend_schema(tags=['Events'])
class CapiEventViewSet(viewsets.ModelViewSet):
    """Log de eventos enviados para a Meta Conversions API (CAPI). Filtre por `fb_status` (PENDING, SENT, ERROR) ou `event_name` (Purchase, InitiateCheckout, Lead)."""
    queryset = CapiEvent.objects.all().order_by('-created_at')
    serializer_class = CapiEventSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['fb_status', 'event_name']

@extend_schema(tags=['Orders'])
class OrderViewSet(viewsets.ModelViewSet):
    """Pedidos/compras reais. Criados automaticamente quando um webhook de Purchase é processado. Filtre por `status` (paid, pending, refunded) ou `payment_method`."""
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'payment_method']

@extend_schema(tags=['Leads'])
class LeadViewSet(viewsets.ModelViewSet):
    """Leads/clientes. Criados automaticamente via webhooks. Filtre por `email` ou `lead_source` (lead, customer, abandonment)."""
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['email', 'lead_source']

# --- WEBHOOKS (Lógica de Recebimento) ---

def _handle_webhook(data, event_type_override=None, lead_source_override=None):
    """
    Função central que recebe o dado, classifica, salva e envia pro Meta.
    """
    try:
        # --- DEBUG: Ver o que está chegando ---
        # print(f"📦 PAYLOAD BRUTO: {data}") 

        # 1. Garante o tipo de evento
        if event_type_override:
            data['event_type'] = event_type_override
        
        # 2. Garante a classificação da fonte (Lead vs Abandono vs Cliente)
        if lead_source_override:
            data['lead_source'] = lead_source_override
            
        print(f"--- PROCESSANDO: {data.get('event_type')} | FONTE: {data.get('lead_source')} ---")
        
        # 3. Chama o services.py (A MÁGICA ACONTECE AQUI)
        result = process_event(data)
        
        # 4. Verifica o resultado do service
        if result.get('status') == 'error':
            # --- DEBUG DE ERRO (IMPORTANTE PARA O PURCHASE 400) ---
            print(f"❌ ERRO 400 (Services): {result}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
        print(f"✅ SUCESSO: Lead ID {result.get('lead_id')} processado.")
        return Response(result, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Erro crítico no webhook: {e}")
        # Retorna erro detalhado (ajuda no debug do Postman/Logs)
        return Response(
            {"status": "error", "detail": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    tags=['Webhooks'],
    summary='Webhook Universal',
    description=(
        'Recebe dados de **qualquer plataforma** (Hotmart, Kiwify, CartPanda, etc.) em formato bruto.\n\n'
        'A API detecta automaticamente a plataforma, normaliza os dados, cria/atualiza o Lead e envia o evento para a Meta CAPI.\n\n'
        'Ideal para integração com n8n: basta enviar `{{ $json }}` sem transformação.'
    ),
    request=WebhookRequestSerializer,
    responses={201: WebhookResponseSerializer, 400: None, 500: None},
    examples=[
        OpenApiExample(
            'Payload genérico',
            value={
                'email': 'cliente@email.com',
                'name': 'João Silva',
                'phone': '11999887766',
                'value': 149.90,
                'product_name': 'Curso de Marketing',
            },
            request_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_gex(request):
    return _handle_webhook(request.data, lead_source_override='lead')

@extend_schema(
    tags=['Webhooks'],
    summary='Webhook Abandono de Carrinho',
    description='Recebe eventos de carrinho abandonado. O Lead é classificado como `abandonment` e o evento enviado ao Meta como `InitiateCheckout`.',
    request=WebhookRequestSerializer,
    responses={201: WebhookResponseSerializer, 400: None, 500: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_cart_abandonment(request):
    return _handle_webhook(request.data, event_type_override='cart_abandonment', lead_source_override='abandonment')

@extend_schema(
    tags=['Webhooks'],
    summary='Webhook Abandono (Script JS)',
    description='Endpoint para o script JS de abandono de carrinho. Mesmo comportamento do `/cart/`.',
    request=WebhookRequestSerializer,
    responses={201: WebhookResponseSerializer, 400: None, 500: None},
)
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_abandono(request):
    return _handle_webhook(request.data, event_type_override='cart_abandonment', lead_source_override='abandonment')

@extend_schema(
    tags=['Webhooks'],
    summary='Webhook Compra Aprovada',
    description=(
        'Recebe eventos de compra aprovada (S2S/Postback). Aceita JSON no body e/ou query params.\n\n'
        'O Lead é classificado como `customer`, uma Order é criada no banco, e o evento `Purchase` é enviado ao Meta CAPI '
        'com `contents`, `order_id`, `value` e `currency` no `custom_data`.'
    ),
    request=WebhookRequestSerializer,
    responses={201: WebhookResponseSerializer, 400: None, 500: None},
)
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def webhook_purchase_approved(request):
    data = {}
    if request.data and isinstance(request.data, dict):
        data.update(request.data)
    if request.query_params:
        data.update(request.query_params.dict())
    return _handle_webhook(data, event_type_override='purchase_approved', lead_source_override='customer')

@extend_schema(
    tags=['Webhooks'],
    summary='Webhook Lead',
    description='Recebe novos leads de formulários. O Lead é classificado como `lead` e o evento enviado ao Meta como `Lead`.',
    request=WebhookRequestSerializer,
    responses={201: WebhookResponseSerializer, 400: None, 500: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_lead(request):
    return _handle_webhook(request.data, event_type_override='lead', lead_source_override='lead')

@extend_schema(
    tags=['Webhooks'],
    summary='Webhook CartPanda',
    description=(
        'Endpoint dedicado para receber webhooks da CartPanda (estrutura Shopify-like).\n\n'
        'Detecta automaticamente o tipo de evento pelo campo `financial_status` ou `topic`:\n'
        '- `paid` / `order.paid` → Purchase (cria Order + envia Meta CAPI)\n'
        '- `refunded` → Refund\n'
        '- `pending` / `order.created` → Lead\n\n'
        'Campos extraídos automaticamente: `customer`, `billing_address`, `line_items`, `total_price`, `gateway`.'
    ),
    request=CartPandaRequestSerializer,
    responses={201: WebhookResponseSerializer, 400: None, 500: None},
    examples=[
        OpenApiExample(
            'CartPanda order.paid',
            value={
                'id': 123456,
                'order_number': 1001,
                'financial_status': 'paid',
                'total_price': '149.90',
                'currency': 'BRL',
                'gateway': 'pix',
                'customer': {
                    'email': 'joao@email.com',
                    'first_name': 'João',
                    'last_name': 'Silva',
                    'phone': '11999887766',
                },
                'billing_address': {
                    'zip': '01310-100',
                    'city': 'São Paulo',
                    'province_code': 'SP',
                },
                'line_items': [
                    {'title': 'Curso de Marketing', 'quantity': 1, 'price': '149.90'}
                ],
            },
            request_only=True,
        ),
    ],
)
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def webhook_cartpanda(request):
    # Suporte a S2S Postback (GET com query params) + POST com JSON body
    data = {}
    if request.data and isinstance(request.data, dict):
        data.update(request.data)
    if request.query_params:
        data.update(request.query_params.dict())
    data['platform'] = 'cartpanda'

    # --- Mapeamento S2S Postback: nomes dos parâmetros CartPanda → nomes internos ---
    s2s_mapping = {
        'phone_number': 'phone',       # CartPanda S2S usa {phone_number}
        'product_id': 'order_id',       # CartPanda S2S usa {product_id}
        'amount_affiliate': 'affiliate_amount',
        'shop_slug': 'store',
        'datetime_unix': 'event_time',
    }
    for s2s_key, internal_key in s2s_mapping.items():
        if s2s_key in data and internal_key not in data:
            data[internal_key] = data[s2s_key]

    # S2S Postback via GET geralmente é compra aprovada — garante financial_status
    if request.method == 'GET' and not data.get('financial_status'):
        data['financial_status'] = 'paid'

    # --- Flatten dos dados aninhados do CartPanda ---
    customer = data.get('customer', {}) or {}
    billing = data.get('billing_address', {}) or {}
    shipping = data.get('shipping_address', {}) or {}
    line_items = data.get('line_items', []) or []

    # Email, phone, nome — prioridade: root > customer > billing > shipping
    if not data.get('email'):
        data['email'] = customer.get('email') or billing.get('email')
    if not data.get('phone'):
        data['phone'] = customer.get('phone') or billing.get('phone') or shipping.get('phone')
    if not data.get('first_name'):
        data['first_name'] = customer.get('first_name') or billing.get('first_name') or shipping.get('first_name')
    if not data.get('last_name'):
        data['last_name'] = customer.get('last_name') or billing.get('last_name') or shipping.get('last_name')

    # Endereço — billing > shipping
    if not data.get('zip_code'):
        data['zip_code'] = billing.get('zip') or shipping.get('zip')
    if not data.get('city'):
        data['city'] = billing.get('city') or shipping.get('city')
    if not data.get('state'):
        data['state'] = billing.get('province_code') or billing.get('province') or shipping.get('province_code')

    # Valor
    if not data.get('value'):
        data['value'] = data.get('total_price') or data.get('subtotal_price')

    # Produtos — converte line_items → products
    if line_items and not data.get('products'):
        products = []
        for item in line_items:
            if isinstance(item, dict):
                products.append({
                    'id': str(item.get('sku') or item.get('title', '')),
                    'name': item.get('title') or item.get('name', ''),
                    'quantity': item.get('quantity', 1),
                    'price': item.get('price', 0),
                    'item_price': item.get('price', 0),
                })
        data['products'] = products
        if products and not data.get('product_name'):
            data['product_name'] = products[0].get('name', '')

    # Order ID
    if not data.get('order_id'):
        data['order_id'] = str(data.get('id') or data.get('order_number') or '')

    # CartPanda ID para criação de Order
    if not data.get('cartpanda_id'):
        data['cartpanda_id'] = str(data.get('id') or '')

    # Payment method
    if not data.get('payment_method'):
        data['payment_method'] = data.get('gateway') or data.get('payment_gateway') or ''

    # --- Detecção de evento ---
    financial_status = str(data.get('financial_status', '')).lower()
    topic = str(data.get('topic', '')).lower()

    if financial_status == 'paid' or 'paid' in topic:
        return _handle_webhook(data, event_type_override='purchase_approved', lead_source_override='customer')
    elif financial_status == 'refunded' or 'refund' in topic:
        return _handle_webhook(data, event_type_override='refund', lead_source_override='customer')
    elif 'abandon' in topic or 'abandon' in financial_status:
        return _handle_webhook(data, event_type_override='cart_abandonment', lead_source_override='abandonment')
    elif financial_status == 'pending' or 'created' in topic:
        return _handle_webhook(data, lead_source_override='lead')
    else:
        return _handle_webhook(data, lead_source_override='lead')

# --- HEALTH CHECK ---

@extend_schema(
    tags=['Health'],
    summary='Health Check',
    description='Verifica se a API e o banco de dados estão funcionando.',
    responses={200: HealthResponseSerializer, 503: HealthResponseSerializer},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    status_data = {"status": "healthy", "database": "unknown"}
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status_data['database'] = "connected"
        return Response(status_data, status=status.HTTP_200_OK)
    except Exception as e:
        status_data['status'] = "unhealthy"
        status_data['error'] = str(e)
        return Response(status_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)