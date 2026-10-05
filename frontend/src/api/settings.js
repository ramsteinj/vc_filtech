import client from './client'

export const getLLMSettings = () => client.get('/settings/llm').then((r) => r.data)

export const updateLLMSettings = (data) => client.put('/settings/llm', data).then((r) => r.data)

export const updateProvider = (provider, data) =>
  client.put(`/settings/llm/providers/${provider}`, data, { timeout: 90000 }).then((r) => r.data)

export const verifyProvider = (provider, modelId) =>
  client
    .post(`/settings/llm/providers/${provider}/verify`, { model_id: modelId }, { timeout: 90000 })
    .then((r) => r.data)

export const createModelOption = (data) =>
  client.post('/settings/llm/models', data).then((r) => r.data)

export const updateModelOption = (id, data) =>
  client.patch(`/settings/llm/models/${id}`, data).then((r) => r.data)

export const deleteModelOption = (id) => client.delete(`/settings/llm/models/${id}`)
