# 🚀 Quick Start - Despliega n8n en AWS en 5 minutos

## Lo que necesitas

1. ✅ Cuenta de AWS
2. ✅ AWS CLI configurado (`aws configure`)
3. ✅ AWS CDK instalado (`npm install -g aws-cdk`)

## Paso 1: Configura tu cuenta AWS

```bash
# Edita el archivo system.yaml
vim system.yaml

# Busca la línea 46 y cambia el account number:
# DE: account: "123456789012"
# A:  account: "TU-NUMERO-DE-CUENTA-AWS"
```

Para obtener tu número de cuenta:

```bash
aws sts get-caller-identity --query Account --output text
```

## Paso 2: Bootstrap CDK (solo la primera vez)

```bash
# Reemplaza ACCOUNT-ID y REGION con tus valores
cdk bootstrap aws://ACCOUNT-ID/us-east-1
```

## Paso 3: Despliega n8n

```bash
# Opción A: Despliegue minimal (~$5-10/mes)
cdk deploy -c environment=dev -c stack_type=minimal --all

# Opción B: Solo ver qué se va a crear (sin desplegar)
cdk diff -c environment=dev -c stack_type=minimal
```

## Paso 4: Accede a n8n

Al final del despliegue verás:

```
Outputs:
n8n-deploy-dev-access.ApiUrl = https://xxxxx.execute-api.us-east-1.amazonaws.com
```

Abre esa URL en tu navegador. Las credenciales por defecto son:

- Usuario: `admin`
- Password: `password`

## 🎯 Resumen de lo que se crea

Con el stack "minimal" obtienes:

- **1 ECS Fargate Task** - Ejecuta n8n (0.25 vCPU, 0.5GB RAM)
- **1 EFS File System** - Almacena workflows y datos
- **1 API Gateway** - Expone n8n a internet
- **Sin base de datos** - Usa SQLite en EFS
- **Sin Load Balancer** - Ahorra $16/mes

Total: ~$5-10/mes con Fargate Spot

## 🛑 Para eliminar todo

```bash
cdk destroy -c environment=dev --all
```

## 📝 Notas importantes

1. **Primera vez**: El despliegue toma ~10-15 minutos
2. **Región**: Por defecto usa `us-east-1`
3. **Costos**: Fargate Spot puede no estar disponible siempre
4. **Seguridad**: Cambia las credenciales después del primer login

## 🔧 Troubleshooting

### Error: "Account ID not found"

```bash
# Asegúrate de haber configurado AWS CLI
aws configure
```

### Error: "CDK not bootstrapped"

```bash
# Bootstrap en tu cuenta/región
cdk bootstrap
```

### Error: "Stack already exists"

```bash
# Elimina el stack anterior
cdk destroy -c environment=dev --all
```

## 🎉 ¡Listo

En 10-15 minutos tendrás n8n ejecutándose en AWS por menos de $10/mes.
