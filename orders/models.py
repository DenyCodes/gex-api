from django.db import models
import uuid

class Lead(models.Model):
    """
    Mapeia a tabela 'leads' do Supabase.
    Identidade única do cliente.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    
    # Dados de Geolocalização (Match Quality)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    
    # Cookies Facebook
    fbp = models.CharField(max_length=255, null=True, blank=True)
    fbc = models.CharField(max_length=255, null=True, blank=True)
    lead_source = models.CharField(max_length=50, default='lead', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False # Django não mexe na estrutura, pois criamos via SQL
        db_table = 'leads'

class Order(models.Model):
    """
    Mapeia a tabela 'orders' do Supabase.
    Compras reais (Financeiro).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='orders')
    
    cartpanda_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, default='pending')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='BRL')
    products = models.JSONField(default=list)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'orders'

class CapiEvent(models.Model):
    """
    Mapeia a tabela 'capi_events' do Supabase.
    Log de envios para o Facebook.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True)
    
    event_name = models.CharField(max_length=50) # InitiateCheckout, Purchase
    event_id = models.CharField(max_length=100)  # Deduplicação
    
    # Dados Técnicos
    user_agent = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    source_url = models.TextField(null=True, blank=True)
    
    # Payload e Status
    payload = models.JSONField(null=True)
    fb_status = models.CharField(max_length=20, default='PENDING')
    fb_response = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'capi_events'