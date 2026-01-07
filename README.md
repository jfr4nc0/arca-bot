# ArcaBot Automation System

A comprehensive RPA (Robotic Process Automation) system for automating AFIP (Argentina's Federal Tax Authority) workflows, built with FastAPI, Redis, Kafka, Selenium, Docker, and Grafana + Prometheus. The system provides automated debt calculation (CCMA) and tax declaration (DDJJ) workflows with enterprise-grade monitoring and event-driven architecture.

## Table of Contents

- [System Architecture](#system-architecture)
- [Quick Start with Docker Compose](#quick-start-with-docker-compose)
- [Features](#features)
- [API Documentation](#api-documentation)
- [Workflow Types](#workflow-types)
- [Event System](#event-system)
- [Observability & Monitoring](#observability--monitoring)
- [Development Setup](#development-setup)
- [Configuration](#configuration)
- [Production Deployment](#production-deployment)

## System Architecture

The ArcaAutoVep system follows a modern microservices architecture with event-driven patterns:

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   FastAPI App   │────│    Redis     │────│     Kafka       │
│  (Orchestrator) │    │  (Caching &  │    │ (Event Stream)  │
└─────────────────┘    │ Transactions)│    └─────────────────┘
         │             └──────────────┘             │
         │                                          │
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Browser RPA   │    │  Monitoring  │    │   File Storage  │
│   (Selenium)    │    │  (Grafana+   │    │   (VEP PDFs)    │
│                 │    │  Prometheus) │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

### Core Components

- **FastAPI REST API**: Workflow orchestration and status monitoring
- **Redis**: Transaction storage, caching, and duplicate detection
- **Kafka**: Event streaming for workflow completion notifications
- **Selenium WebDriver**: Browser automation for AFIP portal interaction
- **Prometheus + Grafana**: Metrics collection and visualization

## Quick Start with Docker Compose

The recommended way to run ArcaAutoVep is using Docker Compose, which provides a complete stack including all dependencies:

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd ArcaAutoVep-automatizations

# Create environment file
cp .env.example .env
# Edit .env with your AFIP credentials
```

### 2. Start the Complete Stack

Choose between development and production profiles:

```bash
# Development mode (HTTP, no HTTPS redirect, debug-friendly)
docker-compose --profile dev up -d

# Build and recreate containers without dependencies
docker-compose --profile dev up -d --build --force-recreate --no-deps

# Production mode (HTTPS redirect, security middleware)
docker-compose --profile prod up -d

# Verify all services are running
docker-compose ps

# View logs
docker-compose logs -f api
```

### 3. Access Services

- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health
- **Grafana Dashboards**: http://localhost:3000 (admin/ArcaAutoVep123)
- **Prometheus Metrics**: http://localhost:9091
- **Kafka UI**: http://localhost:8080
- **Redis**: localhost:6379

### 4. Execute Your First Workflow

```bash
# Execute CCMA workflow
curl -X POST 'http://localhost:8000/workflows/ccma/execute?headless=false' \
  -H "Content-Type: application/json" \
  -d '{
    "credenciales": {
      "cuit": "20429994323",
      "contraseña": "your_arca_password"
    },
    "veps": [{
        "periodo_desde": "01/2023",
        "periodo_hasta": "12/2025",
        "fecha_calculo": "19/09/2025",
        "tipo_contribuyente": "Monotributo",
        "impuesto": "IVA",
        "metodo_pago": "qr",
        "fecha_expiracion": "2025-12-31",
        "incluir_intereses": True,
    }]
  }'

# Get workflow status
curl http://localhost:8000/workflows/{exchange_id}/status
```

## Features

### Core Capabilities
- **Automated AFIP Authentication**: Secure login to AFIP portal
- **CCMA Workflow**: Complete debt calculation and account status workflow
- **DDJJ Workflow**: Tax declaration submission with multiple entries
- **VEP Generation**: Automatic generation of payment vouchers (VEP)
- **Multi-format Payments**: QR codes, bank transfers, Pago Mis Cuentas
- **Transaction Deduplication**: Prevents duplicate processing using hash-based detection

### Enterprise Features
- **Event-Driven Architecture**: Kafka-based workflow notifications
- **Comprehensive Monitoring**: Golden signals metrics (traffic, latency, errors, saturation)
- **Distributed Tracing**: End-to-end traceability with correlation IDs
- **Automatic Retry Logic**: Built-in retry for transient failures (timeouts, 503s)
- **High Availability**: Stateless design with Redis-based persistence
- **Production Security**: HTTPS enforcement, trusted hosts validation

## API Documentation

### Core Endpoints

#### Execute CCMA Workflow
Initiates debt calculation workflow for AFIP CCMA service.

```http
POST /workflows/ccma/execute?headless=false
Content-Type: application/json

{
    "credenciales": {
      "cuit": "20429994323",
      "contraseña": "your_arca_password"
    },
    "veps": [{
        "periodo_desde": "01/2023",
        "periodo_hasta": "12/2025",
        "fecha_calculo": "19/09/2025",
        "tipo_contribuyente": "Monotributo",
        "impuesto": "IVA",
        "metodo_pago": "qr",
        "fecha_expiracion": "2025-12-31",
        "incluir_intereses": True,
    }]
  }'
```

**Response:**
```json
{
  "exchange_id": "550e8400-e29b-41d4-a716-446655440000",
  "transaction_hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
  "status": "running",
  "message": "Workflow execution started",
  "created_at": "2025-01-15T10:30:00"
}
```

#### Execute DDJJ Workflow
Processes tax declarations with multiple VEP entries.

```http
POST /workflows/ddjj/execute?headless=false
Content-Type: application/json

{
  "credenciales": {
    "cuit": "20123456789",
    "contraseña": "your_arca_password"
  },
  "data": {
    "metodo_pago": "qr",
    "veps": [
      {
        "fecha_expiracion": "2025-12-31",
        "nro_formulario": "1571",
        "cod_tipo_pago": "33",
        "cuit": "20123456789",
        "concepto": "19",
        "sub_concepto": "19",
        "periodo_fiscal": "202412",
        "importe": 300.00,
        "impuesto": "24"
      }
    ]
  }
}
```

#### Get Workflow Status
Retrieves real-time workflow execution status.

```http
GET /workflows/{exchange_id}/status
```

**Response:**
```json
{
  "exchange_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "started_at": "2025-01-15T10:30:00",
  "completed_at": "2025-01-15T10:32:15",
  "results": {
    "workflow_result": {
      "workflow_id": "ccma_workflow",
      "status": "COMPLETED",
      "steps_completed": 7,
      "steps_failed": 0,
      "total_steps": 7,
      "results": {
        "vep_pdf_filename": "vep_20250115_123456.pdf",
        "payment_url": "https://payment.afip.gob.ar/vep?id=12345"
      },
      "errors": null
    }
  },
  "errors": null
}
```

#### Health and System Endpoints

```http
GET /health                    # API health status
GET /metrics                  # Prometheus metrics endpoint
POST /retry?max_retries=3     # Retry failed transactions
```

### Payment Methods

The system supports multiple payment methods for AFIP VEP generation. Use the `form_payment` parameter in your requests:

| Payment Method | Value | Description |
|---|---|---|
| **QR Code** | `"qr"` | Generate QR code for instant payment (default) |
| **Payment Link** | `"link"` | Generate web link for online payment |
| **Pago Mis Cuentas** | `"pago_mis_cuentas"` | Bank transfer via Pago Mis Cuentas |
| **Inter Banking** | `"inter_banking"` | Inter-bank transfer system |
| **XN Group** | `"xn_group"` | XN Group payment method |

If no payment method is specified, the system defaults to `"qr"` (QR code).

## Workflow Types

### CCMA (Cuenta Corriente y Moratoria AFIP)
Automates the complete debt calculation and payment workflow:

1. **AFIP Authentication**: Secure login with CUIT/password
2. **Service Navigation**: Navigate to CCMA service section
3. **Form Completion**: Fill taxpayer information and date ranges
4. **Debt Calculation**: Process debt calculation request
5. **Payment Method Selection**: Choose from available payment options
6. **VEP Generation**: Generate and download payment vouchers
7. **Result Processing**: Extract and store transaction details

### DDJJ (Declaración Jurada)
Processes tax declarations with multiple entries:

1. **Authentication**: Login to AFIP portal
2. **Declaration Setup**: Configure tax period and type
3. **Data Entry**: Process multiple declaration entries
4. **Validation**: Verify declaration data accuracy
5. **Submission**: Submit declarations to AFIP
6. **Confirmation**: Retrieve submission confirmations

## Event System

The system uses Apache Kafka for event-driven workflow notifications:

### Kafka Topics
- **workflow-events**: Workflow completion notifications

### Event Types
```json
{
  "exchange_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_type": "ccma_workflow",
  "timestamp": "2025-01-15T10:32:15",
  "success": true,
  "response": { /* WorkflowStatusResponse */ },
  "error_details": null
}
```

### Consumer Integration
External systems can consume workflow events:

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'workflow-events',
    bootstrap_servers=['localhost:29092'],
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)

for message in consumer:
    workflow_event = message.value
    print(f"Workflow {workflow_event['exchange_id']} completed: {workflow_event['success']}")
```

## Observability & Monitoring

### Monitoring Stack Components

#### Grafana Dashboards
- **ArcaAutoVep Overview**: Business metrics, success/failure rates by workflow type
- **Golden Signals**: Request rate, response time, error rate, active workflows
- **System Health**: Redis connections, Kafka throughput, browser sessions

#### Prometheus Metrics
Key metrics exposed at `/metrics`:

```
# Business Metrics
ArcaAutoVep_workflow_total{workflow_type="ccma", status="success"} 150
ArcaAutoVep_workflow_total{workflow_type="ccma", status="failed"} 3

# Performance Metrics
ArcaAutoVep_workflow_duration_seconds{workflow_type="ccma"} 45.2
ArcaAutoVep_vep_generation_total{payment_method="qr_code"} 75

# System Metrics
ArcaAutoVep_active_workflows_gauge 5
ArcaAutoVep_http_requests_total{method="POST", endpoint="/workflows/ccma/execute"} 200
```

#### Centralized Logging
Structured logging with complete traceability:

```bash
# View logs for specific workflow
docker-compose logs api | grep "exchange_id=550e8400"

# Alternative: Check application logs directly
docker-compose logs api | grep "workflow"
```

### Starting Monitoring Stack

```bash
# Start complete observability stack
docker-compose up -d prometheus grafana

# Verify services
docker-compose ps | grep -E "(prometheus|grafana)"

# Access dashboards
echo "Grafana: http://localhost:3000 (admin/ArcaAutoVep123)"
echo "Prometheus: http://localhost:9091"
```

## Development Setup

### Prerequisites
- Python 3.12+
- Poetry
- Docker & Docker Compose
- Chrome or Firefox browser

### Local Development

```bash
# Install dependencies
poetry install

# Setup development environment
cp .env.example .env
# Configure AFIP credentials and settings

# Start dependencies only
docker-compose up -d redis kafka zookeeper

# Run API locally
poetry run python -m api.main

# Run tests
poetry run pytest

# Code formatting
poetry run black .
poetry run isort .

# Pre-commit hooks
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# AFIP Credentials (Required)
AFIP_CUIT=your_cuit_here
AFIP_PASSWORD=your_password_here

# API Configuration
REDIS_URL=redis://localhost:6379
REDIS_ENABLED=true
ENVIRONMENT=development

# Browser Configuration
HEADLESS=false

# Retry Configuration
MAX_RETRY_ATTEMPTS=3

# Google Drive Uploads
GOOGLE_CREDENTIALS_PATH=secrets/google_credentials.json
GOOGLE_TOKEN_PATH=secrets/google_token.json
DRIVE_UPLOAD_ACTIVE=false

# Security (Production)
API_TITLE="ArcaAutoVep RPA API"
API_DESCRIPTION="RPA automation for AFIP workflows"
API_VERSION="1.0.0"
```

Set `DRIVE_UPLOAD_ACTIVE=true` to push generated VEP PDFs and QR images to the Google Drive account defined by `GOOGLE_CREDENTIALS_PATH`/`GOOGLE_TOKEN_PATH`. Leave it `false` for local-only debugging.

To manually test the Drive integration with existing artifacts, run:

```bash
python scripts/google_drive_upload_test.py
```

The helper picks any PDFs under `resources/pdf` and PNGs under `resources/qr` and uploads them using the configured credentials.

### Service Configuration

#### Docker Compose Profiles
```bash
# Start only core services
docker-compose --profile core up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# Start everything
docker-compose up -d
```

#### Custom Configuration
- **Prometheus**: `/home/jcanossa/workspace/ArcaAutoVep-automatizations/monitoring/prometheus.yml`
- **Grafana Datasources**: `/home/jcanossa/workspace/ArcaAutoVep-automatizations/monitoring/grafana/datasources/`

## Production Deployment

### Security Considerations
- Use secure AFIP credentials storage (HashiCorp Vault, AWS Secrets Manager)
- Enable HTTPS with proper TLS certificates
- Configure firewall rules to restrict access
- Regular security updates for all components

### Scalability
- **Horizontal Scaling**: Deploy multiple API instances behind load balancer
- **Database**: Use Redis Cluster for high availability
- **Message Queue**: Kafka cluster with multiple brokers
- **Monitoring**: Configure alerting rules for production metrics

### Backup Strategy
- **Redis Snapshots**: Automated backup of transaction data
- **Configuration**: Version control all configuration files
- **Logs**: Archive logs to long-term storage
- **VEP Files**: Backup generated payment vouchers

### Deployment Commands

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Health checks
curl http://localhost:8000/health

# Monitor services
docker-compose logs -f --tail=100

# Backup Redis data
docker-compose exec redis redis-cli BGSAVE
```

### Environment-Specific Overrides

Create `docker-compose.prod.yml` for production overrides:

```yaml
version: '3.8'
services:
  api:
    environment:
      - ENVIRONMENT=production
      - HEADLESS=true
    restart: always

  redis:
    volumes:
      - /var/lib/redis:/data
    restart: always
```

## Requirements

- **Python**: 3.12+
- **Browser**: Chrome/Chromium or Firefox with WebDriver support
- **Memory**: Minimum 4GB RAM (8GB recommended for full stack)
- **Storage**: 10GB available disk space
- **Network**: Stable internet connection for AFIP portal access

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the [API documentation](http://localhost:8000/docs) when running locally
2. Review logs using `docker-compose logs -f api`
3. Monitor system health via Grafana dashboards
4. Check Kafka events for workflow completion status

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**ArcaAutoVep RPA System** - Automating AFIP workflows with enterprise-grade reliability and monitoring.
