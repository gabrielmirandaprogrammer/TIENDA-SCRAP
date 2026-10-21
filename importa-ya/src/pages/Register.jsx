import { useState } from "react";
import Navbar from "../components/Navbar";
import { supabase } from "../services/supabase";
import "./css/Registro.css";

const beneficios = [
  { icono: "🚚", titulo: "Envío gratis", texto: "En tu primera compra" },
  { icono: "🏷️", titulo: "Ofertas exclusivas", texto: "Hasta 60% OFF para miembros" },
  { icono: "📦", titulo: "Sigue tus compras", texto: "Mira el estado de tus pedidos" },
  { icono: "🔒", titulo: "Compra segura", texto: "Tus datos siempre protegidos" },
];

function nivelContrasena(password) {
  let puntos = 0;
  if (password.length >= 8) puntos++;
  if (/[A-Z]/.test(password)) puntos++;
  if (/[0-9]/.test(password)) puntos++;
  if (/[^A-Za-z0-9]/.test(password)) puntos++;

  if (!password) return null;
  if (puntos <= 1) return { texto: "Débil", clase: "debil" };
  if (puntos <= 2) return { texto: "Media", clase: "media" };
  return { texto: "Fuerte", clase: "fuerte" };
}

function Registro() {
  const [form, setForm] = useState({
    nombre: "",
    email: "",
    telefono: "",
    password: "",
    confirmar: "",
    terminos: false,
  });
  const [verPassword, setVerPassword] = useState(false);
  const [errores, setErrores] = useState({});
  const [mensaje, setMensaje] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const nivel = nivelContrasena(form.password);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
    setErrores({ ...errores, [name]: null });
    setMensaje(null);
  };

  const validar = () => {
    const nuevos = {};

    if (form.nombre.trim().length < 3) {
      nuevos.nombre = "Escribe tu nombre completo.";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      nuevos.email = "Escribe un correo válido.";
    }
    if (form.telefono && !/^[0-9]{7,15}$/.test(form.telefono)) {
      nuevos.telefono = "Escribe solo números (7 a 15 dígitos).";
    }
    if (form.password.length < 6) {
      nuevos.password = "La contraseña debe tener al menos 6 caracteres.";
    }
    if (form.password !== form.confirmar) {
      nuevos.confirmar = "Las contraseñas no coinciden.";
    }
    if (!form.terminos) {
      nuevos.terminos = "Debes aceptar los términos y condiciones.";
    }

    setErrores(nuevos);
    return Object.keys(nuevos).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validar()) return;

    setEnviando(true);
    setMensaje(null);

    const { data, error } = await supabase.auth.signUp({
      email: form.email.trim(),
      password: form.password,
      options: {
        data: {
          nombre: form.nombre.trim(),
          telefono: form.telefono,
        },
      },
    });

    setEnviando(false);

    if (error) {
      let texto = "No pudimos crear tu cuenta. Inténtalo de nuevo.";
      if (error.message.includes("already registered")) {
        texto = "Este correo ya tiene una cuenta. Intenta ingresar.";
      } else if (error.message.includes("Password")) {
        texto = "La contraseña no es válida. Usa al menos 6 caracteres.";
      }
      setMensaje({ tipo: "error", texto });
      return;
    }

    // Si Supabase pide confirmar el correo, no hay sesión todavía
    if (!data.session) {
      setMensaje({
        tipo: "exito",
        texto: `¡Listo! Te enviamos un correo a ${form.email}. Confírmalo para activar tu cuenta.`,
      });
    } else {
      setMensaje({ tipo: "exito", texto: "¡Cuenta creada! Redirigiendo..." });
      setTimeout(() => (window.location.href = "/"), 1500);
    }

    setForm({ nombre: "", email: "", telefono: "", password: "", confirmar: "", terminos: false });
  };

  return (
    <>
      <Navbar />

      <main className="registro-page">
        <div className="registro-container">
          {/* Columna izquierda: beneficios */}
          <section className="registro-info">
            <h1>Crea tu cuenta en Importa-Ya</h1>
            <p>Regístrate gratis y empieza a comprar los mejores instrumentos importados.</p>

            <ul className="registro-beneficios">
              {beneficios.map((b) => (
                <li key={b.titulo}>
                  <span className="registro-beneficio-icono">{b.icono}</span>
                  <div>
                    <strong>{b.titulo}</strong>
                    <p>{b.texto}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          {/* Columna derecha: formulario */}
          <section className="registro-card">
            <h2>Completa tus datos</h2>

            {mensaje && (
              <div className={`registro-alerta ${mensaje.tipo}`}>{mensaje.texto}</div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <div className="registro-campo">
                <label htmlFor="nombre">Nombre completo</label>
                <input
                  id="nombre"
                  name="nombre"
                  type="text"
                  placeholder="Ej: Juan Pérez"
                  value={form.nombre}
                  onChange={handleChange}
                  className={errores.nombre ? "con-error" : ""}
                  autoComplete="name"
                />
                {errores.nombre && <span className="registro-error">{errores.nombre}</span>}
              </div>

              <div className="registro-campo">
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
                {errores.email && <span className="registro-error">{errores.email}</span>}
              </div>

              <div className="registro-campo">
                <label htmlFor="telefono">
                  Celular <span className="registro-opcional">(opcional)</span>
                </label>
                <input
                  id="telefono"
                  name="telefono"
                  type="tel"
                  placeholder="3001234567"
                  value={form.telefono}
                  onChange={handleChange}
                  className={errores.telefono ? "con-error" : ""}
                  autoComplete="tel"
                />
                {errores.telefono && <span className="registro-error">{errores.telefono}</span>}
              </div>

              <div className="registro-campo">
                <label htmlFor="password">Contraseña</label>
                <div className="registro-password">
                  <input
                    id="password"
                    name="password"
                    type={verPassword ? "text" : "password"}
                    placeholder="Mínimo 6 caracteres"
                    value={form.password}
                    onChange={handleChange}
                    className={errores.password ? "con-error" : ""}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setVerPassword(!verPassword)}
                    aria-label={verPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  >
                    {verPassword ? "🙈" : "👁️"}
                  </button>
                </div>
                {nivel && (
                  <div className={`registro-nivel ${nivel.clase}`}>
                    <div className="registro-nivel-barra"><span /></div>
                    <small>Seguridad: {nivel.texto}</small>
                  </div>
                )}
                {errores.password && <span className="registro-error">{errores.password}</span>}
              </div>

              <div className="registro-campo">
                <label htmlFor="confirmar">Confirmar contraseña</label>
                <input
                  id="confirmar"
                  name="confirmar"
                  type={verPassword ? "text" : "password"}
                  placeholder="Repite tu contraseña"
                  value={form.confirmar}
                  onChange={handleChange}
                  className={errores.confirmar ? "con-error" : ""}
                  autoComplete="new-password"
                />
                {errores.confirmar && <span className="registro-error">{errores.confirmar}</span>}
              </div>

              <label className="registro-terminos">
                <input
                  type="checkbox"
                  name="terminos"
                  checked={form.terminos}
                  onChange={handleChange}
                />
                <span>
                  Acepto los <a href="/terminos">Términos y condiciones</a> y la{" "}
                  <a href="/privacidad">Política de privacidad</a>.
                </span>
              </label>
              {errores.terminos && <span className="registro-error">{errores.terminos}</span>}

              <button type="submit" className="registro-boton" disabled={enviando}>
                {enviando ? "Creando cuenta..." : "Crear cuenta"}
              </button>
            </form>

            <p className="registro-login">
              ¿Ya tienes cuenta? <a href="/ingresar">Ingresa</a>
            </p>
          </section>
        </div>
      </main>
    </>
  );
}

export default Registro;