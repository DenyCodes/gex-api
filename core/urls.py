from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Importamos as views da app orders
from orders.views import (
    OrderViewSet,
    CapiEventViewSet,
    LeadViewSet,
    webhook_abandono,
    webhook_gex,
    webhook_cart_abandonment,
    webhook_purchase_approved,
    webhook_lead,
    health_check,
)

# Configuração do router para ViewSets
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'events', CapiEventViewSet, basename='event')
router.register(r'leads', LeadViewSet, basename='lead')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API v1 - Endpoints principais (Orders, Events, Leads)
    path('api/v1/', include(router.urls)),
    
    # --- WEBHOOKS (URLs Ajustadas e Simplificadas) ---
    
    # Webhook Principal GEX
    path('api/v1/webhook/', webhook_gex, name='webhook-gex'),
        path('api/v1/webhook/abandono/', webhook_abandono, name='webhook_abandono'),

    # Webhook Carrinho (Simplificado para /cart/)
    path('api/v1/webhook/cart/', webhook_cart_abandonment, name='webhook-cart-abandonment'),
    
    # Webhook Compra (Simplificado para /purchase/ - CORRIGE SEU ERRO 404)
    path('api/v1/webhook/purchase/', webhook_purchase_approved, name='webhook-purchase-approved'),
    
    # Webhook Lead
    path('api/v1/webhook/lead/', webhook_lead, name='webhook-lead'),
    
    # --- OUTROS ---

    # Compatibilidade (Opcional)
    path('api/v1/n8n-webhook/', webhook_gex, name='n8n-webhook'),
    
    # Health check
    path('api/v1/health/', health_check, name='health-check'),
    
    # Documentação OpenAPI/Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]