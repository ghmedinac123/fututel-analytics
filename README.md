# 🚀 FUTUISP Analytics - Microservicio de Análisis de Pagos

Microservicio Python para análisis estadístico de comportamiento de pagos en FUTUISP, implementado con arquitectura hexagonal (puertos y adaptadores).

## 📋 Características

- **Análisis de comportamiento de pagos** clasificado en períodos:

  - 🟢 **ÓPTIMO**: Pagos días 1-10 (100% rendimiento)
  - 🟡 **ACEPTABLE**: Pagos días 11-corte (75% rendimiento)
  - 🔴 **CRÍTICO**: Pagos post-corte (40% rendimiento)
  - ⚪ **PENDIENTE**: Facturas sin pagar

- **Stack Tecnológico**:

  - Python 3.12
  - FastAPI (API REST)
  - SQLAlchemy (ORM async)
  - Redis (caché)
  - Docker & Docker Compose
  - UV (gestor de dependencias)

- **Arquitectura Hexagonal**:

```
  Domain (Entities, Value Objects)
    ↓
  Application (Use Cases, Ports)
    ↓
  Infrastructure (Repositories, DB, Cache)
    ↓
  Interfaces (REST API, CLI)
```

## 🏗️ Estructura del Proyecto

```
futuisp-analytics/
├── src/futuisp_analytics/
│   ├── domain/              # Lógica de negocio
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── services/
│   ├── application/         # Casos de uso
│   │   ├── use_cases/
│   │   └── ports/
│   ├── infrastructure/      # Implementaciones
│   │   ├── database/
│   │   ├── cache/
│   │   └── config/
│   └── interfaces/          # APIs y CLI
│       └── api/v1/
├── tests/
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## 🚀 Instalación

### **Requisitos**

- Python 3.12+
- Docker & Docker Compose
- UV (instalador de paquetes)
- Acceso a base de datos MySQL

### **Setup Desarrollo**

```bash
# 1. Clonar repositorio
cd /home/futuisp-analytics/futuisp-analytics

# 2. Crear entorno virtual con UV
uv venv
source .venv/bin/activate

# 3. Instalar dependencias
uv pip install -e .

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Levantar Redis
docker compose -f docker-compose.dev.yml up -d

# 6. Ejecutar aplicación
uvicorn futuisp_analytics.interfaces.api.main:app --reload --host 0.0.0.0 --port 12048
```

## 🔧 Configuración (.env)

```bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mysql
DB_USER=root
DB_PASSWORD=your_password

# API
API_HOST=0.0.0.0
API_PORT=12048
API_RELOAD=true

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_TTL=300

# App
DEBUG=true
```

## 📡 Endpoints API

### **Health Check**

```bash
GET /api/v1/health

Response:
{
  "status": "healthy",
  "service": "FUTUISP Analytics",
  "version": "0.1.0",
  "database": "connected",
  "redis": "connected"
}
```

### **Análisis de Comportamiento de Pagos**

```bash
GET /api/v1/analytics/payment-behavior
  ?fecha_inicio=2024-10-01
  &fecha_fin=2024-11-01
  &zona_id=1  # Opcional

Response:
{
  "periodo": "2024-10",
  "total_facturas": 5377,
  "metricas": {
    "OPTIMO": {
      "cantidad_usuarios": 3500,
      "monto_total": 140000000.00,
      "porcentaje": 65.12,
      "dias_promedio_pago": 5.2,
      "rendimiento": 100
    },
    "ACEPTABLE": { ... },
    "CRITICO": { ... },
    "PENDIENTE": { ... }
  }
}
```

### **Limpiar Caché**

```bash
DELETE /api/v1/analytics/cache/clear?pattern=metricas:*
```

## 🧪 Testing

```bash
# Health check
curl http://localhost:12048/api/v1/health

# Métricas con timing
time curl "http://localhost:12048/api/v1/analytics/payment-behavior?fecha_inicio=2024-10-01&fecha_fin=2024-11-01"

# Documentación interactiva
http://localhost:12048/docs
```

## 🐳 Despliegue con Docker

### **Desarrollo (solo Redis)**

```bash
docker compose -f docker-compose.dev.yml up -d
```

### **Producción (completo)**

```bash
# Generar requirements.txt
uv pip compile pyproject.toml -o requirements.txt

# Build y deploy
docker compose up -d --build

# Ver logs
docker compose logs -f api
```

## 📊 Optimizaciones Implementadas

1. **Caché con Redis**: Resultados cacheados 5 minutos
2. **Connection Pool**: 10 conexiones con 20 overflow
3. **Async/Await**: Operaciones no bloqueantes
4. **Logging estructurado**: Trazabilidad completa

## 🔒 Seguridad

- Conexiones a BD solo desde IPs autorizadas (iptables)
- Variables sensibles en `.env` (no versionado)
- SQL injection protegido por SQLAlchemy ORM
- CORS configurado para producción

## 🛠️ Desarrollo

### **Agregar nueva dependencia**

```bash
uv pip install nombre-paquete
```

### **Ejecutar con auto-reload**

```bash
uvicorn futuisp_analytics.interfaces.api.main:app --reload
```

### **Ver logs detallados**

```bash
# En .env cambiar DEBUG=true
```

## 📈 Próximas Funcionalidades

- [ ] Análisis histórico (6+ meses)
- [ ] Predicción de morosidad con ML
- [ ] Reportes exportables (PDF/Excel)
- [ ] Webhooks para notificaciones
- [ ] Dashboard web interactivo

## 🤝 Contribución

1. Fork del proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar funcionalidad X'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

## 📞 Soporte

- **Issues**: GitHub Issues
- **Email**: soporte@fututel.com
- **Documentación**: http://localhost:12048/docs

## 📝 Licencia

Propiedad de FUTUISP - Todos los derechos reservados

---

**Versión**: 0.1.0  
**Última actualización**: Noviembre 2025
docker compose down && docker compose build --no-cache api && docker compose up -d
docker exec -it futuisp-redis redis-cli FLUSHALL
# fututel-analytics
