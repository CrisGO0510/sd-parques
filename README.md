# Parqués distribuido — Sistemas Distribuidos UTP 2026-1

Juego de parqués multijugador por red: motor de reglas en Python, servidor TCP con hilos + puente WebSocket, cliente Quasar/Vue 3 + TypeScript con soporte Android (Capacitor).

## Estructura del repo

```
sd-parques/
├── core/          # reglas del juego (Python puro, sin I/O)
├── server/        # servidor TCP multihilo + WebSocket bridge
├── client/        # cliente Quasar v2 (Vue 3 + TS)
├── tests/         # pruebas unitarias del core
├── tests_server/  # pruebas del servidor
└── docs/          # specs y planes por módulo
```

## Requisitos

- **Python** ≥ 3.11
- **Node.js** ≥ 22.12 (o 24 / 26 / 28) y **npm**
- Linux, macOS o WSL (el servidor usa sockets Unix-friendly)

## 1. Servidor Python

### Instalar

Desde la raíz del repo:

```bash
# Crear entorno virtual (solo la primera vez)
python3 -m venv .venv

# Activar
source .venv/bin/activate

# Instalar el paquete + dependencias opcionales (websockets + pytest)
pip install -e '.[dev,ws]'
```

### Correr el servidor

```bash
.venv/bin/python -m server --log-level INFO
```

Por defecto escucha:
- **TCP**: `0.0.0.0:5000`
- **WebSocket**: `0.0.0.0:5001`

Flags disponibles:

| Flag | Default | Descripción |
|---|---|---|
| `--host` | `0.0.0.0` | interfaz de red |
| `--port-tcp` | `5000` | puerto TCP crudo |
| `--port-ws` | `5001` | puerto WebSocket (0 = disabled) |
| `--no-ws` | off | apagar completamente el listener WS |
| `--log-level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

Ejemplo solo-TCP:

```bash
.venv/bin/python -m server --no-ws --log-level DEBUG
```

Detener con `Ctrl+C`.

### Tests del backend

```bash
.venv/bin/python -m pytest tests/ tests_server/
```

Debe pasar **140+ tests** sin fallos.

## 2. Cliente Vue

El cliente se conecta al servidor via WebSocket (`ws://<host>:5001`).

### Instalar

```bash
cd client
npm install
```

### Correr en modo dev

```bash
npm run dev
```

Abre automáticamente en `http://localhost:9000`. Hot reload activado.

### Build de producción

```bash
npm run build
```

Deja el bundle estático en `client/dist/spa/`.

### Tests del cliente

```bash
npm test            # una pasada
npm run test:watch  # watch mode
npm run typecheck   # vue-tsc --noEmit
npm run lint        # eslint
```

## 3. Jugar localmente

1. **Terminal 1** — servidor:
   ```bash
   source .venv/bin/activate
   python -m server --log-level INFO
   ```
2. **Terminal 2** — cliente:
   ```bash
   cd client
   npm run dev
   ```
3. En el navegador, abre `http://localhost:9000`. Conecta con:
   - **Host**: `localhost`
   - **Puerto**: `5001`
   - **Usuario**: cualquier nombre
4. Para probar multijugador, abre **otra pestaña** (o ventana de incógnito) y repite el join con otro nombre. Necesitas **al menos 2 jugadores** para iniciar partida.

## Scripts útiles

Desde la raíz:

```bash
# backend completo
.venv/bin/python -m pytest tests/ tests_server/ -v

# cliente completo
cd client && npm run typecheck && npm run lint && npm test
```
