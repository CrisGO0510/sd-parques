import { ref } from 'vue'
import { io } from 'socket.io-client'
import { useUserStore } from 'src/stores/userStore'

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'http://localhost:5000'

let socket = null
const connected = ref(false)

export function useSocket() {
  const userStore = useUserStore()

  function connect() {
    if (socket?.connected) return socket
    socket = io(SOCKET_URL, {
      transports: ['websocket'],
      auth: { token: userStore.token },
    })
    socket.on('connect', () => { connected.value = true })
    socket.on('disconnect', () => { connected.value = false })
    return socket
  }

  function disconnect() {
    if (socket) {
      socket.disconnect()
      socket = null
      connected.value = false
    }
  }

  function getSocket() {
    return socket
  }

  return { connect, disconnect, getSocket, connected }
}
