import axios from 'axios'

// Shared axios instance. JWT header and refresh/409 interceptors are added in Phase 2.
const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
})

export default client
