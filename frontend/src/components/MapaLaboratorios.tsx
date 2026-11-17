import type { Laboratorio } from '../lib/turnos'

// Argentina, con las islas del sur fuera del cuadro: alcanza para ubicar a los laboratorios.
const LONGITUDES = [-74, -53]
const LATITUDES = [-56, -21]
const ANCHO = 280
const ALTO = 560

function proyectar(lab: Laboratorio): { x: number; y: number } {
  return {
    x: ((lab.longitud - LONGITUDES[0]) / (LONGITUDES[1] - LONGITUDES[0])) * ANCHO,
    y: ((LATITUDES[1] - lab.latitud) / (LATITUDES[1] - LATITUDES[0])) * ALTO,
  }
}

interface Props {
  laboratorios: Laboratorio[]
  seleccionado: number | null
  onElegir: (laboratorio: Laboratorio) => void
}

/**
 * Mapa simple de los laboratorios de extracción: cada punto está en su latitud y longitud.
 * No usa una biblioteca de mapas (no hay una en el proyecto); la lista de al lado ofrece lo mismo
 * para quien navega con teclado o con lector de pantalla.
 */
export function MapaLaboratorios({ laboratorios, seleccionado, onElegir }: Props) {
  return (
    <svg
      viewBox={`0 0 ${ANCHO} ${ALTO}`}
      role="group"
      aria-label="Mapa de laboratorios de extracción"
      className="mx-auto h-auto w-full max-w-xs rounded-lg border border-slate-200 bg-sky-50"
    >
      {laboratorios.map((lab) => {
        const { x, y } = proyectar(lab)
        const activo = lab.id === seleccionado
        return (
          <g
            key={lab.id}
            role="button"
            tabIndex={0}
            aria-label={`Mapa: ${lab.nombre}`}
            aria-pressed={activo}
            onClick={() => onElegir(lab)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onElegir(lab)
              }
            }}
            className="cursor-pointer"
          >
            <title>{lab.nombre}</title>
            <circle
              cx={x}
              cy={y}
              r={activo ? 7 : 4}
              className={activo ? 'fill-teal-700 stroke-white' : 'fill-slate-500 stroke-white'}
              strokeWidth={1}
            />
          </g>
        )
      })}
    </svg>
  )
}
