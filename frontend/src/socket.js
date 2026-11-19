/**
 * socket.js — Singleton Socket.IO client.
 * Exports a single `socket` instance reused across all components.
 */
import { io } from 'socket.io-client'

// In development the Vite proxy routes /socket.io → localhost:5001
// In production point this at the deployed backend URL
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || ''

export const socket = io(BACKEND_URL, {
  transports: ['websocket', 'polling'],
  autoConnect: true,
})

export default socket
