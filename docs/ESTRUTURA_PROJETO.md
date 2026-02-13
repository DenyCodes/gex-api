# Estrutura do Projeto - GEX Corporation API

Este documento descreve a estrutura e organização do projeto da API da GEX Corporation.

## 📁 Estrutura de Diretórios

```
reportana/
├── core/                      # Configurações principais do Django
│   ├── __init__.py
│   ├── settings.py            # Configurações da aplicação
│   ├── urls.py                # Rotas da API
│   ├── wsgi.py                # WSGI config
│   └── asgi.py                # ASGI config
│
├── orders/                    # App principal de eventos
│   ├── __init__.py
│   ├── models.py              # Modelos de dados (Order)
│   ├── views.py               # Views e endpoints da API
│   ├── serializers.py         # Serializadores DRF
│   ├── services.py            # Lógica de negócio
│   ├── admin.py               # Configuração do admin Django
│   ├── apps.py                # Configuração do app
│   ├── tests.py               # Testes unitários
│   └── migrations/            # Migrações do banco de dados
│
├── docs/                      # Documentação adicional
│   └── ESTRUTURA_PROJETO.md   # Este arquivo
│
├── venv/                      # Ambiente virtual Python
│
├── .gitignore                 # Arquivos ignorados pelo Git
├── Dockerfile                 # Configuração Docker
├── docker-compose.yml         # Compose para Docker
├── manage.py                  # Script de gerenciamento Django
├── requirements.txt          # Dependências do projeto
├── README.md                  # Documentação principal
├── GUIA_INTEGRACAO_N8N.md     # Guia de integração com n8n
└── n8n_workflow_gex.json      # Exemplo de workflow n8n
```

## 🏗️ Arquitetura

### Camadas da Aplicação

1. **Camada de Apresentação (Views)**
   - `orders/views.py`: Endpoints REST da API
   - ViewSets para operações CRUD
   - Webhooks específicos para cada tipo de evento

2. **Camada de Negócio (Services)**
   - `orders/services.py`: Lógica de negócio
   - Processadores específicos para cada tipo de evento
   - Integração com Reportana

3. **Camada de Dados (Models)**
   - `orders/models.py`: Modelos Django
   - Representação das tabelas do banco de dados

4. **Camada de Serialização**
   - `orders/serializers.py`: Serializadores DRF
   - Validação de dados
   - Transformação de dados

### Fluxo de Dados

```
n8n/Plataforma Externa
    ↓
Webhook Endpoint (views.py)
    ↓
Service Layer (services.py)
    ├─ Validação
    ├─ Processamento de Negócio
    └─ Integração com Reportana
    ↓
Model Layer (models.py)
    ↓
Banco de Dados MySQL
```

## 📦 Componentes Principais

### 1. Models (`orders/models.py`)

**Order Model:**
- Representa eventos/pedidos no banco de dados
- Campos principais:
  - `unique_key`: Chave primária única
  - `order_id`: ID do pedido
  - `event_type`: Tipo do evento
  - `client_*`: Dados do cliente
  - `status_whatsapp`: Status do envio

### 2. Services (`orders/services.py`)

**Processadores de Eventos:**
- `CartAbandonmentProcessor`: Abandono de carrinho
- `ApprovedPurchaseProcessor`: Compras aprovadas
- `LeadProcessor`: Leads
- `GenericEventProcessor`: Eventos genéricos

**Função Principal:**
- `process_event()`: Roteia eventos para o processador correto

### 3. Views (`orders/views.py`)

**Endpoints:**
- `OrderViewSet`: CRUD completo de eventos
- `webhook_gex()`: Webhook principal
- `webhook_cart_abandonment()`: Webhook de abandono
- `webhook_purchase_approved()`: Webhook de compra
- `webhook_lead()`: Webhook de lead
- `health_check()`: Verificação de saúde

### 4. Serializers (`orders/serializers.py`)

**OrderSerializer:**
- Validação de dados
- Transformação de dados
- Campos read-only

## 🔄 Fluxos de Processamento

### Fluxo 1: Abandono de Carrinho

```
1. Webhook recebe evento
2. CartAbandonmentProcessor.process()
3. Salva no banco de dados
4. Prepara payload específico (com cart_value e urgency)
5. Envia para Reportana
6. Atualiza status_whatsapp
7. Retorna resposta
```

### Fluxo 2: Compra Aprovada

```
1. Webhook recebe evento
2. ApprovedPurchaseProcessor.process()
3. Salva no banco de dados
4. Prepara payload específico (com purchase_value e priority)
5. Envia para Reportana
6. Atualiza status_whatsapp
7. Retorna resposta
```

### Fluxo 3: Lead

```
1. Webhook recebe evento
2. LeadProcessor.process()
3. Salva no banco de dados
4. Calcula lead_score
5. Prepara payload específico (com lead_score e source)
6. Envia para Reportana
7. Atualiza status_whatsapp
8. Retorna resposta
```

## 🔌 Integrações

### Reportana

- **URL**: `https://api.reportana.com/v1/webhooks/{token}`
- **Método**: POST
- **Formato**: JSON
- **Timeout**: 10 segundos

### Banco de Dados

- **Tipo**: MySQL
- **Tabela**: `unified_lead_events_new_teste_2`
- **Model**: `Order` (managed=False)

## 📝 Convenções de Código

### Nomenclatura

- **Classes**: PascalCase (ex: `CartAbandonmentProcessor`)
- **Funções**: snake_case (ex: `process_event`)
- **Variáveis**: snake_case (ex: `unique_key`)
- **Constantes**: UPPER_SNAKE_CASE (ex: `REPORTANA_TOKEN`)

### Estrutura de Respostas

Todas as respostas seguem o padrão:

```json
{
  "status": "success|error|partial_success",
  "message": "Mensagem descritiva",
  "data": { ... }
}
```

### Tratamento de Erros

- **400**: Dados inválidos
- **500**: Erro interno
- **503**: Serviço indisponível (health check)

## 🧪 Testes

### Estrutura de Testes

```
orders/
└── tests.py
```

### Tipos de Testes

1. **Testes Unitários**: Services e lógica de negócio
2. **Testes de Integração**: Endpoints e fluxos completos
3. **Testes de API**: Requisições HTTP

## 🔒 Segurança

### Configurações Importantes

- **SECRET_KEY**: Mantido em settings.py (alterar em produção)
- **ALLOWED_HOSTS**: Configurado para desenvolvimento
- **CORS**: Habilitado para todas as origens (ajustar em produção)
- **Autenticação**: Não configurada (adicionar em produção)

## 📊 Monitoramento

### Health Check

- **Endpoint**: `/api/v1/health/`
- **Verifica**: Conexão com banco de dados
- **Retorna**: Status da API

### Logs

- **Framework**: Python logging
- **Nível**: INFO, ERROR
- **Localização**: Console/Arquivo (configurar)

## 🚀 Deploy

### Docker

- **Dockerfile**: Configurado
- **docker-compose.yml**: Configurado
- **Comando**: `docker-compose up -d`

### Variáveis de Ambiente

Configurar:
- `SECRET_KEY`
- `DATABASE_*`
- `ALLOWED_HOSTS`
- `REPORTANA_TOKEN`

## 📚 Documentação

### Documentação Automática

- **Swagger**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI Schema**: `/api/schema/`

### Documentação Manual

- **README.md**: Documentação principal
- **GUIA_INTEGRACAO_N8N.md**: Guia de integração
- **ESTRUTURA_PROJETO.md**: Este arquivo

---

**GEX Corporation** - Estrutura do Projeto v1.0.0

