import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from './components/layout/Layout'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import DocumentsPage from './pages/DocumentsPage'
import AskPage from './pages/AskPage'
import ChatPage from './pages/ChatPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'search',
        element: <SearchPage />,
      },
      {
        path: 'documents',
        element: <DocumentsPage />,
      },
      {
        path: 'ask',
        element: <AskPage />,
      },
      {
        path: 'ask/:sessionId',
        element: <ChatPage />,
      },
    ],
  },
])

function App() {
  return <RouterProvider router={router} />
}

export default App
