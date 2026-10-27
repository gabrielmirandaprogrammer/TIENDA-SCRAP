// Carrito compartido guardado en localStorage. Los componentes se
// enteran de los cambios mediante un evento propio y el evento
// "storage" (para sincronizar entre pestañas del navegador).
const CLAVE_CARRITO = "carrito_importaya";
const EVENTO_CARRITO = "carrito:cambio";
const CANTIDAD_MAXIMA = 99;

function normalizarItem(item) {
  return {
    id: Number(item.id),
    nombre: String(item.nombre ?? ""),
    precio: Number(item.precio),
    imagen: typeof item.imagen === "string" ? item.imagen : "",
    cantidad: Math.min(
      Math.max(1, Math.floor(Number(item.cantidad) || 1)),
      CANTIDAD_MAXIMA
    ),
    // Estados calculados al sincronizar con la base.
    agotado: item.agotado === true,
    fuera_catalogo: item.fuera_catalogo === true,
  };
}

export function leerCarrito() {
  try {
    const datos = JSON.parse(localStorage.getItem(CLAVE_CARRITO) ?? "[]");

    if (!Array.isArray(datos)) {
      return [];
    }

    return datos
      .filter(
        (item) =>
          item &&
          typeof item === "object" &&
          Number.isFinite(Number(item.id)) &&
          Number.isFinite(Number(item.precio))
      )
      .map(normalizarItem);
  } catch {
    return [];
  }
}

export function guardarCarrito(carrito) {
  if (!Array.isArray(carrito)) {
    throw new Error("El carrito debe ser una lista de productos.");
  }

  localStorage.setItem(
    CLAVE_CARRITO,
    JSON.stringify(carrito.map(normalizarItem))
  );
  window.dispatchEvent(new CustomEvent(EVENTO_CARRITO));
}

// Devuelve la función para dejar de escuchar cambios.
export function suscribirseCarrito(callback) {
  const notificar = () => callback(leerCarrito());

  window.addEventListener(EVENTO_CARRITO, notificar);
  window.addEventListener("storage", notificar);

  return () => {
    window.removeEventListener(EVENTO_CARRITO, notificar);
    window.removeEventListener("storage", notificar);
  };
}

export function agregarProducto(producto, cantidad = 1) {
  const carrito = leerCarrito();
  const id = Number(producto.id);
  const existente = carrito.find((item) => item.id === id);
  const cantidadNueva = Math.max(1, Math.floor(Number(cantidad) || 1));

  if (existente) {
    existente.cantidad = Math.min(
      existente.cantidad + cantidadNueva,
      CANTIDAD_MAXIMA
    );
  } else {
    carrito.push({
      id,
      nombre: String(producto.nombre ?? ""),
      precio: Number(producto.precio),
      imagen:
        typeof producto.imagen_principal === "string"
          ? producto.imagen_principal
          : "",
      cantidad: Math.min(cantidadNueva, CANTIDAD_MAXIMA),
    });
  }

  guardarCarrito(carrito);
}

export function cambiarCantidad(id, cantidad) {
  const carrito = leerCarrito();
  const existente = carrito.find((item) => item.id === Number(id));

  if (!existente) {
    return;
  }

  existente.cantidad = Math.min(
    Math.max(1, Math.floor(Number(cantidad) || 1)),
    CANTIDAD_MAXIMA
  );

  guardarCarrito(carrito);
}

export function quitarProducto(id) {
  guardarCarrito(
    leerCarrito().filter((item) => item.id !== Number(id))
  );
}

export function vaciarCarrito() {
  guardarCarrito([]);
}

export function contarArticulos(carrito) {
  return (carrito ?? leerCarrito()).reduce(
    (total, item) => total + item.cantidad,
    0
  );
}