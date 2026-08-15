import React, { useEffect, useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { buildApiUrl, resolveApiBase } from './api/api'
import './index.css'

function Root() {
  const [online, setOnline] = useState(navigator.onLine)
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [updateReady, setUpdateReady] = useState(false)
  const skipWaitingPostedRef = useRef(false)

  useEffect(() => {
    const onOnline = () => setOnline(true)
    const onOffline = () => setOnline(false)
    const onBeforeInstallPrompt = (event) => {
      event.preventDefault()
      setDeferredPrompt(event)
    }

    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt)

    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
      window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt)
    }
  }, [])

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return undefined

    let updateInterval
    let healthInterval
    resolveApiBase().catch(() => {})
    const requestSyncFlush = () => {
      if (!navigator.serviceWorker.controller) return
      navigator.serviceWorker.controller.postMessage({ type: 'SYNC_REQUEST' })
    }
    const registerSyncTag = () => {
      if (!navigator.serviceWorker.controller) return
      navigator.serviceWorker.controller.postMessage({ type: 'REGISTER_SYNC' })
    }
    const onControllerChange = () => {
      // Only reload if we triggered the skip waiting (i.e., an update was applied)
      if (skipWaitingPostedRef.current) window.location.reload()
      registerSyncTag()
    }
    const onOnline = () => requestSyncFlush()
    const registerWorker = async () => {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js')
        await resolveApiBase().catch(() => {})
        if (registration.waiting) setUpdateReady(true)
        registration.addEventListener('updatefound', () => {
          const nextWorker = registration.installing
          if (!nextWorker) return
          nextWorker.addEventListener('statechange', () => {
            if (nextWorker.state === 'installed' && navigator.serviceWorker.controller) {
              setUpdateReady(true)
            }
          })
        })
        updateInterval = window.setInterval(() => registration.update().catch(() => {}), 60000)
        registerSyncTag()
        healthInterval = window.setInterval(async () => {
          try {
            await fetch(buildApiUrl('/health'), { method: 'GET', cache: 'no-store' })
          } catch {
            requestSyncFlush()
          }
        }, 300000)
      } catch {
        // ignore registration issues
      }
    }

    navigator.serviceWorker.addEventListener('controllerchange', onControllerChange)
    window.addEventListener('online', onOnline)

    if (document.readyState === 'complete') {
      registerWorker()
    } else {
      window.addEventListener('load', registerWorker, { once: true })
    }

    return () => {
      if (updateInterval) window.clearInterval(updateInterval)
      if (healthInterval) window.clearInterval(healthInterval)
      navigator.serviceWorker.removeEventListener('controllerchange', onControllerChange)
      window.removeEventListener('online', onOnline)
      window.removeEventListener('load', registerWorker)
    }
  }, [])

  const handleInstall = async () => {
    if (!deferredPrompt) return
    await deferredPrompt.prompt()
    setDeferredPrompt(null)
  }

  const handleUpdate = async () => {
    const registration = await navigator.serviceWorker.getRegistration()
    if (registration?.waiting) {
      skipWaitingPostedRef.current = true
      registration.waiting.postMessage({ type: 'SKIP_WAITING' })
    } else {
      window.location.reload()
    }
  }

  return (
    <>
      {!online && (
        <div className="fixed top-0 inset-x-0 z-50 bg-amber-500 text-white text-center text-sm py-2">
          Tryb offline — zmiany zostaną zsynchronizowane po odzyskaniu połączenia.
        </div>
      )}
      {updateReady && (
        <div className={`fixed inset-x-0 z-50 ${online ? 'top-0' : 'top-10'} bg-blue-600 text-white text-center text-sm py-2`}>
          Nowa wersja aplikacji jest gotowa.
          <button onClick={handleUpdate} className="ml-3 rounded bg-white/20 px-3 py-1 font-semibold hover:bg-white/30">
            Odśwież
          </button>
        </div>
      )}
      {deferredPrompt && (
        <button
          onClick={handleInstall}
          className="fixed bottom-4 right-4 z-50 rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg hover:bg-blue-700"
        >
          Zainstaluj aplikację
        </button>
      )}
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
)
