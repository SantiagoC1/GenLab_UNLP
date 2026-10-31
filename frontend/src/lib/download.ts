import { readSession } from './session'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// REUTILIZABLE: baja un archivo que el backend protege con la sesión (por ejemplo un PDF).
// Un enlace común no sirve porque el navegador no manda el token en una navegación.
export async function downloadFile(path: string, fileName: string): Promise<void> {
  const session = readSession()
  const response = await fetch(`${API_URL}${path}`, {
    headers: session ? { Authorization: `Bearer ${session.token}` } : {},
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detalle ?? response.statusText)
  }
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
