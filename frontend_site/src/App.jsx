"use client"
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import './App.css';
import Home from './pages/Home';
import Login from './pages/Login';
import Resume from './pages/Resume';
import Register from './pages/Register';
import Wrapper from './pages/Wrapper';



function App() {
  return (
    <Router>
      <Routes>
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route 
          path="/" 
          element={
            <Wrapper>
              <Home />
            </Wrapper>
          }
        />
        <Route 
          path="/resume" 
          element={
            <Wrapper>
              <Resume />
            </Wrapper>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
