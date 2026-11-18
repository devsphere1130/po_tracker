import { useEffect, useRef, useState } from 'react'
import { Search } from 'lucide-react'

export function Field({ label, required, error, hint, children, className = '' }) {
  return (
    <div className={`field ${className}`}>
      {label && <label>{label}{required && <span className="req"> *</span>}</label>}
      {children}
      {error ? <span className="field-error">{error}</span> : hint ? <span className="field-hint">{hint}</span> : null}
    </div>
  )
}

export function Input({ invalid, className = '', ...props }) {
  return <input className={`input ${invalid ? 'invalid' : ''} ${className}`} {...props} />
}

export function Select({ invalid, className = '', children, ...props }) {
  return <select className={`input ${invalid ? 'invalid' : ''} ${className}`} {...props}>{children}</select>
}

export function TextArea({ invalid, ...props }) {
  return <textarea className={`input ${invalid ? 'invalid' : ''}`} {...props} />
}

/** Debounced search box. */
export function SearchInput({ value, onChange, placeholder = 'Search…' }) {
  const [text, setText] = useState(value || '')
  const timer = useRef()
  useEffect(() => setText(value || ''), [value])
  const change = (v) => {
    setText(v)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => onChange(v), 300)
  }
  return (
    <div className="search-wrap">
      <Search size={16} />
      <input className="input" value={text} placeholder={placeholder} onChange={(e) => change(e.target.value)} aria-label="Search" />
    </div>
  )
}

/** Reusable customer / material dropdowns fed by the API lists. */
export function OptionSelect({ value, onChange, options, placeholder = 'All', labelKey = 'name', invalid, disabled }) {
  return (
    <Select value={value ?? ''} onChange={(e) => onChange(e.target.value)} invalid={invalid} disabled={disabled}>
      <option value="">{placeholder}</option>
      {options.map((o) => <option key={o.id} value={o.id}>{typeof labelKey === 'function' ? labelKey(o) : o[labelKey]}</option>)}
    </Select>
  )
}
