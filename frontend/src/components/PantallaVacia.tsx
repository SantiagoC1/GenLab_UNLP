interface Props {
  titulo: string
  referencia?: string
}

export function PantallaVacia({ titulo, referencia }: Props) {
  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{titulo}</h1>
      {referencia && <p className="mt-1 text-sm text-slate-500">{referencia}</p>}
      <div className="mt-6 rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500 sm:p-10">
        Pantalla pendiente de implementar.
      </div>
    </section>
  )
}
