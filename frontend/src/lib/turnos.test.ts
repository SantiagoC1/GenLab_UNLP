import { describe, expect, it } from 'vitest'
import { describirRemuestreo } from './turnos'

describe('describirRemuestreo', () => {
  it('explains that the sample arrived with poor quality', () => {
    expect(describirRemuestreo('mala_calidad_de_muestra')).toBe('la muestra llegó con mala calidad')
  })

  it('explains that the DNA was not enough', () => {
    expect(describirRemuestreo('adn_desnaturalizado')).toBe(
      'el ADN de la muestra no alcanzó para el análisis',
    )
  })

  it.each(['volumen_menor_2ml', 'otro_motivo', ''])(
    'uses a neutral text, without any volume, for the reason "%s"',
    (motivo) => {
      const texto = describirRemuestreo(motivo)

      expect(texto).toBe('la muestra anterior no sirvió para el estudio')
      expect(texto).not.toMatch(/ml|volumen/i)
    },
  )
})
