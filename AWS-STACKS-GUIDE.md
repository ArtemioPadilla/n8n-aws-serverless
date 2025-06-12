# Guía de Stacks AWS para n8n Serverless

## 📋 Resumen de Stacks Disponibles

El proyecto está organizado en **8 stacks modulares** que se pueden combinar según tus necesidades:

### 1. **NetworkStack** (Opcional)
- **Propósito**: Crear VPC, subnets, security groups
- **Cuándo lo necesitas**: Si no tienes una VPC existente
- **Costo**: $0/mes (recursos de red son gratuitos)

### 2. **StorageStack** (Requerido)
- **Propósito**: Sistema de archivos EFS para persistencia
- **Incluye**: EFS, backups, lifecycle policies
- **Costo**: ~$3-5/mes (con lifecycle policies)

### 3. **DatabaseStack** (Opcional)
- **Propósito**: Base de datos PostgreSQL
- **Opciones**: RDS o Aurora Serverless
- **Costo**: 
  - RDS: ~$15/mes (db.t3.micro)
  - Aurora Serverless: ~$0.12/hora cuando está activo

### 4. **ComputeStack** (Requerido)
- **Propósito**: ECS Fargate para ejecutar n8n
- **Incluye**: Cluster ECS, Task Definition, Service
- **Costo**: 
  - Con Spot (80%): ~$3-5/mes
  - Sin Spot: ~$15-20/mes

### 5. **AccessStack** (Requerido)
- **Propósito**: Exponer n8n a internet
- **Incluye**: API Gateway HTTP API
- **Opciones**: CloudFront, WAF
- **Costo**: 
  - API Gateway solo: ~$1/mes
  - Con CloudFront: +$0-5/mes

### 6. **MonitoringStack** (Opcional)
- **Propósito**: CloudWatch dashboards y alertas
- **Incluye**: Logs, métricas, alarmas, SNS
- **Costo**: ~$5-10/mes

## 🚀 Opciones de Despliegue

### Opción 1: **Minimal** (~$5-10/mes)
La configuración más simple y económica:

```bash
# Usar el stack type "minimal"
cdk deploy -c environment=dev -c stack_type=minimal
```

**Incluye**:
- ✅ StorageStack (EFS para SQLite)
- ✅ ComputeStack (Fargate con Spot)
- ✅ AccessStack (API Gateway)
- ❌ No incluye base de datos (usa SQLite)
- ❌ No incluye monitoreo

**Arquitectura**:
```
Internet → API Gateway → Fargate (n8n) → EFS (SQLite)
```

### Opción 2: **Standard** (~$15-30/mes)
Incluye monitoreo y backups:

```bash
cdk deploy -c environment=dev -c stack_type=standard
```

**Incluye**:
- ✅ Todo de Minimal
- ✅ MonitoringStack
- ✅ Backups automáticos
- ✅ CloudFront (opcional)

### Opción 3: **Enterprise** (~$50-100/mes)
Para producción con alta disponibilidad:

```bash
cdk deploy -c environment=production -c stack_type=enterprise
```

**Incluye**:
- ✅ Todo de Standard
- ✅ DatabaseStack (PostgreSQL)
- ✅ WAF
- ✅ Multi-AZ
- ✅ Auto-scaling

## 🎯 Recomendación: Empieza con Minimal

Para empezar con **UN SOLO COMANDO**:

```bash
# 1. Actualiza tu cuenta AWS en system.yaml
vim system.yaml
# Cambia la línea 46: account: "123456789012" por tu cuenta real

# 2. Despliega el stack minimal
cdk deploy -c environment=dev -c stack_type=minimal --all
```

Esto creará:
1. **EFS** para almacenar datos de n8n
2. **Fargate** ejecutando n8n (con 80% Spot para ahorrar)
3. **API Gateway** para acceder a n8n

## 📊 Análisis de Costos Detallado

### Stack Minimal (dev)
| Servicio | Configuración | Costo Estimado |
|----------|--------------|----------------|
| EFS | 1GB con lifecycle | $0.30/mes |
| Fargate | 0.25 vCPU, 0.5GB RAM, 80% Spot | $3-5/mes |
| API Gateway | HTTP API, <1M requests | $1/mes |
| **TOTAL** | | **~$5-10/mes** |

### ¿Por qué tan barato?
1. **Fargate Spot**: 70-80% de descuento
2. **EFS Lifecycle**: Mueve archivos viejos a almacenamiento barato
3. **API Gateway HTTP**: Más barato que ALB ($16/mes)
4. **Sin RDS**: SQLite es suficiente para uso personal

## 🛠️ Configuración Paso a Paso

### 1. Preparar system.yaml

```yaml
environments:
  dev:
    account: "TU-CUENTA-AWS"  # ← Cambia esto
    region: "us-east-1"       # ← O tu región preferida
    settings:
      # El resto ya está configurado para minimal
```

### 2. Verificar antes de desplegar

```bash
# Ver qué se va a crear
cdk diff -c environment=dev -c stack_type=minimal

# Lista de stacks que se crearán
cdk list -c environment=dev -c stack_type=minimal
```

### 3. Desplegar

```bash
# Opción A: Desplegar todo de una vez
cdk deploy -c environment=dev -c stack_type=minimal --all

# Opción B: Desplegar stack por stack
cdk deploy -c environment=dev n8n-serverless-dev-storage
cdk deploy -c environment=dev n8n-serverless-dev-compute
cdk deploy -c environment=dev n8n-serverless-dev-access
```

### 4. Obtener la URL

Después del despliegue, verás:
```
Outputs:
n8n-serverless-dev-access.ApiUrl = https://xxxxx.execute-api.us-east-1.amazonaws.com
```

## 🔧 Personalización

### Si quieres usar tu VPC existente:

```yaml
environments:
  dev:
    settings:
      networking:
        use_existing_vpc: true
        vpc_id: "vpc-xxxxx"
        subnet_ids:
          - "subnet-xxxxx"
          - "subnet-yyyyy"
```

### Si quieres más memoria/CPU:

```yaml
environments:
  dev:
    settings:
      fargate:
        cpu: 512      # 0.5 vCPU
        memory: 1024  # 1 GB RAM
```

### Si quieres PostgreSQL en lugar de SQLite:

```yaml
environments:
  dev:
    settings:
      database:
        type: "postgres"
        instance_class: "db.t3.micro"  # ~$15/mes
```

## ❓ Preguntas Frecuentes

### ¿Necesito todos los stacks?
No. Con el tipo "minimal" solo se crean 3 stacks esenciales.

### ¿Puedo añadir stacks después?
Sí. Puedes empezar con minimal y añadir monitoring o database más tarde.

### ¿Cómo elimino todo?
```bash
cdk destroy -c environment=dev --all
```

### ¿Puedo usar esto en producción?
Sí, pero usa el tipo "standard" o "enterprise" con PostgreSQL.

## 📈 Siguiente Paso

**Ejecuta este comando para empezar:**
```bash
cdk deploy -c environment=dev -c stack_type=minimal --all --require-approval never
```

Esto desplegará n8n en AWS en unos 10-15 minutos. ¡Listo! 🎉