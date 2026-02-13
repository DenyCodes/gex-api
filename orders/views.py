import logging
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
# Imports dos seus models e serializers
from .models import Order, CapiEvent, Lead
from .serializers import OrderSerializer, CapiEventSerializer, LeadSerializer
from .services import process_event  # ESSENCIAL: É isso que salva no banco e envia pro Meta

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    """Paginação padrão: 50 itens por página."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

# --- VIEWSETS (Para o Painel) ---

class CapiEventViewSet(viewsets.ModelViewSet):
    queryset = CapiEvent.objects.all().order_by('-created_at')
    serializer_class = CapiEventSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['fb_status', 'event_name']

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'payment_method']

class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['email']

# --- WEBHOOKS (Lógica de Recebimento) ---

def _handle_webhook(data, event_type_override=None):
    """
    Função central que recebe o dado, salva no Supabase e envia pro Meta via services.py
    """
    try:
        # 1. Garante o tipo de evento
        if event_type_override:
            data['event_type'] = event_type_override
            
        print(f"--- PROCESSANDO EVENTO: {data.get('event_type')} ---")
        
        # 2. Chama o services.py (AQUI ACONTECE A MÁGICA: SALVAR DB + ENVIAR META)
        result = process_event(data)
        
        # 3. Verifica o resultado do service
        if result.get('status') == 'error':
            print(f"ERRO NO PROCESSAMENTO: {result}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
        print("SUCESSO: Salvo no Supabase e Processado.")
        return Response(result, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Erro crítico no webhook: {e}")
        # Retorna erro detalhado para você ver no terminal
        return Response(
            {"status": "error", "detail": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_gex(request):
    return _handle_webhook(request.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_cart_abandonment(request):
    # Abandono de carrinho
    return _handle_webhook(request.data, event_type_override='cart_abandonment')


@csrf_exempt  # <--- ESSENCIAL para receber dados externos
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_abandono(request):
    try:
        # Pega os dados brutos do JSON enviado pelo script JS
        data = request.data
        
        # Opcional: Log para ver chegando
        print(f"--> Webhook recebido: {data.get('email')} - {data.get('phone')}")

        # Chama sua função process_event (que já sabe limpar e salvar)
        # Como o script JS manda chaves como 'phone', 'email', 'sku',
        # seu service.py precisa estar preparado para ler essas chaves.
        resultado = process_event(data)

        return JsonResponse(resultado, status=200)

    except Exception as e:
        print(f"Erro no webhook: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
@api_view(['POST', 'GET']) # Agora aceita GET também!
@permission_classes([AllowAny])
def webhook_purchase_approved(request):
    """
    Webhook para Compras.
    Aceita JSON (Webhook padrão) e Query Params (S2S/Postback).
    """
    # 1. Unifica os dados (Pega do corpo JSON OU da URL)
    data = {}
    
    # Se vier JSON no corpo (Webhook tradicional)
    if request.data:
        data.update(request.data)
        
    # Se vier na URL (Postback S2S / GET)
    if request.query_params:
        data.update(request.query_params.dict())

    # Define o tipo de evento
    # Se vier via S2S, assumimos que é compra aprovada
    return _handle_webhook(data, event_type_override='purchase_approved')

@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_lead(request):
    return _handle_webhook(request.data, event_type_override='lead')

# --- HEALTH CHECK ---

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