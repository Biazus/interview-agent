import { BrowserRouter, Route, Routes } from 'react-router-dom'

function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold text-blue-600">
        Interview Agent
      </h1>
      <p className="text-gray-600">Frontend MVP — Tailwind v4 ready</p>
    </main>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
