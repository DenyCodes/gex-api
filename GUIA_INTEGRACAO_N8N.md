# Guia de Integração com n8n - GEX Corporation API

Este guia detalha como integrar a API da GEX Corporation com o n8n para automatizar fluxos de trabalho.

## 🎯 Diferencial: Normalização Automática

**A API faz TODO o trabalho pesado!** Você pode enviar dados brutos de qualquer plataforma e a API:
- ✅ Detecta automaticamente a plataforma (Hotmart, Kiwify, Braip, etc.)
- ✅ Normaliza todos os campos automaticamente
- ✅ Gera campos faltantes (unique_key, event_type, etc.)
- ✅ Valida e limpa dados (emails, telefones, valores monetários)
- ✅ Separa nome completo em primeiro/último nome
- ✅ Converte valores para formato padrão

**Resultado:** O n8n só precisa fazer um simples `{{ $json }}` - sem transformações complexas!

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Configuração Simplificada](#configuração-simplificada)
- [Workflows por Tipo de Evento](#workflows-por-tipo-de-evento)
- [Mapeamento de Dados (Opcional)](#mapeamento-de-dados-opcional)
- [Tratamento de Erros](#tratamento-de-erros)
- [Exemplos Práticos](#exemplos-práticos)

## 🎯 Visão Geral

A API da GEX Corporation oferece endpoints específicos para diferentes tipos de eventos:

- **Webhook Principal**: `/api/v1/webhook/` - Processa qualquer tipo de evento (RECOMENDADO)
- **Abandono de Carrinho**: `/api/v1/webhook/cart-abandonment/`
- **Compra Aprovada**: `/api/v1/webhook/purchase-approved/`
- **Lead**: `/api/v1/webhook/lead/`

**Todos os endpoints aceitam dados brutos e fazem normalização automática!**

## ⚙️ Configuração Simplificada

### 1. Criar Workflow no n8n

1. Acesse o n8n
2. Clique em "New Workflow"
3. Adicione um nó **Webhook** como trigger
4. Configure o webhook:
   - **HTTP Method**: POST
   - **Path**: `gex-webhook` (ou o nome que preferir)
   - **Response Mode**: Respond When Last Node Finishes

### 2. Adicionar Nó HTTP Request (SIMPLES!)

1. Adicione um nó **HTTP Request** após o Webhook
2. Configure:
   - **Method**: POST
   - **URL**: `http://seu-servidor:8000/api/v1/webhook/`
   - **Authentication**: None (ou configure se necessário)
   - **Send Body**: ✅
   - **Body Content Type**: JSON
   - **Body**: `{{ $json }}` (SIMPLES! Apenas passe os dados brutos)

**Pronto!** A API faz todo o resto automaticamente.

## 🔄 Workflows por Tipo de Evento

### Workflow 1: Abandono de Carrinho

**Objetivo:** Capturar carrinhos abandonados e enviar para recuperação.

**Estrutura:**
```
Webhook → HTTP Request → IF (Verificar Sucesso) → Responder
```

**Configuração do HTTP Request (SIMPLIFICADO):**
- **URL**: `http://seu-servidor:8000/api/v1/webhook/cart-abandonment/`
- **Body (JSON)**: `{{ $json }}`

**Isso é tudo!** A API:
- Detecta automaticamente que é abandono de carrinho
- Extrai dados de qualquer estrutura
- Normaliza valores, telefones, emails
- Gera unique_key se necessário

**Exemplo com dados brutos do Hotmart:**
```json
{{ $json }}
```

A API recebe e transforma automaticamente!

**Verificação de Sucesso (IF Node):**
- **Condition**: String
- **Value 1**: `={{ $json.status }}`
- **Operation**: equals
- **Value 2**: `success`

### Workflow 2: Compra Aprovada

**Objetivo:** Processar compras aprovadas e enviar mensagem de boas-vindas.

**Estrutura:**
```
Webhook → HTTP Request → IF (Verificar Sucesso) → Responder
```

**Configuração do HTTP Request:**
- **URL**: `http://seu-servidor:8000/api/v1/webhook/purchase-approved/`
- **Body (JSON)**:
```json
{
  "unique_key": "={{ $json.order.id || $json.id }}",
  "order_id": "={{ $json.order.number || $json.order_id }}",
  "client_email": "={{ $json.customer.email }}",
  "client_first_name": "={{ $json.customer.first_name || '' }}",
  "client_last_name": "={{ $json.customer.last_name || '' }}",
  "client_phone": "={{ $json.customer.phone || '' }}",
  "product_name": "={{ $json.product.name || $json.product_name || '' }}",
  "order_amount": "={{ $json.order.total || $json.order_amount || 0 }}",
  "platform": "={{ $json.platform || 'unknown' }}"
}
```

### Workflow 3: Novo Lead

**Objetivo:** Capturar novos leads e qualificá-los automaticamente.

**Estrutura:**
```
Webhook → HTTP Request → IF (Verificar Sucesso) → Responder
```

**Configuração do HTTP Request:**
- **URL**: `http://seu-servidor:8000/api/v1/webhook/lead/`
- **Body (JSON)**:
```json
{
  "unique_key": "={{ $json.lead.id || $json.id }}",
  "order_id": "={{ $json.lead.source_id || $json.order_id || '' }}",
  "client_email": "={{ $json.lead.email || $json.email }}",
  "client_first_name": "={{ $json.lead.first_name || $json.first_name || '' }}",
  "client_last_name": "={{ $json.lead.last_name || $json.last_name || '' }}",
  "client_phone": "={{ $json.lead.phone || $json.phone || '' }}",
  "product_name": "={{ $json.lead.product_interest || $json.product_name || '' }}",
  "source": "={{ $json.lead.source || $json.source || 'unknown' }}",
  "platform": "={{ $json.platform || 'unknown' }}"
}
```

### Workflow 4: Webhook Universal (RECOMENDADO)

**Objetivo:** Processar qualquer tipo de evento usando o endpoint principal.

**Estrutura:**
```
Webhook → HTTP Request → IF (Verificar Sucesso) → Responder
```

**Configuração do HTTP Request (ULTRA SIMPLES):**
- **URL**: `http://seu-servidor:8000/api/v1/webhook/`
- **Body (JSON)**: `{{ $json }}`

**A API faz TUDO automaticamente:**
- Detecta plataforma (Hotmart, Kiwify, Braip, etc.)
- Detecta tipo de evento
- Normaliza todos os campos
- Valida e limpa dados
- Gera campos faltantes

**Este é o workflow mais simples e recomendado!**

## 📊 Mapeamento de Dados (Opcional)

### ⚡ Normalização Automática

**A API aceita dados de QUALQUER formato!** Você não precisa mapear nada manualmente.

### Estrutura de Dados Aceita

A API aceita dados em qualquer formato e normaliza automaticamente. Exemplos:

#### Hotmart (Formato Original)
```json
{
  "data": {
    "purchase": {
      "buyer": {
        "name": "João Silva",
        "email": "joao@example.com",
        "phone": { "number": "11999999999" }
      },
      "product": { "name": "Curso de Python" },
      "order": {
        "order_id": "12345",
        "price": { "value": 299.90 }
      }
    }
  }
}
```

#### Kiwify (Formato Original)
```json
{
  "order": { "id": "12345", "total": 299.90 },
  "customer": {
    "name": "João Silva",
    "email": "joao@example.com",
    "phone": "11999999999"
  },
  "product": { "name": "Curso de Python" }
}
```

#### Formato Genérico
```json
{
  "email": "joao@example.com",
  "name": "João Silva",
  "phone": "11999999999",
  "product": "Curso de Python",
  "amount": 299.90
}
```

**Todos esses formatos funcionam!** A API detecta e normaliza automaticamente.

### Campos Gerados Automaticamente

Se algum campo não existir, a API gera automaticamente:

- `unique_key`: Gerado baseado em ID + plataforma + timestamp
- `event_type`: Detectado automaticamente pelo contexto
- `platform`: Detectado pela estrutura dos dados
- `client_first_name` / `client_last_name`: Separado de `name` completo
- `client_phone`: Normalizado para formato padrão
- `client_email`: Validado e normalizado
- `order_amount`: Convertido para formato numérico padrão

### Mapeamento Manual (Opcional)

Se você quiser mapear manualmente (não necessário), a API espera:

| Campo | Obrigatório | Descrição | Exemplo |
|-------|-------------|-----------|---------|
| `unique_key` | ❌ Não* | Identificador único | "ORD-12345" |
| `order_id` | ❌ Não | ID do pedido | "12345" |
| `event_type` | ❌ Não* | Tipo do evento | "cart_abandonment" |
| `email` / `client_email` | ✅ Sim* | Email do cliente | "cliente@example.com" |
| `name` / `client_name` | ❌ Não | Nome completo | "João Silva" |
| `phone` / `client_phone` | ❌ Não | Telefone | "11999999999" |
| `product_name` / `product` | ❌ Não | Nome do produto | "Curso de Python" |
| `amount` / `order_amount` | ❌ Não | Valor | 299.90 |
| `platform` | ❌ Não* | Plataforma | "hotmart" |

*Campos marcados com * são gerados/detectados automaticamente se não fornecidos.

## ⚠️ Tratamento de Erros

### Estrutura de Resposta

A API sempre retorna uma resposta padronizada:

**Sucesso:**
```json
{
  "status": "success",
  "message": "Evento processado com sucesso",
  "data": { ... }
}
```

**Erro Parcial:**
```json
{
  "status": "partial_success",
  "message": "Evento salvo, mas houve erro ao enviar para Reportana",
  "data": { ... }
}
```

**Erro:**
```json
{
  "status": "error",
  "detail": "Mensagem de erro",
  "code": "CODIGO_ERRO"
}
```

### Códigos de Status HTTP

- **201**: Evento processado com sucesso
- **400**: Dados inválidos (verifique o campo `detail`)
- **500**: Erro interno do servidor

### Tratamento no n8n

**Nó IF para Verificar Sucesso:**
- **Condition**: String
- **Value 1**: `={{ $json.status }}`
- **Operation**: equals
- **Value 2**: `success`

**Nó IF para Verificar Erro:**
- **Condition**: String
- **Value 1**: `={{ $json.status }}`
- **Operation**: equals
- **Value 2**: `error`

**Nó para Log de Erro:**
- Use um nó **Code** ou **Function** para registrar erros
- Envie notificações em caso de erro crítico

## 💡 Exemplos Práticos

### Exemplo 1: Workflow Completo com Tratamento de Erros

```
Webhook
  ↓
HTTP Request (Enviar para API)
  ↓
IF (Status = success?)
  ├─ Sim → Responder Sucesso
  └─ Não → 
      ├─ Log de Erro
      ├─ Enviar Notificação
      └─ Responder Erro
```

### Exemplo 2: Workflow com Múltiplos Destinos

```
Webhook
  ↓
HTTP Request (Enviar para API GEX)
  ↓
IF (Status = success?)
  ├─ Sim → 
  │   ├─ Enviar para CRM
  │   ├─ Enviar Email
  │   └─ Responder Sucesso
  └─ Não → Responder Erro
```

### Exemplo 3: Workflow com Retry

```
Webhook
  ↓
HTTP Request (Enviar para API)
  ↓
IF (Status = success?)
  ├─ Sim → Responder Sucesso
  └─ Não → 
      ├─ Wait (5 segundos)
      ├─ HTTP Request (Retry)
      └─ IF (Status = success?)
          ├─ Sim → Responder Sucesso
          └─ Não → Responder Erro
```

## 🔍 Testando a Integração

### 1. Testar Health Check

```bash
curl http://seu-servidor:8000/api/v1/health/
```

### 2. Testar Webhook de Abandono de Carrinho

```bash
curl -X POST http://seu-servidor:8000/api/v1/webhook/cart-abandonment/ \
  -H "Content-Type: application/json" \
  -d '{
    "unique_key": "TEST-123",
    "client_email": "teste@example.com",
    "client_first_name": "Teste",
    "client_last_name": "API",
    "client_phone": "+5511999999999",
    "product_name": "Produto Teste",
    "cart_amount": 100.00,
    "platform": "test"
  }'
```

### 3. Verificar Eventos Criados

```bash
curl "http://seu-servidor:8000/api/v1/orders/?event_type=cart_abandonment"
```

## 📝 Dicas e Boas Práticas

1. **Sempre use `unique_key` único**: Evite duplicatas usando um identificador único
2. **Trate erros adequadamente**: Configure nós IF para verificar sucesso/erro
3. **Use logs**: Adicione nós de log para debug
4. **Configure retry**: Para operações críticas, configure retry automático
5. **Monitore health check**: Use o endpoint `/api/v1/health/` para monitoramento
6. **Valide dados**: Valide os dados antes de enviar para a API
7. **Use variáveis de ambiente**: Configure URLs e tokens como variáveis de ambiente no n8n

## 🆘 Solução de Problemas

### Problema: Erro 400 - unique_key é obrigatório

**Solução:** Verifique se o campo `unique_key` está sendo mapeado corretamente no nó HTTP Request.

### Problema: Erro 500 - Erro interno

**Solução:** 
1. Verifique os logs da API
2. Verifique se o banco de dados está acessível
3. Verifique se a Reportana está respondendo

### Problema: Status partial_success

**Solução:** O evento foi salvo no banco, mas houve erro ao enviar para Reportana. Verifique:
1. Token da Reportana está correto
2. Conexão com a internet
3. Status da API da Reportana

## 📚 Recursos Adicionais

- **Documentação Swagger**: http://seu-servidor:8000/api/docs/
- **Schema OpenAPI**: http://seu-servidor:8000/api/schema/
- **README Principal**: Veja o arquivo `README.md` para mais informações

---

**GEX Corporation** - Guia de Integração n8n v1.0.0

