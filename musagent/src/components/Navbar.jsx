import { useState, useEffect, useRef } from 'react';

import { Link, useLocation } from 'react-router-dom';

import { ROUTES, NAV_GROUPS, NAV_PRIMARY, NAV_MORE } from '../config/routes.js';
import { useAuth } from '../context/AuthContext.jsx';



const Navbar = () => {

  const location = useLocation();
  const { user, logout, isLoggedIn } = useAuth();

  const [open, setOpen] = useState(false);

  const [moreOpen, setMoreOpen] = useState(false);

  const moreRef = useRef(null);



  useEffect(() => {

    setOpen(false);

    setMoreOpen(false);

  }, [location.pathname]);



  useEffect(() => {

    document.body.style.overflow = open ? 'hidden' : '';

    return () => { document.body.style.overflow = ''; };

  }, [open]);



  useEffect(() => {

    const onClick = (e) => {

      if (moreRef.current && !moreRef.current.contains(e.target)) {

        setMoreOpen(false);

      }

    };

    document.addEventListener('click', onClick);

    return () => document.removeEventListener('click', onClick);

  }, []);



  const isActive = (path) => location.pathname === path;



  return (

    <>

      <nav className="site-nav">

        <div className="site-nav-inner">

          <Link to={ROUTES.home.path} className="site-nav-brand">

            <img src="/images/logo.png" alt="MusAgent" className="site-nav-logo" />

            <span className="font-modern-negra">MusAgent</span>

          </Link>



          <div className="site-nav-desktop">

            <div className="site-nav-primary">

              {NAV_PRIMARY.map((item) => (

                <Link

                  key={item.path}

                  to={item.path}

                  className={isActive(item.path) ? 'is-active' : ''}

                  title={item.desc}

                >

                  {item.label}

                </Link>

              ))}

            </div>

            <div className={`site-nav-more ${moreOpen ? 'is-open' : ''}`} ref={moreRef}>

              <button

                type="button"

                className="site-nav-more-btn"

                aria-expanded={moreOpen}

                onClick={() => setMoreOpen((v) => !v)}

              >

                更多

                <span style={{ fontSize: '0.65rem' }}>{moreOpen ? '▲' : '▼'}</span>

              </button>

              <div className="site-nav-more-menu">

                {NAV_MORE.map((group) => (

                  <div key={group.group}>

                    <p className="site-nav-more-section">{group.group}</p>

                    {group.items.map((item) => (

                      <Link

                        key={item.path}

                        to={item.path}

                        className={isActive(item.path) ? 'is-active' : ''}

                        onClick={() => setMoreOpen(false)}

                      >

                        {item.label}

                      </Link>

                    ))}

                  </div>

                ))}

              </div>

            </div>

            <div className="site-nav-auth">
              {isLoggedIn ? (
                <>
                  <span className="site-nav-user font-cjk">{user?.displayName || user?.username}</span>
                  <button type="button" className="site-nav-auth-btn font-cjk" onClick={logout}>退出</button>
                </>
              ) : (
                <Link to={ROUTES.login.path} className="site-nav-auth-btn font-cjk is-login">登录</Link>
              )}
            </div>
          </div>



          <button

            type="button"

            className="site-nav-toggle"

            aria-label={open ? '关闭菜单' : '打开菜单'}

            aria-expanded={open}

            onClick={() => setOpen((v) => !v)}

          >

            <span className={open ? 'open' : ''} />

          </button>

        </div>

      </nav>



      <div className={`site-nav-drawer ${open ? 'is-open' : ''}`} aria-hidden={!open}>

        <div className="site-nav-drawer-backdrop" onClick={() => setOpen(false)} />

        <div className="site-nav-drawer-panel">

          <div className="site-nav-drawer-head">

            <p className="font-cjk text-xl font-semibold">导航</p>

            <button type="button" className="site-nav-drawer-close" onClick={() => setOpen(false)}>✕</button>

          </div>

          {NAV_GROUPS.map((group) => (

            <div key={group.id} className="site-nav-drawer-section">

              <p className="site-nav-drawer-section-label">{group.label}</p>

              <ul>

                {group.items.map((item) => (

                  <li key={item.path}>

                    <Link to={item.path} className={isActive(item.path) ? 'is-active' : ''}>

                      <span>{item.label}</span>

                      <span className="desc">{item.desc}</span>

                    </Link>

                  </li>

                ))}

              </ul>

            </div>

          ))}

          <Link to={ROUTES.home.path} className="site-nav-drawer-home">← 返回首页</Link>

        </div>

      </div>

    </>

  );

};



export default Navbar;

