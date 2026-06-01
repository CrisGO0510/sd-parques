# PostgreSQL Setup - Guía de Configuración

Este documento te guiará a través de los pasos necesarios para configurar PostgreSQL para el proyecto Parqués Distribuido.

## 1. Configuración Local (Desarrollo)

### 1.1 Crear la Base de Datos

```bash
# Conectarse a PostgreSQL como usuario 'postgres'
psql -U postgres

# Una vez dentro de psql, ejecutar:
CREATE DATABASE sd_parques;
```

O desde la terminal sin entrar en psql:
```bash
createdb -U postgres sd_parques
```

### 1.3 Ejecutar el Script SQL

```bash
# Desde la raíz del proyecto
psql -U postgres -d sd_parques -f server/init_db.sql
```

**Verificar que se creó correctamente:**
```bash
psql -U postgres -d sd_parques -c "SELECT * FROM players;"
```

### 1.4 Configurar Variables de Entorno (Opcional)

Por defecto, el código intenta conectar a:
```
postgresql://postgres:postgres@localhost:5432/sd_parques
```

Si tu configuración es diferente, crea un archivo `.env` en la raíz del proyecto:

```env
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/sd_parques
```

El código leerá automáticamente esta variable.

---

## 2. Configuración en Render

### 2.1 Crear Servicio PostgreSQL en Render

1. Ve a [render.com](https://render.com)
2. Dashboard → New → PostgreSQL
3. **Nombre:** `sd-parques-db`
4. **PostgreSQL Version:** 16
5. **Region:** La misma que tu servicio web (ej: Ohio, Frankfurt)
6. **Tier:** Free (desarrollar) → Standard (producción)
7. Click **Create Database**

### 2.2 Obtener Credenciales

Una vez creada, Render proporciona automáticamente:
- `INTERNAL_DATABASE_URL` (solo para servicios internos en Render)
- `DATABASE_URL` (completa, con credenciales)

Render **inyecta automáticamente** `DATABASE_URL` como variable de entorno en tu servicio web.

### 2.3 Crear el Script SQL en Render

Después de crear la BD, ejecuta el script SQL:

1. Click en el nombre de la BD en Render
2. Ve a la pestaña **"Console"**
3. Copia y pega el contenido de `server/init_db.sql`
4. Ejecuta

O usa `psql` desde terminal (si tienes instalado):
```bash
psql <DATABASE_URL> -f server/init_db.sql
```

### 2.4 Verificar Conexión

En el panel de Render, verifica que la tabla se creó:
```sql
SELECT * FROM players;
```

---

## 3. Variables de Entorno en Render

Tu servicio web (`parques-server`) debe tener estas variables:

| Variable | Valor | Nota |
|----------|-------|------|
| `DATABASE_URL` | `postgresql://...` | Inyectada automáticamente por Render |
| `PYTHONUNBUFFERED` | `1` | Ya configurado en `render.yaml` |
| `VITE_WS_URL` | `wss://tu-app.onrender.com` | Para el cliente Vue |

---

## 4. Comandos Útiles

### Conectar a PostgreSQL localmente
```bash
psql -U postgres -d sd_parques
```

### Ver tablas en la BD
```bash
\dt
```

### Ver estructura de la tabla 'players'
```bash
\d players
```

### Salir de psql
```bash
\q
```

### Eliminar y recrear la BD (si la arruinas)
```bash
dropdb -U postgres sd_parques
createdb -U postgres sd_parques
psql -U postgres -d sd_parques -f server/init_db.sql
```

---

## 5. Troubleshooting

### Error: "could not connect to server"
- ✅ Verificar que PostgreSQL está corriendo
- ✅ Verificar que el usuario/contraseña son correctos
- ✅ Verificar que el host y puerto son correctos

### Error: "database sd_parques does not exist"
```bash
# Crear la BD
createdb -U postgres sd_parques

# Ejecutar el script
psql -U postgres -d sd_parques -f server/init_db.sql
```

### Error en Render: "FATAL: remaining connection slots are reserved"
- Free tier tiene límite de conexiones
- Considerar subir a Standard tier o usar connection pooling

---

## 6. Diferencias entre MySQL y PostgreSQL

| Feature | MySQL | PostgreSQL |
|---------|-------|-----------|
| Parámetros | `%s` | `%s` (igual) |
| Tipos de datos | `INT AUTO_INCREMENT` | `SERIAL` |
| Diccionarios de cursor | `dictionary=True` | `RealDictCursor` |
| timestamps | `CURRENT_TIMESTAMP ON UPDATE` | `CURRENT_TIMESTAMP` (manual trigger) |
| División entera | Automática | Requiere `CAST` |

El código ya está actualizado para PostgreSQL. ✅
