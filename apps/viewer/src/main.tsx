import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from '@/app/App'
import '@/app/index.css'

// Input modality: focus styling only after keyboard navigation, never after a click.
const setInput = (mode: 'keyboard' | 'pointer') => {
  document.documentElement.dataset.input = mode
}
window.addEventListener('keydown', (e) => !e.metaKey && !e.ctrlKey && !e.altKey && setInput('keyboard'), true)
window.addEventListener('pointerdown', () => setInput('pointer'), true)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
