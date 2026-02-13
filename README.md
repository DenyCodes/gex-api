# GEX Corporation API
# DESENVOLVIDO POR DENIS OLIVEIRA
API REST oficial da GEX Corporation desenvolvida com Django REST Framework para integração com n8n e outras plataformas. Gerencia eventos de negócio, abandono de carrinho, compras aprovadas, leads e fluxos de dados da empresa.

## 📋 Índice

- [Características](#-características)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Documentação da API](#-documentação-da-api)
- [Tipos de Eventos](#-tipos-de-eventos)
- [Integração com n8n](#-integração-com-n8n)
- [Endpoints](#-endpoints)
- [Exemplos de Uso](#-exemplos-de-uso)
- [Docker](#-docker)
- [Segurança](#-segurança)

## 🚀 Características

- ✅ **API RESTful completa** com operações CRUD
- ✅ **Normalização automática de dados** - Aceita dados de QUALQUER formato e plataforma
- ✅ **Detecção automática de plataforma** - Hotmart, Kiwify, Braip, Eduzz e mais
- ✅ **Transformação inteligente** - Converte automaticamente para formato padrão
- ✅ **Lógica de negócio especializada** para diferentes tipos de eventos
- ✅ **Documentação OpenAPI/Swagger** para fácil integração
- ✅ **Webhooks otimizados** - n8n pode enviar dados brutos sem transformação
- ✅ **Processamento inteligente** de abandono de carrinho, compras aprovadas e leads
- ✅ **Validação e limpeza automática** de dados (emails, telefones, valores)
- ✅ **Geração automática de campos** faltantes (unique_key, event_type, etc.)
- ✅ **Filtros e busca avançada** para consultas flexíveis
- ✅ **Paginação** para grandes volumes de dados
- ✅ **Health check** para monitoramento
- ✅ **Tratamento de erros padronizado** com respostas consistentes

## 📋 Pré-requisitos

- Python 3.8 ou superior
- MySQL (banco de dados configurado)
- pip (gerenciador de pacotes Python)

## 🔧 Instalação

### 1. Clone o repositório

```bash
git clone <seu-repositorio>
cd reportana
```

### 2. Crie e ative um ambiente virtual

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o banco de dados

Edite o arquivo `core/settings.py` e configure as credenciais do MySQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'seu_banco',
        'USER': 'seu_usuario',
        'PASSWORD': 'sua_senha',
        'HOST': 'seu_host',
        'PORT': '3306',
    }
}
```

### 5. Execute as migrações (se necessário)

```bash
python manage.py migrate
```

### 6. Inicie o servidor

```bash
python manage.py runserver
```

A API estará disponível em `http://localhost:8000`

## 📚 Documentação da API

### Acessar Documentação Interativa

Após iniciar o servidor, acesse:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Schema OpenAPI**: http://localhost:8000/api/schema/

## 🎯 Tipos de Eventos

A API da GEX Corporation processa diferentes tipos de eventos com lógicas de negócio específicas:

### 1. Abandono de Carrinho (`cart_abandonment`)

**Descrição:** Eventos de carrinho abandonado pelo cliente.

**Lógica de Negócio:**
- Salva o evento no banco de dados
- Envia mensagem de recuperação via Reportana
- Prioriza leads com valor alto de carrinho (> R$ 500)
- Classifica urgência baseada no valor do carrinho

**Campos Especiais:**
- `cart_amount`: Valor do carrinho abandonado

### 2. Compras Aprovadas (`purchase_approved`)

**Descrição:** Eventos de compras que foram aprovadas.

**Lógica de Negócio:**
- Salva a compra no banco de dados
- Envia mensagem de confirmação e boas-vindas
- Prioriza compras de alto valor (> R$ 1.000)
- Classifica prioridade baseada no valor da compra

**Campos Especiais:**
- `order_amount`: Valor da compra aprovada

### 3. Leads (`lead`)

**Descrição:** Novos leads capturados.

**Lógica de Negócio:**
- Salva o lead no banco de dados
- Envia para nurturing via Reportana
- Calcula score de qualidade do lead automaticamente
- Classifica leads como high, medium ou low

**Critérios de Score:**
- Email válido: +1 ponto
- Telefone presente: +1 ponto
- Nome completo: +1 ponto
- Produto de interesse: +1 ponto

**Campos Especiais:**
- `source`: Origem do lead (ex: facebook, google, etc.)

### 4. Eventos Genéricos

Qualquer outro tipo de evento é processado de forma genérica, mantendo compatibilidade com diferentes plataformas.

## 🔗 Integração com n8n

### ⚡ Configuração Simplificada

A API faz TODO o trabalho pesado! O n8n só precisa enviar os dados brutos.

1. **Adicionar nó HTTP Request no n8n:**
   - Método: `POST`
   - URL: `http://seu-servidor:8000/api/v1/webhook/`
   - Authentication: None (ou configure se necessário)
   - Body: JSON

2. **Enviar dados brutos (SIMPLES!):**

```json
{{ $json }}
```

**Isso é tudo!** A API:
- ✅ Detecta automaticamente a plataforma (Hotmart, Kiwify, etc.)
- ✅ Normaliza todos os campos automaticamente
- ✅ Gera `unique_key` se não existir
- ✅ Detecta `event_type` automaticamente
- ✅ Limpa e valida emails, telefones e valores
- ✅ Separa nome completo em primeiro/último nome
- ✅ Converte valores monetários para formato padrão

### Exemplo: Hotmart

**Antes (complexo no n8n):**
```json
{
    "unique_key": "={{ $json.data.purchase.order.order_id }}",
    "order_id": "={{ $json.data.purchase.order.order_id }}",
    "event_type": "={{ $json.event }}",
    "client_email": "={{ $json.data.purchase.buyer.email }}",
    "client_first_name": "={{ $json.data.purchase.buyer.name.split(' ')[0] }}",
    "client_last_name": "={{ $json.data.purchase.buyer.name.split(' ').slice(1).join(' ') }}",
    "client_phone": "={{ $json.data.purchase.buyer.phone.number }}",
    "product_name": "={{ $json.data.purchase.product.name }}",
    "order_amount": "={{ $json.data.purchase.order.price.value }}",
    "platform": "hotmart"
}
```

**Agora (simples no n8n):**
```json
{{ $json }}
```

A API faz toda a transformação automaticamente!

### Workflows Recomendados

#### Workflow para Abandono de Carrinho

1. Webhook recebe evento de carrinho abandonado
2. Envia para `/api/v1/webhook/cart-abandonment/`
3. API processa e envia para Reportana
4. Resposta de sucesso/erro

#### Workflow para Compras Aprovadas

1. Webhook recebe evento de compra aprovada
2. Envia para `/api/v1/webhook/purchase-approved/`
3. API processa e envia mensagem de boas-vindas
4. Resposta de sucesso/erro

#### Workflow para Leads

1. Webhook recebe novo lead
2. Envia para `/api/v1/webhook/lead/`
3. API calcula score e envia para nurturing
4. Resposta com score do lead

## 📡 Endpoints

### Health Check

**GET** `/api/v1/health/`

Verifica se a API está funcionando normalmente.

**Resposta de Sucesso (200):**
```json
{
    "status": "healthy",
    "service": "gex-corporation-api",
    "version": "1.0.0",
    "timestamp": "2024-01-01T12:00:00Z",
    "database": "connected"
}
```

### Webhook Principal

**POST** `/api/v1/webhook/`

Endpoint principal que processa qualquer tipo de evento automaticamente.

**Payload:**
```json
{
    "unique_key": "ORD-12345",
    "order_id": "12345",
    "event_type": "cart_abandonment",
    "client_email": "cliente@example.com",
    "client_first_name": "João",
    "client_last_name": "Silva",
    "client_phone": "+5511999999999",
    "product_name": "Curso de Python",
    "order_amount": 299.90,
    "platform": "hotmart"
}
```

**Tipos de evento suportados:**
- `cart_abandonment` ou `abandono_carrinho`
- `purchase_approved` ou `compra_aprovada`
- `lead` ou `novo_lead`
- Qualquer outro (processado como genérico)

### Webhook - Abandono de Carrinho

**POST** `/api/v1/webhook/cart-abandonment/`

Endpoint específico para abandono de carrinho.

**Payload:**
```json
{
    "unique_key": "CART-12345",
    "order_id": "12345",
    "client_email": "cliente@example.com",
    "client_first_name": "João",
    "client_last_name": "Silva",
    "client_phone": "+5511999999999",
    "product_name": "Curso de Python",
    "cart_amount": 299.90,
    "platform": "hotmart"
}
```

**Resposta:**
```json
{
    "status": "success",
    "message": "Abandono de carrinho processado. Enviado com sucesso",
    "data": {
        "unique_key": "CART-12345",
        "order_id": "12345",
        "event_type": "cart_abandonment",
        "status_whatsapp": "SENT",
        "created": true,
        "cart_value": "299.90"
    }
}
```

### Webhook - Compra Aprovada

**POST** `/api/v1/webhook/purchase-approved/`

Endpoint específico para compras aprovadas.

**Payload:**
```json
{
    "unique_key": "PURCH-12345",
    "order_id": "12345",
    "client_email": "cliente@example.com",
    "client_first_name": "João",
    "client_last_name": "Silva",
    "client_phone": "+5511999999999",
    "product_name": "Curso de Python",
    "order_amount": 299.90,
    "platform": "hotmart"
}
```

**Resposta:**
```json
{
    "status": "success",
    "message": "Compra aprovada processada. Enviado com sucesso",
    "data": {
        "unique_key": "PURCH-12345",
        "order_id": "12345",
        "event_type": "purchase_approved",
        "status_whatsapp": "SENT",
        "created": true,
        "purchase_value": "299.90"
    }
}
```

### Webhook - Lead

**POST** `/api/v1/webhook/lead/`

Endpoint específico para novos leads.

**Payload:**
```json
{
    "unique_key": "LEAD-12345",
    "order_id": "12345",
    "client_email": "cliente@example.com",
    "client_first_name": "João",
    "client_last_name": "Silva",
    "client_phone": "+5511999999999",
    "product_name": "Curso de Python",
    "source": "facebook",
    "platform": "hotmart"
}
```

**Resposta:**
```json
{
    "status": "success",
    "message": "Lead processado. Enviado com sucesso",
    "data": {
        "unique_key": "LEAD-12345",
        "order_id": "12345",
        "event_type": "lead",
        "status_whatsapp": "SENT",
        "created": true,
        "lead_score": "high"
    }
}
```

### Listar Eventos

**GET** `/api/v1/orders/`

Lista todos os eventos com paginação e filtros.

**Query Parameters:**
- `page`: Número da página (padrão: 1)
- `page_size`: Itens por página (padrão: 50, máximo: 1000)
- `event_type`: Filtrar por tipo de evento
- `status_whatsapp`: Filtrar por status do WhatsApp
- `platform`: Filtrar por plataforma
- `search`: Buscar por nome, email, telefone ou produto
- `ordering`: Ordenar resultados (ex: `-unique_key` para mais recentes)

**Exemplos:**
```
GET /api/v1/orders/?event_type=cart_abandonment
GET /api/v1/orders/?status_whatsapp=SENT
GET /api/v1/orders/?search=joao
GET /api/v1/orders/?page=2&page_size=20
GET /api/v1/orders/?ordering=-unique_key
```

### Detalhes de um Evento

**GET** `/api/v1/orders/{unique_key}/`

Retorna os detalhes de um evento específico.

### Criar Evento

**POST** `/api/v1/orders/`

Cria um novo evento manualmente.

### Atualizar Evento

**PUT** `/api/v1/orders/{unique_key}/` - Atualização completa
**PATCH** `/api/v1/orders/{unique_key}/` - Atualização parcial

### Atualizar Status do WhatsApp

**PATCH** `/api/v1/orders/{unique_key}/update_status/`

Atualiza apenas o status do WhatsApp.

**Payload:**
```json
{
    "status_whatsapp": "SENT"
}
```

### Deletar Evento

**DELETE** `/api/v1/orders/{unique_key}/`

Remove um evento.

## 💡 Exemplos de Uso

### Exemplo 1: Enviar Abandono de Carrinho

```bash
curl -X POST http://localhost:8000/api/v1/webhook/cart-abandonment/ \
  -H "Content-Type: application/json" \
  -d '{
    "unique_key": "CART-12345",
    "order_id": "12345",
    "client_email": "cliente@example.com",
    "client_first_name": "João",
    "client_last_name": "Silva",
    "client_phone": "+5511999999999",
    "product_name": "Curso de Python",
    "cart_amount": 299.90,
    "platform": "hotmart"
  }'
```

### Exemplo 2: Enviar Compra Aprovada

```bash
curl -X POST http://localhost:8000/api/v1/webhook/purchase-approved/ \
  -H "Content-Type: application/json" \
  -d '{
    "unique_key": "PURCH-12345",
    "order_id": "12345",
    "client_email": "cliente@example.com",
    "client_first_name": "João",
    "client_last_name": "Silva",
    "client_phone": "+5511999999999",
    "product_name": "Curso de Python",
    "order_amount": 299.90,
    "platform": "hotmart"
  }'
```

### Exemplo 3: Listar Abandonos de Carrinho

```bash
curl "http://localhost:8000/api/v1/orders/?event_type=cart_abandonment&page=1&page_size=20"
```

## 🐳 Docker

O projeto inclui configuração Docker. Para usar:

```bash
docker-compose up -d
```

## 🔒 Segurança

⚠️ **Importante para Produção:**

1. Altere `SECRET_KEY` no `settings.py`
2. Configure `ALLOWED_HOSTS` adequadamente
3. Configure autenticação (Token, JWT, etc.)
4. Use HTTPS em produção
5. Configure CORS adequadamente
6. Mantenha as credenciais do banco de dados seguras

## 📝 Status do WhatsApp

Os possíveis valores para `status_whatsapp`:

- `WAITING`: Aguardando processamento
- `PROCESSING`: Em processamento
- `SENT`: Enviado com sucesso
- `ERROR_REPORTANA`: Erro ao enviar para Reportana
- `TIMEOUT_REPORTANA`: Timeout na conexão com Reportana

## 📊 Estrutura do Projeto

```
reportana/
├── core/                 # Configurações principais do Django
│   ├── settings.py       # Configurações da aplicação
│   ├── urls.py          # Rotas da API
│   └── ...
├── orders/               # App principal de eventos
│   ├── models.py        # Modelos de dados
│   ├── views.py         # Views e endpoints
│   ├── serializers.py   # Serializadores
│   ├── services.py      # Lógica de negócio
│   └── ...
├── requirements.txt     # Dependências do projeto
├── README.md           # Esta documentação
└── ...
```

## 🤝 Suporte

Para dúvidas ou problemas:

1. Consulte a documentação Swagger em `/api/docs/`
2. Verifique os logs da aplicação
3. Entre em contato com a equipe de desenvolvimento

## 📄 Licença

Este projeto é propriedade da GEX Corporation e é de uso interno.

---

**GEX Corporation API v1.0.0** - Desenvolvido para integração com n8n e outras plataformas.
