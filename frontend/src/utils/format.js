export function formatDate(value) {
  if (!value) return '-'
  return String(value).slice(0, 10)
}

export function formatDateTime(value) {
  if (!value) return '-'
  const d = new Date(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || value === '') return '-'
  return Number(value).toLocaleString('ko-KR', { maximumFractionDigits: digits || 3 })
}

export function formatBytes(bytes) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i += 1
  }
  return `${value.toFixed(i ? 1 : 0)} ${units[i]}`
}

export function productDimension(p) {
  if (p.diameter_mm) {
    const dia = p.diameter2_mm ? `Ø${p.diameter_mm}/Ø${p.diameter2_mm}` : `Ø${p.diameter_mm}`
    return `${dia} × ${p.length_mm ?? '?'} mm`
  }
  if (p.width_mm) return `${p.width_mm} × ${p.height_mm} × ${p.depth_mm ?? '?'} mm`
  return p.dimension_text || '-'
}

export function displayValue(value) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? '예' : '아니오'
  if (typeof value === 'object') return JSON.stringify(value, null, 1)
  return String(value)
}

export const DOCUMENT_STATUS_VARIANT = {
  UPLOADED: 'secondary',
  PARSING: 'info',
  PARSED: 'warning',
  NEEDS_OCR: 'warning',
  EXTRACTING: 'info',
  EXTRACTED: 'primary',
  REVIEWED: 'success',
  FAILED: 'danger',
}

export const CERT_STATUS_VARIANT = {
  VALID: 'success',
  EXPIRING: 'warning',
  EXPIRED: 'danger',
  UNKNOWN: 'secondary',
}
