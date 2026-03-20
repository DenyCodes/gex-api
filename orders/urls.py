from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CapiEventViewSet,
    OrderViewSet,
    LeadViewSet,
    webhook_abandono,          # <--- Verifique se está importado
    webhook_gex, 
    webhook_cart_abandonment,
    webhook_purchase_approved,
    webhook_lead,
    health_check
)

router = DefaultRouter()
router.register(r'events', CapiEventViewSet, basename='events')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'leads', LeadViewSet, basename='leads')

urlpatterns = [
    # Rotas do Painel
    path('', include(router.urls)),
    
    # --- AQUI ESTÁ A CORREÇÃO ---
    # Coloque esta linha explicitamente aqui:
    path('webhook/abandono/', webhook_abandono, name='webhook_abandono'),
    
    # As outras rotas
    path('webhook/', webhook_gex, name='webhook-main'),
    path('webhook/cart/', webhook_cart_abandonment, name='webhook-cart'), 
    path('webhook/purchase/', webhook_purchase_approved, name='webhook-purchase'),
    path('webhook/lead/', webhook_lead, name='webhook-lead'),
    path('health/', health_check, name='health-check'),
]