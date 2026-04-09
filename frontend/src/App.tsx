import { useEffect } from 'react'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Search from './pages/Search'
import Images from './pages/Images'
import Multimedia from './pages/Multimedia'
import Timeline from './pages/Timeline'
import Duplicates from './pages/Duplicates'
import Indexing from './pages/Indexing'
import Settings from './pages/Settings'
import { useStore } from './store'

export default function App() {
  const { activeTab, theme } = useStore()

  useEffect(() => {
    document.documentElement.classList.toggle('light', theme === 'light')
  }, [theme])

  const Page = {
    dashboard: Dashboard,
    search: Search,
    images: Images,
    multimedia: Multimedia,
    timeline: Timeline,
    duplicates: Duplicates,
    indexing: Indexing,
    settings: Settings,
  }[activeTab] ?? Dashboard

  return (
    <Layout>
      <Page />
    </Layout>
  )
}
