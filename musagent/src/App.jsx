import gsap from 'gsap';

import { ScrollTrigger, SplitText } from 'gsap/all';

import { Routes, Route, Navigate } from 'react-router-dom';



import Navbar from './components/Navbar.jsx';

import Home from './pages/Home.jsx';

import InspirePage from './pages/InspirePage.jsx';

import LibraryPage from './pages/LibraryPage.jsx';

import AboutPage from './pages/AboutPage.jsx';

import PolishPage from './pages/PolishPage.jsx';

import SummaryPage from './pages/SummaryPage.jsx';

import CorrectPage from './pages/CorrectPage.jsx';

import EvaluatePage from './pages/EvaluatePage.jsx';

import TechStackPage from './pages/TechStackPage.jsx';

import KnowledgeGraphPage from './pages/KnowledgeGraphPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import { LEGACY_REDIRECTS } from './config/routes.js';



gsap.registerPlugin(ScrollTrigger, SplitText);



const LegacyRedirect = ({ to }) => <Navigate to={to} replace />;



const App = () => (

  <main>

    <Navbar />

    <Routes>

      <Route path="/" element={<Home />} />

      <Route path="/inspire" element={<InspirePage />} />

      <Route path="/library" element={<LibraryPage />} />

      <Route path="/polish" element={<PolishPage />} />

      <Route path="/summary" element={<SummaryPage />} />

      <Route path="/correct" element={<CorrectPage />} />

      <Route path="/workflow" element={<AboutPage />} />

      <Route path="/stack" element={<TechStackPage />} />

      <Route path="/login" element={<LoginPage />} />

      <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />

      <Route path="/evaluate" element={<EvaluatePage />} />
      <Route path="/benchmark" element={<EvaluatePage />} />

      {Object.entries(LEGACY_REDIRECTS).map(([from, to]) => (

        <Route key={from} path={from} element={<LegacyRedirect to={to} />} />

      ))}

    </Routes>

  </main>

);



export default App;

