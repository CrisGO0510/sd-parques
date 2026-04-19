import axios from 'axios'
import { useUserStore } from 'src/stores/userStore'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export function useAuth() {
  const userStore = useUserStore()

  async function login(username, password) {
    const { data } = await axios.post(`${API_URL}/login`, { username, password })
    userStore.setAuth(data.token, data.username)
    return data
  }

  async function register(username, password) {
    const { data } = await axios.post(`${API_URL}/register`, { username, password })
    return data
  }

  function logout() {
    userStore.logout()
  }

  return { login, register, logout }
}
