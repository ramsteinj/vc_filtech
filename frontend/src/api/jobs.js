import client from './client'

export const getJob = (id) => client.get(`/jobs/${id}`).then((r) => r.data)
