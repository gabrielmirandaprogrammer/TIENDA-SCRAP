import { useState } from "react";
import Navbar from "../components/Navbar";
import { supabase } from "../services/supabase";
import "./css/login.css";

function Ingresar() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [verPassword, setVerPassword] = useState(false);
  const [errores, setErrores] = useState({});
  const [mensaje, setMensaje] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
    setErrores({ ...errores, [name]: null });
    setMensaje(null);
  };

  const validar = () => {
    const nuevos = {};
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      nuevos.email = "Escribe un correo válido.";
    }
    if (form.password.length < 6) {
      nuevos.password = "La contraseña debe tener al menos 6 caracteres.";
    }
    setErrores(nuevos);
    return Object.keys(nuevos).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validar()) return;

    setEnviando(true);
    setMensaje(null);

    const { error } = await supabase.auth.signInWithPassword({
      email: form.email.trim(),
      password: form.password,
    });

    setEnviando(false);

    if (error) {
      let texto = "No pudimos iniciar sesión. Inténtalo de nuevo.";
      if (
        error.message.includes("Invalid login credentials") ||
        error.message.includes("invalid_credentials")
      ) {
        texto = "Correo o contraseña incorrectos.";
      } else if (error.message.includes("Email not confirmed")) {
        texto = "Debes confirmar tu correo antes de ingresar. Revisa tu bandeja.";
      }
      setMensaje({ tipo: "error", texto });
      return;
    }

    setMensaje({ tipo: "exito", texto: "¡Bienvenido! Redirigiendo..." });
    setTimeout(() => (window.location.href = "/"), 1200);
  };

  const handleGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
  };

  return (
    <>
      <Navbar />

      <main className="ingresar-page">
        <div className="ingresar-card">
          <h1>Ingresa a tu cuenta</h1>
          <p className="ingresar-subtitulo">
            ¿No tienes cuenta? <a href="/Register">Regístrate gratis</a>
          </p>

          {mensaje && (
            <div className={`ingresar-alerta ${mensaje.tipo}`}>{mensaje.texto}</div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            {/* Email */}
            <div className="ingresar-campo">
              <label htmlFor="email">Correo electrónico</label>
              <input
                id="email"
                name="email"
                type="email"
                placeholder="tucorreo@ejemplo.com"
                value={form.email}
                onChange={handleChange}
                className={errores.email ? "con-error" : ""}
                autoComplete="email"
              />
              {errores.email && (
                <span className="ingresar-error">{errores.email}</span>
              )}
            </div>

            {/* Contraseña */}
            <div className="ingresar-campo">
              <div className="ingresar-label-row">
                <label htmlFor="password">Contraseña</label>
                <a href="/recuperar" className="ingresar-olvidaste">
                  ¿Olvidaste tu contraseña?
                </a>
              </div>
              <div className="ingresar-password">
                <input
                  id="password"
                  name="password"
                  type={verPassword ? "text" : "password"}
                  placeholder="Tu contraseña"
                  value={form.password}
                  onChange={handleChange}
                  className={errores.password ? "con-error" : ""}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setVerPassword(!verPassword)}
                  aria-label={verPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {verPassword ? "🙈" : "👁️"}
                </button>
              </div>
              {errores.password && (
                <span className="ingresar-error">{errores.password}</span>
              )}
            </div>

            {/* Botón submit */}
            <button type="submit" className="ingresar-boton" disabled={enviando}>
              {enviando ? "Ingresando..." : "Ingresar"}
            </button>
          </form>

          {/* Divisor */}
          <div className="ingresar-divisor">
            <span>o continúa con</span>
          </div>

          {/* Google */}
          <button className="ingresar-google" onClick={handleGoogle}>
            <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
            Continuar con Google
          </button>
        </div>
      </main>
    </>
  );
}

export default Ingresar;
