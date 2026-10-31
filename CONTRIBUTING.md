# Cómo colaborar

## Ramas

- `main` es la rama de entrega. `develop` es la rama de integración.
- **Nadie hace push directo a `main` ni a `develop`.** Todo entra por pull request.
- Cada tarea tiene su rama, creada desde `develop`:

  ```
  feature/<id-tarea>-descripcion
  ```

  Por ejemplo `feature/3.3-alta-de-paciente` o `feature/CB3-servicio-de-consulta`. El `id-tarea` es el de la tabla de `docs/Reparto_de_tareas_GenLab.md`.
- Para tareas de infraestructura o documentación se usa `chore/<descripcion>`, y para correcciones `fix/<descripcion>`.

## Pull requests

- El PR apunta a `develop` y enlaza el issue (`Cierra #N`).
- Necesita **al menos una revisión** de otro integrante antes de mergear.
- Completá la checklist de la plantilla. El CI (lint y tests) tiene que estar en verde.
- Mergeá con "Squash and merge" para mantener `develop` legible.
- Protegé `main` y `develop` en GitHub (Settings → Branches): exigir PR, una aprobación y que pase el CI.

## Commits

En español, en imperativo y con un resumen corto:

```
Agrega el alta de patología lisosomal
Corrige el cálculo del presupuesto con más de 5 genes
```

Commits chicos y con sentido: uno por cambio lógico.

## Vocabulario

Pantallas, mails y documentos usan los términos del LEL, sin sinónimos: estudio, lote, muestra de sangre, laboratorio de extracción, transportista, orden del día, obra social, cupón de descuento.

## Estados del estudio

Siguen el catálogo de la especificación. Nadie agrega, quita ni renombra estados sin avisar al resto. Pompe urgente es una marca de prioridad, no un estado.

## Entorno local

```bash
cp .env.example .env
make up        # levanta todo
make test      # tests de backend, chatbot y frontend
make lint      # ruff, eslint y prettier
```

No hay migraciones: las tablas están en `supabase/*.sql` y se ejecutan a mano, en orden, en el SQL Editor de Supabase. Las claves de Supabase van en el `.env` propio (`SUPABASE_URL`, `SUPABASE_KEY` y `SUPABASE_SERVICE_ROLE_KEY`).

Nunca subas secretos: `.env` está en `.gitignore`. Las claves de los modelos del chatbot (`GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`) van solo en el `.env`.
