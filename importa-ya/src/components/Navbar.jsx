import { useEffect, useState } from "react";
import Buscador from "../components/js/busqueda";
import logo from "../assets/IconLogo.png";
import { supabase } from "../services/supabase";
import "./css/navbar.css";

function Navbar({ productos }) {
  const [usuario, setUsuario] = useState(null);

  useEffect(() => {
    // Sesión inicial
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUsuario(session?.user ?? null);
    });

    // Escucha cambios en tiempo real (login / logout)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUsuario(session?.user ?? null);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const handleCerrarSesion = async () => {
    await supabase.auth.signOut();
    window.location.href = "/";
  };

  return (
    <header className="ml-navbar">
      {/* Fila superior: logo + buscador + promo */}
      <div className="ml-navbar-top">
        <a href="/" className="ml-navbar-logo">
          <img src={logo} alt="Importa-Ya" />
          <span>Importa-Ya</span>
        </a>

        <div className="ml-navbar-search">
          <Buscador productos={productos} />
        </div>

        <div className="ml-navbar-promo">
          🚚 <strong>Envío gratis</strong> en tu primera compra
        </div>
      </div>

      {/* Fila inferior: enlaces + usuario */}
      <div className="ml-navbar-bottom">
        <nav className="ml-navbar-links">
          <a href="/">Inicio</a>
          <a href="/productos">Productos</a>
          <a href="/categorias">Categorías</a>
          <a href="/contacto">Contacto</a>
        </nav>

        <div className="ml-navbar-user">
          {usuario ? (
            /* ── Usuario autenticado ── */
            <>
              <span className="ml-navbar-saludo">
                Hola, {usuario.user_metadata?.nombre?.split(" ")[0] || "Usuario"}
              </span>
              <a href="/compras">Mis compras</a>
              <button
                className="ml-navbar-cerrar"
                onClick={handleCerrarSesion}
              >
                Cerrar sesión
              </button>
            </>
          ) : (
            /* ── Sin sesión ── */
            <>
              <a href="/Register">Crea tu cuenta</a>
              <a href="/Login">Ingresa</a>
            </>
          )}

          {/* Carrito siempre visible */}
          <a href="/carrito" className="ml-navbar-cart" aria-label="Carrito">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="21" r="1" />
              <circle cx="20" cy="21" r="1" />
              <path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
