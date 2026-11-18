import { useCallback, useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import Modal from '../../components/Modal'
import { Field, Input } from '../../components/FormControls'
import { Loading } from '../../components/DataTable'
import { aliasesApi } from '../../api/materials'
import { errorMessage } from '../../api/client'
import { useToast } from '../../components/Toast'

/** Maps customer/OCR descriptions to a master material so future documents match automatically. */
export default function MaterialAliases({ material, onClose }) {
  const toast = useToast()
  const [aliases, setAliases] = useState(null)
  const [text, setText] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(() => aliasesApi.list({ material: material.id, page_size: 200 }).then((r) => setAliases(r.results)), [material.id])
  useEffect(() => { load().catch((e) => setError(errorMessage(e))) }, [load])

  const add = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await aliasesApi.create({ material: material.id, description: text })
      setText('')
      toast.success('Description mapped.')
      load()
    } catch (err) { setError(errorMessage(err)) }
  }
  const remove = async (id) => {
    try { await aliasesApi.remove(id); load() } catch (err) { toast.error(errorMessage(err)) }
  }

  return (
    <Modal title={`Customer descriptions — ${material.name}`} onClose={onClose} footer={<button className="btn btn-primary" onClick={onClose}>Done</button>}>
      <p className="muted" style={{ marginTop: 0 }}>Original descriptions received from customers that should map to this material. OCR uses these to pre-select the material.</p>
      <form className="flex" style={{ alignItems: 'flex-end' }} onSubmit={add}>
        <Field label="Customer description" className="grow"><Input value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. HEX BOLT 10X50 ZP" required /></Field>
        <button className="btn btn-primary">Map</button>
      </form>
      {error && <div className="alert alert-error" style={{ marginTop: 10 }}>{error}</div>}
      <div style={{ marginTop: 14 }}>
        {!aliases ? <Loading /> : aliases.length === 0 ? <div className="muted">No mapped descriptions yet.</div> : (
          <table className="table"><tbody>
            {aliases.map((a) => (
              <tr key={a.id}><td>{a.description}</td><td className="right"><button className="btn btn-sm btn-icon btn-danger" onClick={() => remove(a.id)} aria-label="Remove"><Trash2 size={14} /></button></td></tr>
            ))}
          </tbody></table>
        )}
      </div>
    </Modal>
  )
}
