
import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../../lib/api'

type PendingStudy = {
  id: number
  batch_id: number
  state: string
  pompe_urgent: boolean
}

type UploadResponse = {
  study_id: number
  state: string
  filename: string
  file_size: number
  uploaded_at: string
  notification_status: string
}

export default function DatosCrudosPantalla() {
  const [studies, setStudies] = useState<PendingStudy[]>([])
  const [selectedStudyId, setSelectedStudyId] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadStudies = useCallback(async () => {
    try {
      const result = await api<PendingStudy[]>(
        '/bioinformatics/raw-data/pending',
      )

      setStudies(result)
      setError('')
    } catch {
      setError('No se pudieron consultar los estudios pendientes.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadStudies()
  }, [loadStudies])

  const selectedStudy = studies.find(
    (study) => study.id === Number(selectedStudyId),
  )

  function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setError('')
    setSuccess('')
  }

  function openConfirmation() {
    if (!selectedStudy) {
      setError('Seleccioná un estudio.')
      return
    }

    if (!selectedFile) {
      setError('Seleccioná un archivo de datos crudos.')
      return
    }

    if (selectedFile.size === 0) {
      setError('El archivo no puede estar vacío.')
      return
    }

    setError('')
    setIsModalOpen(true)
  }

  async function handleUpload() {
    if (!selectedStudy || !selectedFile || isUploading) {
      return
    }

    setIsUploading(true)
    setError('')
    setSuccess('')

    try {
      const result = await api<UploadResponse>(
        `/bioinformatics/studies/${selectedStudy.id}/raw-data`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/octet-stream',
            'X-File-Name': selectedFile.name,
          },
          body: selectedFile,
        },
      )

      setIsModalOpen(false)
      setSelectedStudyId('')
      setSelectedFile(null)

      const fileInput = document.getElementById(
        'raw-data-file',
      ) as HTMLInputElement | null

      if (fileInput) {
        fileInput.value = ''
      }

      await loadStudies()

      setSuccess(
        `Los datos crudos del estudio #${result.study_id} ` +
          'se cargaron correctamente. El estudio quedó ' +
          'disponible para Bioinformática. ' +
          'El aviso por correo fue simulado.',
      )
    } catch (caughtError) {
      setIsModalOpen(false)

      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
      } else {
        setError('No se pudo cargar el archivo.')
      }
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <section className="space-y-6 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Cargar datos crudos de un estudio
          </h1>

          <p className="mt-2 text-sm text-gray-600">
            Adjuntá los datos recibidos desde Corea a un
            estudio que se encuentre en viaje a Corea.
          </p>
        </div>

        <button
          type="button"
          disabled={isLoading || isUploading}
          onClick={() => {
            setIsLoading(true)
            void loadStudies()
          }}
          className="rounded-lg border px-4 py-2 text-sm disabled:opacity-50"
        >
          Actualizar
        </button>
      </header>

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </p>
      )}

      {success && (
        <p
          role="status"
          className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800"
        >
          {success}
        </p>
      )}

      {isLoading ? (
        <p role="status">Cargando estudios...</p>
      ) : studies.length === 0 ? (
        <div className="rounded-xl border bg-white p-5">
          <p className="font-medium">
            No hay estudios pendientes de carga.
          </p>
          <p className="mt-2 text-sm text-gray-600">
            Los estudios aparecerán aquí cuando FedEx
            haya confirmado el retiro de sus lotes.
          </p>
        </div>
      ) : (
        <div className="max-w-2xl space-y-5 rounded-xl border bg-white p-6">
          <div>
            <label
              htmlFor="raw-data-study"
              className="block text-sm font-medium"
            >
              Estudio
            </label>

            <select
              id="raw-data-study"
              value={selectedStudyId}
              disabled={isUploading}
              onChange={(event) => {
                setSelectedStudyId(event.target.value)
                setSelectedFile(null)
                setError('')
                setSuccess('')

                const fileInput = document.getElementById(
                  'raw-data-file',
                ) as HTMLInputElement | null

                if (fileInput) {
                  fileInput.value = ''
                }
              }}
              className="mt-2 w-full rounded-lg border p-3"
            >
              <option value="">Seleccioná un estudio</option>

              {studies.map((study) => (
                <option key={study.id} value={study.id}>
                  Estudio #{study.id} — Lote #{study.batch_id}
                  {study.pompe_urgent ? ' — Pompe urgente' : ''}
                </option>
              ))}
            </select>
          </div>

          {selectedStudy && (
            <>
              <div className="space-y-2 rounded-lg bg-gray-50 p-4 text-sm">
                <p>
                  <strong>Estudio:</strong> #{selectedStudy.id}
                </p>
                <p>
                  <strong>Lote de origen:</strong> #
                  {selectedStudy.batch_id}
                </p>
                <p>
                  <strong>Estado actual:</strong>{' '}
                  En viaje a Corea
                </p>

                {selectedStudy.pompe_urgent && (
                  <p className="font-semibold text-red-700">
                    Prioridad Pompe urgente
                  </p>
                )}
              </div>

              <div>
                <label
                  htmlFor="raw-data-file"
                  className="block text-sm font-medium"
                >
                  Archivo de datos crudos
                </label>

                <input
                  id="raw-data-file"
                  type="file"
                  disabled={isUploading}
                  onChange={handleFileChange}
                  className="mt-2 block w-full rounded-lg border p-3 text-sm"
                />

                <p className="mt-2 text-xs text-gray-500">
                  Seleccioná el archivo recibido desde Corea
                  correspondiente a este estudio.
                </p>
              </div>

              {selectedFile && (
                <div className="rounded-lg border p-3 text-sm">
                  <p>
                    <strong>Archivo:</strong>{' '}
                    {selectedFile.name}
                  </p>
                  <p>
                    <strong>Tamaño:</strong>{' '}
                    {selectedFile.size.toLocaleString('es-AR')}{' '}
                    bytes
                  </p>
                </div>
              )}

              <button
                type="button"
                disabled={
                  !selectedFile ||
                  selectedFile.size === 0 ||
                  isUploading
                }
                onClick={openConfirmation}
                className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cargar datos crudos
              </button>
            </>
          )}
        </div>
      )}

      {isModalOpen && selectedStudy && selectedFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="raw-data-dialog-title"
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
          >
            <h2
              id="raw-data-dialog-title"
              className="text-xl font-semibold"
            >
              Confirmar carga de datos crudos
            </h2>

            <p className="mt-4 text-sm text-gray-600">
              ¿Confirmás que el archivo{' '}
              <strong>{selectedFile.name}</strong>{' '}
              corresponde al estudio{' '}
              <strong>#{selectedStudy.id}</strong>?
            </p>

            <p className="mt-3 text-sm text-gray-600">
              Al confirmar, el estudio pasará a
              «En el área de bioinformática».
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={isUploading}
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg border px-4 py-2 text-sm disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                type="button"
                disabled={isUploading}
                onClick={() => void handleUpload()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                {isUploading
                  ? 'Cargando...'
                  : 'Confirmar carga'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
