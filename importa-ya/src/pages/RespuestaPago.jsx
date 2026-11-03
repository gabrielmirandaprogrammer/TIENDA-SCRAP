import { useSearchParams, Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import "./css/RespuestaPago.css";

const MENSAJES = {
  aprobado: ["¡Pago aprobado!", "Tu compra fue confirmada. El estado del pedido queda registrado y te contactaremos con los detalles."],
  pendiente: ["Pago pendiente", "Tu pago quedó en proceso. Te avisaremos cuando se confirme."],
  rechazado: ["Pago rechazado", "El pago no se pudo procesar. Puedes volver al carrito e intentar con otro medio de pago."],
  cancelado: ["Pago cancelado", "Cancelaste el pago. Tu carrito sigue disponible."],
};

function RespuestaPago() {
  const [params] = useSearchParams();
  const estado = params.get("estado") || "pendiente";
  const [titulo, detalle] = MENSAJES[estado] || MENSAJES.pendiente;

  return (
    <>
      <Navbar />
      <main className="respuesta-pago">
        <h1>{titulo}</h1>
        <p>{detalle}</p>
        <Link to="/" className="boton-volver">Volver a la tienda</Link>
      </main>
      <Footer />
    </>
  );
}

export default RespuestaPago;