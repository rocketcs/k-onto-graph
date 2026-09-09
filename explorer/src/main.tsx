import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { loader } from '@monaco-editor/react'
import { locale } from './i18n'

loader.config({ 'vs/nls': { availableLanguages: { '*': locale === 'zh-CN' ? 'zh-cn' : 'en' } } })

createRoot(document.getElementById('root')!).render(
  <App />,
)
