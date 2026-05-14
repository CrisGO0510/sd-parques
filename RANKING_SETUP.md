# Sistema de Ranking - Guía de Configuración

Este documento te guiará a través de los pasos necesarios para configurar y ejecutar el sistema de ranking para el juego de Parqués Distribuido.

## Requisitos Previos

- Python 3.11 o superior
- MySQL instalado y ejecutándose localmente
- Node.js y npm/pnpm para el cliente

## Paso 1: Configurar la Base de Datos MySQL

### 1.1 Conectarse a MySQL

Abre una terminal o MySQL Workbench y conectate a tu servidor MySQL:

```bash
mysql -u root -p
```

Si MySQL está configurado sin contraseña:

```bash
mysql -u root
```

### 1.2 Crear la base de datos

Ejecuta el script SQL que se encuentra en `server/init_db.sql`:

```sql
-- Desde la terminal MySQL:
source server/init_db.sql;
```

O copia y pega el contenido del archivo en tu cliente MySQL.

Esto creará:
- Base de datos: `sd_parques`
- Tabla: `players` con las columnas:
  - `id`: Identificador único (AUTO_INCREMENT)
  - `username`: Nombre del jugador (UNIQUE)
  - `games_played`: Total de partidas jugadas
  - `games_won`: Total de partidas ganadas
  - `created_at`: Fecha de registro
  - `updated_at`: Fecha de última actua lización

### 1.3 Verificar la instalación

```sql
USE sd_parques;
SHOW TABLES;
DESCRIBE players;
```

## Paso 2: Configurar el Servidor Python

### 2.1 Instalar dependencias

Desde la raíz del proyecto:

```bash
pip install -e .
```

Esto instalará `mysql-connector-python` y otras dependencias necesarias.

### 2.2 Configuración de la Conexión a BD

El servidor intenta conectarse a MySQL con la siguiente configuración por defecto:

```python
host = "localhost"
user = "root"
password = ""
database = "sd_parques"
port = 3306
```

Si tu configuración es diferente, puedes modificarla en el archivo `server/server.py` al crear la instancia del servidor:

```python
from server.db_config import DatabaseConfig, PlayerDatabase

# Personaliza la configuración si es necesario
db_config = DatabaseConfig(
    host="localhost",
    user="root",
    password="tu_contraseña",  # Si tienes contraseña
    database="sd_parques",
    port=3306
)

server = Server(db_config=db_config)
```

### 2.3 Ejecutar el servidor

```bash
python -m server
```

El servidor escuchará en `0.0.0.0:5000` por defecto.

## Paso 3: Ejecutar el Cliente

### 3.1 Instalar dependencias del cliente

```bash
cd client
npm install
# o si usas pnpm
pnpm install
```

### 3.2 Ejecutar el cliente en desarrollo

```bash
npm run dev
# o con pnpm
pnpm dev
```

## Funcionalidades del Sistema de Ranking

### 1. Registro Automático de Jugadores

Cuando un jugador se conecta por primera vez con un nombre de usuario, el sistema:
- Verifica si el nombre existe en la base de datos
- Si no existe, crea un nuevo registro con `games_played = 0` y `games_won = 0`
- Si existe, carga sus estadísticas

### 2. Contadores de Partidas

- **games_played**: Se incrementa en 1 cuando el jugador inicia una partida
- **games_won**: Se incrementa en 1 cuando el jugador gana una partida

### 3. Porcentaje de Victoria

Se calcula automáticamente como:
```
porcentaje = (games_won / games_played) * 100
```

### 4. Página de Ranking

Puedes acceder al ranking desde la interfaz del cliente. Muestra:
- Posición en el ranking
- Nombre del jugador
- Partidas jugadas
- Victorias
- Porcentaje de victoria

### 5. Perfil del Jugador

En la página de ranking, también puedes ver:
- Tu nombre de usuario
- Tus estadísticas personales
- Tu porcentaje de victoria

## Protocolo de Comunicación

### Comandos de Ranking

#### 1. Verificar/Registrar Jugador

```json
{
  "type": "verify_player",
  "username": "nombre_del_jugador"
}
```

Respuesta:
```json
{
  "type": "player_verified",
  "player_id": 1,
  "username": "nombre_del_jugador",
  "games_played": 0,
  "games_won": 0
}
```

#### 2. Obtener Ranking

```json
{
  "type": "get_ranking"
}
```

Respuesta:
```json
{
  "type": "ranking_update",
  "players": [
    {
      "id": 1,
      "username": "jugador1",
      "games_played": 10,
      "games_won": 7,
      "win_percentage": 70
    },
    ...
  ]
}
```

#### 3. Reportar Victoria

```json
{
  "type": "report_win",
  "player_id": 1
}
```

Respuesta:
```json
{
  "type": "stats_updated",
  "player_id": 1,
  "games_played": 11,
  "games_won": 8
}
```

## Solución de Problemas

### Error de conexión a MySQL

**Síntoma**: `Error connecting to MySQL: Access denied for user 'root'@'localhost'`

**Solución**: 
- Verifica que MySQL está ejecutándose
- Comprueba tu usuario y contraseña
- Si no tienes contraseña, asegúrate de pasar una cadena vacía

### Base de datos no existe

**Síntoma**: `1049 (42000): Unknown database 'sd_parques'`

**Solución**:
- Ejecuta el script `server/init_db.sql` para crear la base de datos
- Verifica que lo ejecutaste en el servidor correcto

### Tabla de jugadores vacía

**Síntoma**: El ranking no muestra jugadores

**Solución**:
- Los jugadores se crean cuando se conectan por primera vez
- Verifica que los jugadores han enviado el comando `verify_player`

### Error de tipos en TypeScript (cliente)

**Síntoma**: Errores de compilación en el cliente

**Solución**:
```bash
cd client
npm install
npm run build
```

## Estado Actual del Proyecto ✅

### 1. Sistema de Ranking Completamente Operativo

✅ **Base de datos MySQL**:
- Base de datos `sd_parques` con tabla `players`
- Campos: `id`, `username`, `games_played`, `games_won`, `created_at`, `updated_at`
- Índices optimizados para consultas

✅ **Servidor Python**:
- Escuchando en `0.0.0.0:5000` (TCP) y `0.0.0.0:5001` (WebSocket)
- Implementa protocolo completo de ranking:
  - `verify_player`: Registra o verifica un jugador
  - `get_ranking`: Obtiene el ranking global
  - `report_win`: Reporta una victoria (incrementa `games_won`)
  - Incremento automático de `games_played` al iniciar partida

✅ **Cliente Vue.js**:
- Página de ranking integrada en la sección del lobby
- Tabla interactiva mostrando:
  - Posición en el ranking
  - Nombre del jugador
  - Partidas jugadas
  - Victorias
  - Porcentaje de victoria
- Botón de actualización de ranking en tiempo real

✅ **Flujo de Victoria Verificado**:
- Cuando un jugador gana:
  1. Se incrementa automáticamente `games_won`
  2. El servidor envía respuesta `stats_updated` al cliente
  3. Los datos se persisten en la base de datos
  4. El ranking se actualiza automáticamente

### 2. Pruebas Exitosas

Todas las pruebas de funcionamiento han sido exitosas:
- Creación de jugadores
- Incremento de `games_played` al iniciar partida
- Incremento de `games_won` al reportar victoria
- Conversión correcta de tipos Decimal de MySQL a JSON
- Sincronización entre cliente y servidor

### 3. Archivos Modificados para el Pull

Los siguientes archivos han sido modificados/creados:

1. **server/db_config.py**
   - Agregada función `convert_decimal()` para serializar Decimal a JSON
   - Conversión aplicada a todos los métodos que retornan datos de BD

2. **client/src/pages/LobbyPage.vue**
   - Integración de ranking en el lado derecho del lobby
   - Tabla con información de todos los jugadores
   - Botón de actualización de ranking
   - Carga automática al montar el componente

3. **server/init_db.sql** ✅ (sin cambios, pero verificado)
   - Script SQL completamente funcional y listo para producción
   - Contiene indices para optimización

### 4. Cómo Usar el Sistema de Ranking

#### Para el Desarrollador
1. Ejecuta `python -m server` para iniciar el servidor
2. Ejecuta `npm run dev` en la carpeta `client` para iniciar el cliente
3. Accede a `http://localhost:9000/`
4. El ranking aparece automáticamente en el lobby

#### Para los Jugadores
1. Se registran automáticamente al conectarse por primera vez
2. Al inicio de cada partida, se incrementa `games_played`
3. Al ganar, se incrementa `games_won`
4. El ranking se calcula automáticamente: `(games_won / games_played) * 100`

## Próximas Mejoras Sugeridas

1. **Estadísticas avanzadas**:
   - Racha de victorias
   - Tiempo promedio de partida
   - Oponentes más frecuentes

2. **Sistema de logros**:
   - Primera victoria
   - 10 victorias
   - 100% de victorias en 10 partidas

3. **Visualización mejorada**:
   - Gráficos de evolución
   - Historial de partidas
   - Comparación entre jugadores

4. **Autenticación**:
   - Sistema de login/registro
   - Perfiles de usuario más detallados

## Contacto y Soporte

Si encuentras problemas, verifica:
1. Los logs del servidor (salida en la terminal)
2. Los logs del cliente (consola del navegador)
3. El estado de la conexión a MySQL
4. Que el archivo `server/init_db.sql` se haya ejecutado correctamente
