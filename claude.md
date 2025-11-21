# 🤖 Guía para Claude AI - FUTUISP Analytics

## Contexto del Proyecto

Este es un **microservicio de análisis de pagos** para un ISP (proveedor de internet) implementado con:
- Python 3.12 + FastAPI
- Arquitectura Hexagonal
- SQLAlchemy async + MySQL
- Redis para caché

## Objetivo Principal

Clasificar clientes según su comportamiento de pago en 4 períodos:
1. **ÓPTIMO** (1-10): Pagan puntual
2. **ACEPTABLE** (11-corte): Pagan antes de suspensión
3. **CRÍTICO** (post-corte): Pagaron tarde/suspendidos
4. **PENDIENTE**: No han pagado

## Estructura de Código
```
domain/          → Lógica de negocio pura (sin dependencias externas)
application/     → Casos de uso (orquestan el dominio)
infrastructure/  → Implementaciones concretas (BD, caché, config)
interfaces/      → APIs REST, CLI (entrada/salida del sistema)
```

## Principios de Diseño Aplicados

1. **Dependency Inversion**: Interfaces (ports) definen contratos, infraestructura los implementa
2. **Single Responsibility**: Cada clase tiene un propósito único
3. **Inmutabilidad**: Entidades con `@dataclass(frozen=True)`
4. **Async/Await**: Todas las operaciones I/O son asíncronas

## Cómo Ayudar al Desarrollador

### Cuando pida agregar funcionalidad nueva:

1. **Primero preguntar**:
   - ¿Es lógica de negocio (domain) o infraestructura?
   - ¿Qué casos de uso afecta?
   - ¿Necesita almacenamiento/caché nuevo?

2. **Luego sugerir estructura**:
```python
   # Si es negocio → domain/entities o value_objects
   # Si es operación → application/use_cases
   # Si es DB/API → infrastructure o interfaces
```

3. **Mantener separación de capas**:
   - Domain NUNCA importa de infrastructure
   - Application solo conoce ports (interfaces)
   - Infrastructure implementa ports

### Cuando pida debugging:

1. **Verificar orden de dependencias**:
```bash
   # ¿Están todos los __init__.py?
   # ¿Los imports son circulares?
```

2. **Revisar logs estructurados**:
```python
   logger.info(f"🔍 Variable: {valor}")
```

3. **Verificar .env**:
   - ¿DB_PASSWORD tiene caracteres especiales? → quote_plus()
   - ¿DB_HOST tiene https://? → removerlo

### Cuando pida optimización:

1. **Medir primero**:
```bash
   time curl "http://localhost:12048/api/v1/..."
```

2. **Sugerir en orden**:
   - Caché (ya implementado con Redis)
   - Índices SQL (si queries > 3s)
   - Batch processing (si cálculos pesados)
   - Polars/Pandas (último recurso, preferir SQL)

### Cuando pida integración PHP:
```php
// Wrapper simple
function obtener_metricas_pagos($mes) {
    $url = "http://localhost:12048/api/v1/analytics/payment-behavior";
    $params = http_build_query([
        'fecha_inicio' => "$mes-01",
        'fecha_fin' => date('Y-m-d', strtotime("$mes-01 +1 month"))
    ]);
    
    $response = file_get_contents("$url?$params");
    return json_decode($response, true);
}
```

## Queries SQL Complejos

El repositorio usa **subconsultas** para optimizar:
```python
# ❌ MALO: Función agregada por cada fila
SELECT f.id, MIN(o.fecha_pago) FROM facturas f JOIN operaciones o ...

# ✅ BUENO: Subconsulta agrega primero
subq = select(MIN(o.fecha_pago)).group_by(o.nfactura).subquery()
query = select(f.id, subq.c.fecha_pago).join(subq, ...)
```

## Manejo de Errores Común

### Error: "cannot import name X"
→ Verificar que el archivo X.py existe en la carpeta correcta
→ Verificar que __init__.py exporta X

### Error: "invalid literal for int()"
→ .env tiene valor vacío o inválido
→ Agregar default en settings.py

### Error: "Can't connect to MySQL"
→ Probar conexión manual: `mysql -h HOST -u USER -p`
→ Verificar iptables/firewall

## Testing Sugerido
```python
# Unit tests (domain)
def test_clasificar_periodo_optimo():
    analisis = AnalisisPago(
        fecha_emision=date(2024, 10, 1),
        fecha_primer_pago=date(2024, 10, 5),
        ...
    )
    assert analisis.periodo_pago == PeriodoPago.OPTIMO

# Integration tests (repository)
@pytest.mark.asyncio
async def test_obtener_metricas_mes(db_session):
    repo = FacturaRepositoryImpl(db_session)
    metricas = await repo.obtener_metricas_agregadas(
        date(2024, 10, 1),
        date(2024, 11, 1)
    )
    assert "OPTIMO" in metricas["metricas"]
```

## Comandos de Desarrollo Rápidos
```bash
# Reinstalar todo limpio
uv pip install -e . --force-reinstall

# Ver dependencias instaladas
uv pip list | grep -E "(fastapi|sqlalchemy|redis)"

# Logs de Redis
docker compose -f docker-compose.dev.yml logs -f redis

# Ejecutar con más workers (producción)
uvicorn futuisp_analytics.interfaces.api.main:app --workers 4 --host 0.0.0.0 --port 12048
```

## Reglas de Oro al Modificar Código

1. **NO romper arquitectura hexagonal**
   - Domain independiente siempre
   - Infrastructure nunca en domain

2. **NO agregar dependencias sin justificar**
   - ¿Realmente necesitas Pandas? ¿O basta SQL?

3. **SÍ usar logging estructurado**
```python
   logger.info("📊 Procesando facturas", extra={"count": len(facturas)})
```

4. **SÍ agregar type hints**
```python
   def procesar(data: list[dict]) -> dict[str, Any]:
```

5. **SÍ escribir docstrings**
```python
   """
   Calcula métricas de pago.
   
   Args:
       fecha_inicio: Inicio del período
       fecha_fin: Fin del período
   
   Returns:
       Dict con métricas agregadas
   """
```

## Ejemplo de Nueva Funcionalidad

Si el usuario pide: "Agregar análisis por forma de pago"
```python
# 1. Domain (value object)
class FormaPago(str, Enum):
    EFECTIVO = "efectivo"
    TRANSFERENCIA = "transferencia"
    TARJETA = "tarjeta"

# 2. Application (caso de uso)
class ObtenerMetricasPorFormaPago:
    async def execute(self, mes: str) -> dict:
        return await self.repo.obtener_metricas_forma_pago(mes)

# 3. Infrastructure (repository)
class FacturaRepositoryImpl:
    async def obtener_metricas_forma_pago(self, mes: str) -> dict:
        # Query SQL aquí
        pass

# 4. Interfaces (endpoint)
@router.get("/analytics/by-payment-method")
async def obtener_por_forma_pago(...):
    use_case = ObtenerMetricasPorFormaPago(repo)
    return await use_case.execute(mes)
```

## Recursos Externos

- **FastAPI docs**: https://fastapi.tiangolo.com
- **SQLAlchemy async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Hexagonal Architecture**: https://netflixtechblog.com/ready-for-changes-with-hexagonal-architecture-b315ec967749

---

**Última actualización**: 2025-11-05  
**Mantenido por**: Equipo FUTUISP
