# GenLab: plataforma del laboratorio de genética

Proyecto de la materia TTPS (UNLP). Plataforma web para un laboratorio de genética que gestiona estudios de exoma clínico (enfermedad de Fabry, enfermedad de Pompe, mucopolisacaridosis tipo 1, enfermedad de Gaucher y ASMD), más un **chatbot para el paciente** que se publica como servicio independiente (módulo adicional 8).

Este repositorio contiene solo el esqueleto: estructura, configuración, contratos y pantallas vacías. No hay lógica de negocio todavía.

## Stack

| Parte | Tecnología |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind, react-router, TanStack Query |
| Backend | FastAPI (Python 3.12), SQLAlchemy 2, Alembic, PostgreSQL |
| Chatbot | FastAPI separado, con la API de Anthropic (la clave va por variable de entorno) |
| Local | docker-compose con Postgres y los tres servicios |
| Calidad | ruff y pytest (backend y chatbot); eslint, prettier y vitest (frontend) |
| CI | GitHub Actions: lint y tests en cada PR |

## Levantarlo en 3 comandos

```bash
git clone <url-del-repo> && cd <repo>
cp .env.example .env
make up
```

Después:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000/docs> (salud en `/health`)
- Chatbot: <http://localhost:8001/docs> (salud en `/health`)

Otros comandos: `make down`, `make test`, `make lint`, `make migrate`, `make seed`.

En Windows, `make` no viene instalado. Podés instalarlo (`winget install GnuWin32.Make`, o usar WSL) o correr los comandos de docker compose que figuran en el `Makefile`.

## Mapa del repositorio

```
frontend/              React. Una carpeta por rol en src/roles/ con una pantalla vacía por pantalla
  src/roles/pantallas.ts   lista de pantallas por rol (menú y rutas salen de acá)
backend/
  app/core/            config, seguridad, base de datos, errores, enums (EstadoEstudio, Rol)
  app/modules/         un paquete por área: acceso, config_medica, consulta_medica,
                       presupuesto_pago, cupones, turnos, logistica, bioinformatica, avisos
  app/integrations/    un adaptador por módulo externo, con su simulador
  alembic/             migraciones
  tests/
chatbot/               servicio independiente con su Dockerfile y sus tests
docs/                  especificación, reparto de tareas y escenarios
tools/                 issues.json y crear_issues.py
.github/               CI, plantilla de PR y plantillas de issue
```

## Integraciones externas

Cada módulo de otro grupo (Familiograma, SNOMED, Cupones, CDSS, Apigen, ObrasSociales, Avisos, OptimizacionRecorrido, FedEx) y la API del Ministerio de Salud tienen una interfaz y un simulador en `backend/app/integrations/`. El setting `INTEGRACION_<NOMBRE>` elige `simulador` (por defecto) o `real`. Los contratos reales no están cerrados: los métodos salen de la tabla de contratos mínimos de M10 y el cliente `real` tiene un TODO.

## Decisiones tomadas para el esqueleto

Donde la consigna era ambigua, elegimos la opción más simple:

- **Pantallas del frontend.** El prompt las pedía "según la sección 4" de la especificación, pero ese documento no tiene una sección de pantallas. Se derivaron de los módulos M1 a M11 y de los 41 escenarios (cada pantalla indica su escenario y requerimientos). Si cambia el reparto de pantallas, se edita `frontend/src/roles/pantallas.ts` y el archivo de la pantalla.
- **Pantallas públicas.** Registrarse e Ingresar no pertenecen a un rol y se agruparon en `src/roles/publico/`.
- **Avisos.** La pantalla de avisos es una sola (`/avisos`) y aparece en el menú de todos los roles.
- **Rol de desarrollo.** Hasta que exista el ingreso real (tarea 1.4), el rol sale de un selector visible solo en modo dev y se guarda en `localStorage`.
- **Tests de humo de los routers.** Cada paquete de `modules/` expone `GET /<modulo>/ping`, solo para poder probar que el router está registrado. Se borra cuando el paquete tenga endpoints reales.
- **Estados.** `EstadoEstudio` usa valores sin espacios (`TurnoSacado`, `EnViajeACorea`...). Pompe urgente es un booleano aparte, no un estado.
- **Disponibilidad del chatbot.** `CHATBOT_DISPONIBLE=false` apaga el servicio: `/health` y `/chat` responden 503 con un mensaje claro. Más adelante `/health` también debería reflejar si el modelo de lenguaje responde.
- **Ruff.** Se desactivó la regla E501 (largo de línea); el formateador se ocupa del código.
- **Hash y sesiones.** `core/security.py` solo declara el contrato (`requiere_rol`). Lo implementa la tarea 1.4.

## Documentación

- [`docs/Especificacion_requerimientos_GenLab.md`](docs/Especificacion_requerimientos_GenLab.md)
- [`docs/Reparto_de_tareas_GenLab.md`](docs/Reparto_de_tareas_GenLab.md)
- [`docs/Escenarios_laboratorio_genetica_v3.md`](docs/Escenarios_laboratorio_genetica_v3.md)

Para trabajar en equipo, leé [`CONTRIBUTING.md`](CONTRIBUTING.md).
