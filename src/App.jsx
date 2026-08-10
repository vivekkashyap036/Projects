import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import NewGame from './pages/NewGame'
import Play from './pages/Play'
import Rules from './pages/Rules'
import History from './pages/History'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/new" element={<NewGame />} />
        <Route path="/play" element={<Play />} />
        <Route path="/rules" element={<Rules />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </Layout>
  )
}

export default App
