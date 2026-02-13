"""
Módulo de transformação e normalização de dados da GEX Corporation API.

Este módulo aceita dados de QUALQUER plataforma e formato, normalizando automaticamente
para o formato interno padrão. Isso minimiza o trabalho necessário no n8n.

Suporta:
- Hotmart
- Kiwify
- Braip
- Eduzz
- Formatos genéricos
- Dados brutos de qualquer origem
"""
import re
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Classe para normalização de dados em formato padrão"""
    
    @staticmethod
    def normalize_phone(phone: Optional[str]) -> Optional[str]:
        """
        Normaliza telefone para formato padrão (+55XXXXXXXXXXX).
        
        Args:
            phone: Telefone em qualquer formato
            
        Returns:
            Telefone normalizado ou None
        """
        if not phone:
            return None
        
        # Remove tudo exceto números
        phone_clean = re.sub(r'\D', '', str(phone))
        
        # Remove zeros à esquerda
        phone_clean = phone_clean.lstrip('0')
        
        # Adiciona código do país se necessário (Brasil)
        if len(phone_clean) == 10 or len(phone_clean) == 11:
            if not phone_clean.startswith('55'):
                phone_clean = '55' + phone_clean
        
        # Validação básica
        if len(phone_clean) < 10:
            return None
        
        return phone_clean
    
    @staticmethod
    def normalize_email(email: Optional[str]) -> Optional[str]:
        """
        Normaliza e valida email.
        
        Args:
            email: Email em qualquer formato
            
        Returns:
            Email normalizado ou None
        """
        if not email:
            return None
        
        email = str(email).strip().lower()
        
        # Validação básica
        if '@' not in email or '.' not in email.split('@')[1]:
            return None
        
        # Remove espaços
        email = email.replace(' ', '')
        
        return email
    
    @staticmethod
    def split_name(full_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Separa nome completo em primeiro e último nome.
        
        Args:
            full_name: Nome completo
            
        Returns:
            Tupla (primeiro_nome, ultimo_nome)
        """
        if not full_name:
            return None, None
        
        full_name = str(full_name).strip()
        
        if not full_name:
            return None, None
        
        parts = full_name.split()
        
        if len(parts) == 0:
            return None, None
        elif len(parts) == 1:
            return parts[0], None
        else:
            # Primeiro nome é a primeira palavra
            # Último nome é o resto
            return parts[0], ' '.join(parts[1:])
    
    @staticmethod
    def normalize_amount(amount) -> Optional[float]:
        """
        Normaliza valores monetários para float.
        
        Args:
            amount: Valor em qualquer formato (string, int, float)
            
        Returns:
            Valor normalizado como float ou None
        """
        if amount is None:
            return None
        
        # Se for string, remove símbolos e converte
        if isinstance(amount, str):
            # Remove símbolos de moeda e espaços
            amount_clean = re.sub(r'[^\d,.]', '', amount)
            # Substitui vírgula por ponto (formato brasileiro)
            amount_clean = amount_clean.replace(',', '.')
            # Remove múltiplos pontos
            if amount_clean.count('.') > 1:
                parts = amount_clean.split('.')
                amount_clean = '.'.join(parts[:-1]) + '.' + parts[-1]
        else:
            amount_clean = amount
        
        try:
            value = float(amount_clean)
            # Arredonda para 2 casas decimais
            return round(value, 2)
        except (ValueError, TypeError):
            logger.warning(f"Erro ao normalizar valor monetário: {amount}")
            return None
    
    @staticmethod
    def generate_unique_key(data: Dict, platform: str) -> str:
        """
        Gera unique_key automaticamente se não existir.
        
        Args:
            data: Dados do evento
            platform: Plataforma detectada
            
        Returns:
            unique_key gerado
        """
        # Tenta vários campos possíveis
        possible_keys = [
            data.get('unique_key'),
            data.get('id'),
            data.get('order_id'),
            data.get('purchase_id'),
            data.get('transaction_id'),
            data.get('event_id'),
            data.get('lead_id'),
        ]
        
        # Verifica em estruturas aninhadas
        if 'data' in data and isinstance(data['data'], dict):
            possible_keys.extend([
                data['data'].get('purchase', {}).get('order', {}).get('order_id'),
                data['data'].get('id'),
            ])
        
        if 'order' in data and isinstance(data['order'], dict):
            possible_keys.append(data['order'].get('id'))
        
        # Procura o primeiro valor válido
        for key in possible_keys:
            if key:
                return f"{platform.upper()}-{str(key)}"
        
        # Se não encontrar, gera baseado em timestamp e email
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        email_part = data.get('email') or data.get('client_email') or 'UNKNOWN'
        email_part = email_part.split('@')[0][:10] if '@' in email_part else 'UNKNOWN'
        
        return f"{platform.upper()}-{timestamp}-{email_part}"
    
    @staticmethod
    def detect_event_type(data: Dict) -> Optional[str]:
        """
        Detecta tipo de evento automaticamente baseado no contexto.
        
        Args:
            data: Dados do evento
            
        Returns:
            Tipo de evento detectado ou None
        """
        # Verifica campo explícito
        event = data.get('event') or data.get('event_type') or data.get('type') or ''
        event_lower = str(event).lower()
        
        # Mapeamento de eventos
        if any(keyword in event_lower for keyword in ['cart', 'abandon', 'carrinho', 'abandono']):
            return 'cart_abandonment'
        elif any(keyword in event_lower for keyword in ['purchase', 'approved', 'paid', 'compra', 'aprovada', 'pago']):
            return 'purchase_approved'
        elif any(keyword in event_lower for keyword in ['lead', 'contact', 'form', 'formulario']):
            return 'lead'
        
        # Detecta por estrutura de dados (Hotmart)
        if 'data' in data:
            purchase = data.get('data', {}).get('purchase', {})
            if purchase:
                event_name = purchase.get('event', {}).get('name', '').lower()
                if 'abandon' in event_name or 'cart' in event_name:
                    return 'cart_abandonment'
                elif 'approved' in event_name or 'paid' in event_name:
                    return 'purchase_approved'
        
        # Detecta por presença de campos específicos
        if 'cart_amount' in data or 'cart_total' in data:
            return 'cart_abandonment'
        
        if 'order_amount' in data and data.get('status') in ['approved', 'paid', 'aprovado', 'pago']:
            return 'purchase_approved'

        # Detecta por financial_status (CartPanda/Shopify-like)
        financial_status = str(data.get('financial_status', '')).lower()
        if financial_status == 'paid':
            return 'purchase_approved'
        if financial_status in ('refunded', 'voided'):
            return 'refund'

        return None


class PlatformDetector:
    """Detecta automaticamente a plataforma de origem dos dados"""
    
    @staticmethod
    def detect(data: Dict) -> str:
        """
        Detecta plataforma baseado na estrutura dos dados.
        
        Args:
            data: Dados brutos recebidos
            
        Returns:
            Nome da plataforma detectada
        """
        # Se já vier especificado e válido
        platform = data.get('platform', '').lower()
        if platform and platform not in ['unknown', '']:
            return platform
        
        # Hotmart - estrutura característica
        if 'data' in data and isinstance(data['data'], dict):
            if 'purchase' in data['data'] or 'subscription' in data['data']:
                return 'hotmart'
        
        # Kiwify - estrutura característica
        if 'order' in data and 'customer' in data:
            if isinstance(data.get('order'), dict) and isinstance(data.get('customer'), dict):
                return 'kiwify'
        
        # Braip - estrutura característica
        if 'transaction' in data or 'braip' in str(data).lower():
            return 'braip'
        
        # Eduzz - estrutura característica
        if 'eduzz' in str(data).lower() or ('product' in data and 'affiliate' in data):
            return 'eduzz'
        
        # Tray - estrutura característica
        if 'tray' in str(data).lower() or 'loja' in str(data).lower():
            return 'tray'

        # CartPanda - estrutura Shopify-like
        if 'cartpanda' in str(data).lower():
            return 'cartpanda'
        if 'financial_status' in data and 'line_items' in data:
            return 'cartpanda'
        if 'line_items' in data and 'billing_address' in data:
            return 'cartpanda'

        return 'unknown'


class HotmartTransformer:
    """Transforma dados do formato Hotmart para formato padrão"""
    
    @staticmethod
    def transform(data: Dict) -> Dict:
        """
        Transforma dados do Hotmart.
        
        Args:
            data: Dados no formato Hotmart
            
        Returns:
            Dados normalizados
        """
        try:
            purchase = data.get('data', {}).get('purchase', {})
            buyer = purchase.get('buyer', {})
            product = purchase.get('product', {})
            order = purchase.get('order', {})
            
            # Extrai nome completo e separa
            buyer_name = buyer.get('name', '')
            first_name, last_name = DataNormalizer.split_name(buyer_name)
            
            # Telefone pode vir em formato de objeto
            phone_obj = buyer.get('phone', {})
            phone = phone_obj.get('number') if isinstance(phone_obj, dict) else phone_obj
            
            # Valor pode vir em formato de objeto
            price_obj = order.get('price', {})
            amount = price_obj.get('value') if isinstance(price_obj, dict) else price_obj
            
            return {
                'unique_key': f"HOTMART-{order.get('order_id', '')}",
                'order_id': str(order.get('order_id', '')),
                'event_type': DataNormalizer.detect_event_type(data) or 'unknown',
                'platform': 'hotmart',
                'client_email': DataNormalizer.normalize_email(buyer.get('email')),
                'client_first_name': first_name,
                'client_last_name': last_name,
                'client_phone': DataNormalizer.normalize_phone(phone),
                'product_name': product.get('name', ''),
                'order_amount': DataNormalizer.normalize_amount(amount),
                'raw_payload': str(data)
            }
        except Exception as e:
            logger.error(f"Erro ao transformar dados Hotmart: {str(e)}")
            # Retorna transformação genérica em caso de erro
            return UniversalTransformer._generic_transform(data, 'hotmart')


class KiwifyTransformer:
    """Transforma dados do formato Kiwify para formato padrão"""
    
    @staticmethod
    def transform(data: Dict) -> Dict:
        """
        Transforma dados do Kiwify.
        
        Args:
            data: Dados no formato Kiwify
            
        Returns:
            Dados normalizados
        """
        try:
            order = data.get('order', {})
            customer = data.get('customer', {})
            product = data.get('product', {})
            
            # Nome pode vir completo ou separado
            customer_name = customer.get('name', '')
            if customer_name:
                first_name, last_name = DataNormalizer.split_name(customer_name)
            else:
                first_name = customer.get('first_name')
                last_name = customer.get('last_name')
            
            return {
                'unique_key': f"KIWIFY-{order.get('id', '')}",
                'order_id': str(order.get('id', '')),
                'event_type': DataNormalizer.detect_event_type(data) or 'unknown',
                'platform': 'kiwify',
                'client_email': DataNormalizer.normalize_email(customer.get('email')),
                'client_first_name': first_name,
                'client_last_name': last_name,
                'client_phone': DataNormalizer.normalize_phone(customer.get('phone')),
                'product_name': product.get('name', '') if isinstance(product, dict) else str(product),
                'order_amount': DataNormalizer.normalize_amount(order.get('total')),
                'raw_payload': str(data)
            }
        except Exception as e:
            logger.error(f"Erro ao transformar dados Kiwify: {str(e)}")
            return UniversalTransformer._generic_transform(data, 'kiwify')


class CartPandaTransformer:
    """Transforma dados do formato CartPanda (Shopify-like) para formato padrão"""

    @staticmethod
    def transform(data: Dict) -> Dict:
        try:
            customer = data.get('customer', {}) or {}
            billing = data.get('billing_address', {}) or {}
            shipping = data.get('shipping_address', {}) or {}
            line_items = data.get('line_items', []) or []

            # Nome: customer > billing > shipping
            first_name = customer.get('first_name') or billing.get('first_name') or shipping.get('first_name')
            last_name = customer.get('last_name') or billing.get('last_name') or shipping.get('last_name')

            if not first_name:
                full_name = customer.get('name') or billing.get('name')
                first_name, last_name = DataNormalizer.split_name(full_name)

            # Email e telefone
            email = customer.get('email') or data.get('email') or billing.get('email')
            phone = (customer.get('phone') or billing.get('phone') or
                     shipping.get('phone') or data.get('phone'))

            # Endereço (billing > shipping)
            zip_code = billing.get('zip') or shipping.get('zip')
            city = billing.get('city') or shipping.get('city')
            state = billing.get('province_code') or billing.get('province') or shipping.get('province_code')

            # Valor e financeiro
            amount = data.get('total_price') or data.get('subtotal_price') or 0

            # Produtos: extrai de line_items
            products = []
            for item in line_items:
                if isinstance(item, dict):
                    products.append({
                        'name': item.get('title') or item.get('name', ''),
                        'quantity': item.get('quantity', 1),
                        'price': item.get('price', 0),
                    })

            product_name = products[0]['name'] if products else ''

            # IDs
            order_id = str(data.get('id') or data.get('order_number') or '')
            cartpanda_id = str(data.get('id') or '')

            # Status do evento
            financial_status = str(data.get('financial_status', '')).lower()
            if financial_status == 'paid':
                event_type = 'purchase_approved'
                order_status = 'paid'
            elif financial_status == 'refunded':
                event_type = 'refund'
                order_status = 'refunded'
            elif financial_status == 'pending':
                event_type = 'lead'
                order_status = 'pending'
            else:
                event_type = DataNormalizer.detect_event_type(data) or 'unknown'
                order_status = financial_status or 'pending'

            return {
                'unique_key': f"CARTPANDA-{order_id}",
                'order_id': order_id,
                'cartpanda_id': cartpanda_id,
                'event_type': event_type,
                'platform': 'cartpanda',
                'status': order_status,
                'client_email': DataNormalizer.normalize_email(email),
                'client_first_name': first_name,
                'client_last_name': last_name,
                'client_phone': DataNormalizer.normalize_phone(phone),
                'product_name': product_name,
                'order_amount': DataNormalizer.normalize_amount(amount),
                'products': products,
                'payment_method': data.get('gateway') or data.get('payment_gateway') or '',
                'currency': data.get('currency', 'BRL'),
                'zip_code': zip_code,
                'city': city,
                'state': state,
                'raw_payload': str(data),
            }
        except Exception as e:
            logger.error(f"Erro ao transformar dados CartPanda: {str(e)}")
            return UniversalTransformer._generic_transform(data, 'cartpanda')


class UniversalTransformer:
    """
    Transforma dados de QUALQUER formato para formato padrão.
    
    Esta é a classe principal que deve ser usada para normalizar dados.
    Ela detecta automaticamente a plataforma e aplica a transformação apropriada.
    """
    
    @staticmethod
    def transform(data: Dict) -> Dict:
        """
        Transforma dados de qualquer formato para formato padrão.
        
        Esta função:
        1. Detecta a plataforma automaticamente
        2. Aplica transformador específico se disponível
        3. Usa transformação genérica como fallback
        4. Normaliza todos os campos
        
        Args:
            data: Dados brutos em qualquer formato
            
        Returns:
            Dados normalizados no formato padrão
        """
        if not data:
            raise ValueError("Dados não podem ser vazios")
        
        # Detecta plataforma
        platform = PlatformDetector.detect(data)
        
        # Tenta usar transformador específico
        if platform == 'hotmart':
            try:
                return HotmartTransformer.transform(data)
            except Exception as e:
                logger.warning(f"Erro no transformador Hotmart, usando genérico: {str(e)}")
                return UniversalTransformer._generic_transform(data, platform)
        
        elif platform == 'kiwify':
            try:
                return KiwifyTransformer.transform(data)
            except Exception as e:
                logger.warning(f"Erro no transformador Kiwify, usando genérico: {str(e)}")
                return UniversalTransformer._generic_transform(data, platform)

        elif platform == 'cartpanda':
            try:
                return CartPandaTransformer.transform(data)
            except Exception as e:
                logger.warning(f"Erro no transformador CartPanda, usando genérico: {str(e)}")
                return UniversalTransformer._generic_transform(data, platform)

        # Usa transformação genérica
        return UniversalTransformer._generic_transform(data, platform)
    
    @staticmethod
    def _generic_transform(data: Dict, platform: str) -> Dict:
        """
        Transformação genérica para dados de qualquer formato.
        
        Tenta extrair dados de várias estruturas possíveis.
        
        Args:
            data: Dados brutos
            platform: Plataforma detectada
            
        Returns:
            Dados normalizados
        """
        # Extrai nome de várias possíveis localizações
        full_name = (
            data.get('name') or 
            data.get('client_name') or 
            data.get('customer_name') or
            data.get('buyer_name') or
            f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or
            f"{data.get('client_first_name', '')} {data.get('client_last_name', '')}".strip()
        )
        
        first_name, last_name = DataNormalizer.split_name(full_name)
        
        # Se não encontrou nome completo, tenta campos separados
        if not first_name:
            first_name = data.get('client_first_name') or data.get('first_name')
        if not last_name:
            last_name = data.get('client_last_name') or data.get('last_name')
        
        # Extrai email de várias possíveis localizações
        email = (
            data.get('email') or 
            data.get('client_email') or 
            data.get('customer_email') or
            data.get('buyer_email')
        )
        
        # Extrai telefone de várias possíveis localizações
        phone = (
            data.get('phone') or 
            data.get('client_phone') or 
            data.get('customer_phone') or
            data.get('buyer_phone') or
            data.get('telephone') or
            data.get('mobile')
        )
        
        # Se telefone estiver em objeto aninhado
        if isinstance(phone, dict):
            phone = phone.get('number') or phone.get('value')
        
        # Extrai produto de várias possíveis localizações
        product = (
            data.get('product_name') or 
            data.get('product') or 
            data.get('product_name')
        )
        
        if isinstance(product, dict):
            product = product.get('name') or product.get('title')
        
        # Extrai valor de várias possíveis localizações
        amount = (
            data.get('amount') or 
            data.get('order_amount') or 
            data.get('total') or
            data.get('value') or
            data.get('price') or
            data.get('cart_amount') or
            data.get('purchase_amount')
        )
        
        # Se valor estiver em objeto aninhado
        if isinstance(amount, dict):
            amount = amount.get('value') or amount.get('total') or amount.get('amount')
        
        # Gera unique_key se não existir
        unique_key = data.get('unique_key')
        if not unique_key:
            unique_key = DataNormalizer.generate_unique_key(data, platform)
        
        # Detecta tipo de evento
        event_type = data.get('event_type') or DataNormalizer.detect_event_type(data) or 'unknown'
        
        return {
            'unique_key': unique_key,
            'order_id': str(data.get('order_id') or data.get('id') or data.get('order_number') or ''),
            'event_type': event_type,
            'platform': platform,
            'client_email': DataNormalizer.normalize_email(email),
            'client_first_name': first_name,
            'client_last_name': last_name,
            'client_phone': DataNormalizer.normalize_phone(phone),
            'product_name': str(product) if product else '',
            'order_amount': DataNormalizer.normalize_amount(amount),
            'raw_payload': str(data)
        }

