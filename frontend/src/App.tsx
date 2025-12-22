import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from './components/layout/Layout'
import ChatPage from './pages/ChatPage'
import WelcomeState from './components/chat/WelcomeState'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <WelcomeState />,
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
