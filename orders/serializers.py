from rest_framework import serializers
from .models import Lead, Order, CapiEvent

class LeadSerializer(serializers.ModelSerializer):
    """
    Serializa os dados do Lead (Cliente).
    """
    class Meta:
        model = Lead
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name', 
            'city', 'state', 'zip_code', 'created_at'
        ]

class CapiEventSerializer(serializers.ModelSerializer):
    """
    Serializa o Log de envios para o Facebook.
    Útil para você debugar se o evento foi 'SENT' ou 'ERROR'.
    """
    lead_email = serializers.CharField(source='lead.email', read_only=True)
    
    class Meta:
        model = CapiEvent
        fields = [
            'id', 'event_name', 'event_id', 'fb_status', 
            'lead_email', 'created_at', 'fb_response'
        ]

class OrderSerializer(serializers.ModelSerializer):
    """
    Serializa os Pedidos (Vendas Reais).
    """
    lead_email = serializers.CharField(source='lead.email', read_only=True)
    lead_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'cartpanda_id', 'amount', 'status', 
            'payment_method', 'products', 'created_at', 
            'lead_email', 'lead_name'
        ]

    def get_lead_name(self, obj):
        if obj.lead:
            return f"{obj.lead.first_name or ''} {obj.lead.last_name or ''}".strip()
        return "Desconhecido"