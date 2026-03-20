# Normalização Automática de Dados - GEX Corporation API

## 🎯 Objetivo

A API da GEX Corporation foi projetada para **minimizar o trabalho no n8n** através de normalização automática de dados. Isso significa que você pode enviar dados brutos de qualquer plataforma e a API fará toda a transformação necessária.

## ✨ Funcionalidades

### 1. Detecção Automática de Plataforma

A API detecta automaticamente a plataforma de origem baseado na estrutura dos dados:

- **Hotmart**: Detecta pela estrutura `data.purchase`
- **Kiwify**: Detecta pela estrutura `order` + `customer`
- **Braip**: Detecta pela presença de `transaction` ou palavra "braip"
- **Eduzz**: Detecta pela estrutura `product` + `affiliate`
- **Tray**: Detecta pela palavra "tray" ou "loja"
- **Genérico**: Qualquer outro formato é processado genericamente

### 2. Normalização de Campos

#### Telefone
- Remove caracteres não numéricos
- Adiciona código do país (55) se necessário
- Normaliza para formato: `55XXXXXXXXXXX`
- Valida comprimento mínimo

#### Email
- Converte para minúsculas
- Remove espaços
- Valida formato básico (@ e domínio)
- Retorna `None` se inválido

#### Nome
- Separa nome completo em primeiro e último nome
- Trata casos especiais (um nome só, múltiplos sobrenomes)
- Limpa espaços extras

#### Valores Monetários
- Remove símbolos de moeda
- Converte vírgula para ponto (formato brasileiro)
- Converte para float
- Arredonda para 2 casas decimais

### 3. Geração Automática de Campos

#### unique_key
Se não fornecido, gera automaticamente:
```
{PLATAFORMA}-{ID ou TIMESTAMP}-{EMAIL_PARTE}
```

Exemplo: `HOTMART-12345-joao` ou `KIWIFY-20240101120000-joao`

#### event_type
Detecta automaticamente baseado em:
- Campo `event` ou `event_type` explícito
- Palavras-chave no nome do evento
- Estrutura dos dados (presença de `cart_amount`, etc.)

#### platform
Detecta automaticamente pela estrutura dos dados.

### 4. Extração Inteligente

A API tenta extrair dados de várias localizações possíveis:

**Email:**
- `email`
- `client_email`
- `customer_email`
- `buyer_email`
- `data.purchase.buyer.email` (Hotmart)
- `customer.email` (Kiwify)

**Telefone:**
- `phone`
- `client_phone`
- `customer_phone`
- `buyer_phone`
- `telephone`
- `mobile`
- `data.purchase.buyer.phone.number` (Hotmart)

**Nome:**
- `name`
- `client_name`
- `customer_name`
- `buyer_name`
- `first_name` + `last_name`
- `client_first_name` + `client_last_name`

**Valor:**
- `amount`
- `order_amount`
- `total`
- `value`
- `price`
- `cart_amount`
- `purchase_amount`

## 📋 Exemplos de Transformação

### Exemplo 1: Hotmart

**Entrada (dados brutos):**
```json
{
  "data": {
    "purchase": {
      "buyer": {
        "name": "João Silva",
        "email": "JOAO@EXAMPLE.COM",
        "phone": {
          "number": "(11) 99999-9999"
        }
      },
      "product": {
        "name": "Curso de Python"
      },
      "order": {
        "order_id": "12345",
        "price": {
          "value": "299,90"
        }
      }
    }
  }
}
```

**Saída (normalizada):**
```json
{
  "unique_key": "HOTMART-12345",
  "order_id": "12345",
  "event_type": "unknown",
  "platform": "hotmart",
  "client_email": "joao@example.com",
  "client_first_name": "João",
  "client_last_name": "Silva",
  "client_phone": "5511999999999",
  "product_name": "Curso de Python",
  "order_amount": 299.90
}
```

### Exemplo 2: Kiwify

**Entrada (dados brutos):**
```json
{
  "order": {
    "id": "67890",
    "total": 499.99
  },
  "customer": {
    "name": "Maria Santos",
    "email": "maria@example.com",
    "phone": "11988888888"
  },
  "product": {
    "name": "Curso Avançado"
  }
}
```

**Saída (normalizada):**
```json
{
  "unique_key": "KIWIFY-67890",
  "order_id": "67890",
  "event_type": "unknown",
  "platform": "kiwify",
  "client_email": "maria@example.com",
  "client_first_name": "Maria",
  "client_last_name": "Santos",
  "client_phone": "5511988888888",
  "product_name": "Curso Avançado",
  "order_amount": 499.99
}
```

### Exemplo 3: Formato Genérico

**Entrada (dados brutos):**
```json
{
  "email": "pedro@example.com",
  "name": "Pedro Oliveira",
  "phone": "+55 11 77777-7777",
  "product": "E-book Grátis",
  "amount": "R$ 0,00"
}
```

**Saída (normalizada):**
```json
{
  "unique_key": "UNKNOWN-20240101120000-pedro",
  "order_id": "",
  "event_type": "lead",
  "platform": "unknown",
  "client_email": "pedro@example.com",
  "client_first_name": "Pedro",
  "client_last_name": "Oliveira",
  "client_phone": "5511777777777",
  "product_name": "E-book Grátis",
  "order_amount": 0.0
}
```

## 🔧 Como Usar

### No n8n

**Simplesmente envie os dados brutos:**

```json
{{ $json }}
```

A API fará toda a transformação automaticamente!

### Endpoint

```
POST /api/v1/webhook/
```

**Body:** Dados brutos em qualquer formato

**Resposta:**
```json
{
  "status": "success",
  "message": "Evento processado. Enviado com sucesso",
  "data": {
    "unique_key": "HOTMART-12345",
    "order_id": "12345",
    "event_type": "purchase_approved",
    "status_whatsapp": "SENT",
    "created": true
  }
}
```

## ⚠️ Limitações

1. **Email obrigatório**: Pelo menos um email válido deve estar presente nos dados
2. **Dados não podem ser vazios**: O payload não pode ser `null` ou `{}`
3. **Formato JSON**: Apenas JSON é aceito (não XML, CSV, etc.)

## 🎯 Benefícios

1. **Menos trabalho no n8n**: Apenas `{{ $json }}` é necessário
2. **Suporte a múltiplas plataformas**: Funciona com qualquer formato
3. **Dados sempre normalizados**: Garante consistência no banco
4. **Menos erros**: Validação e limpeza automática
5. **Manutenção simplificada**: Mudanças na estrutura são tratadas automaticamente

---

**GEX Corporation API** - Normalização Automática v1.0.0

