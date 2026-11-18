import { FileText } from 'lucide-react'

/** Original document preview: PDFs in an iframe, images inline. Files are served by the authenticated API. */
export default function AttachmentPreview({ url, contentType = '', filename = '' }) {
  if (!url) return <div className="empty">No document to preview.</div>
  const name = filename.toLowerCase()
  const isImage = contentType.startsWith('image/') || /\.(png|jpe?g)$/.test(name)
  const isPdf = contentType === 'application/pdf' || name.endsWith('.pdf')
  if (isImage) return <img src={url} alt={filename || 'Original attachment'} />
  if (isPdf) return <iframe src={url} title={filename || 'Original attachment'} />
  return (
    <div className="empty">
      <FileText size={30} />
      <div>Preview is not available for this file type.</div>
      <a href={url} target="_blank" rel="noreferrer">Open {filename || 'file'}</a>
    </div>
  )
}
