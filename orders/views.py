import logging
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# Imports dos seus models e serializers
from .models import Order, CapiEvent, Lead
from .serializers import OrderSerializer, CapiEventSerializer, LeadSerializer
from .services import process_event 

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    """Paginação padrão: 50 itens por página."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

# --- VIEWSETS (Para o Painel Admin) ---

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
    # AJUSTE: Adicionado 'lead_source' para você filtrar abandonos no painel
    filterset_fields = ['email', 'lead_source'] 

# --- WEBHOOKS (Lógica de Recebimento) ---

def _handle_webhook(data, event_type_override=None, lead_source_override=None):
    """
    Função central que recebe o dado, classifica, salva e envia pro Meta.
    """
    try:
        # 1. Garante o tipo de evento
        if event_type_override:
            data['event_type'] = event_type_override
        
        # 2. Garante a classificação da fonte (Lead vs Abandono vs Cliente)
        if lead_source_override:
            data['lead_source'] = lead_source_override
            
        print(f"--- PROCESSANDO EVENTO: {data.get('event_type')} | FONTE: {data.get('lead_source')} ---")
        
        # 3. Chama o services.py
        result = process_event(data)
        
        # 4. Verifica o resultado
        if result.get('status') == 'error':
            print(f"ERRO NO PROCESSAMENTO: {result}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
        print("SUCESSO: Salvo no Supabase e Processado.")
        return Response(result, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Erro crítico no webhook: {e}")
        return Response(
            {"status": "error", "detail": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_gex(request):
    # Webhook genérico, assume lead se não vier nada
    return _handle_webhook(request.data, lead_source_override='lead')

@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_cart_abandonment(request):
    # Abandono de carrinho (Legado ou integração direta)
    return _handle_webhook(request.data, event_type_override='cart_abandonment', lead_source_override='abandonment')

@csrf_exempt 
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_abandono(request):
    """
    Webhook específico para o SCRIPT JS de Abandono.
    """
    # Usamos a função auxiliar para manter padronização, mas forçamos as tags
    return _handle_webhook(request.data, event_type_override='cart_abandonment', lead_source_override='abandonment')

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def webhook_purchase_approved(request):
    """
    Webhook para Compras (S2S/Postback).
    """
    data = {}
    if request.data:
        data.update(request.data)
    if request.query_params:
        data.update(request.query_params.dict())

    # Compras classificamos como 'customer'
    return _handle_webhook(data, event_type_override='purchase_approved', lead_source_override='customer')

@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_lead(request):
    # Leads de formulários padrão
    return _handle_webhook(request.data, event_type_override='lead', lead_source_override='lead')

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