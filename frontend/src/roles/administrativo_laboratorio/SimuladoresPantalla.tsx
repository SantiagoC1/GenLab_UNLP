import LaboratorioExtraccionSimulador from './simuladores/LaboratorioExtraccionSimulador'

export default function SimuladoresPantalla() {
  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Simuladores de actores externos
      </h1>
      <p className="mt-1 text-sm text-slate-500">M10-RF4</p>
      <div className="mt-6 space-y-10">
        <LaboratorioExtraccionSimulador />
      </div>
    </section>
  )
}
