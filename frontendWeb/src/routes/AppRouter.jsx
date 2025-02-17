import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Login from '../app/auth/Login'

const AppRouter = () => {
  return (
    <Routes>
        <Route path='/login' element={<Login />} />
    </Routes>
  )
}

export default AppRouter;