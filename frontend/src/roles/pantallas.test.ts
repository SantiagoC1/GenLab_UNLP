import { PANTALLAS } from './pantallas'
import { ROLES } from './roles'

describe('pantallas por rol', () => {
  it('cada rol tiene al menos una pantalla', () => {
    for (const rol of ROLES) {
      expect(
        PANTALLAS.some((p) => p.rol === rol),
        rol,
      ).toBe(true)
    }
  })

  it('no hay rutas repetidas', () => {
    const rutas = PANTALLAS.map((p) => `${p.rol}/${p.ruta}`)
    expect(new Set(rutas).size).toBe(rutas.length)
  })
})
