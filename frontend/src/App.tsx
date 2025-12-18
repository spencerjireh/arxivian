import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from './components/layout/Layout'
import AskPage from './pages/AskPage'
import ChatPage from './pages/ChatPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <AskPage />,
      },
      {
        path: ':sessionId',
        element: <ChatPage />,
      },
    ],
  },
])

function App() {
  return <RouterProvider router={router} />
}

export default App
