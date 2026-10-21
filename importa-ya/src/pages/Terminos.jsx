import Navbar from "../components/Navbar";
import "./css/Terminos.css";

const secciones = [
  {
    id: "aceptacion",
    titulo: "1. Aceptación de los términos",
    contenido: `Al acceder, navegar o realizar una compra en Importa-Ya, el usuario acepta
    en su totalidad los presentes Términos y Condiciones. Si no estás de acuerdo con alguna
    de las disposiciones aquí establecidas, te pedimos que no utilices nuestra plataforma.
    Importa-Ya se reserva el derecho de modificar estos términos en cualquier momento;
    los cambios entrarán en vigor desde el momento de su publicación en el sitio.`,
  },
  {
    id: "uso",
    titulo: "2. Uso de la plataforma",
    contenido: `El sitio web de Importa-Ya está destinado exclusivamente a usuarios mayores de 18 años
    o menores acompañados de un adulto responsable. El usuario se compromete a:
    
    • Proporcionar información veraz y actualizada al momento del registro.
    • No utilizar la plataforma para fines ilegales, fraudulentos o que vulneren derechos de terceros.
    • No intentar acceder sin autorización a sistemas, cuentas o datos ajenos.
    • No reproducir, distribuir ni modificar el contenido del sitio sin autorización expresa.
    
    El incumplimiento de estas condiciones podrá resultar en la suspensión o eliminación permanente
    de la cuenta, sin previo aviso y sin derecho a reembolso.`,
  },
  {
    id: "productos",
    titulo: "3. Productos e información",
    contenido: `Importa-Ya realiza sus mejores esfuerzos para mantener la información de los productos
    (imágenes, descripciones, precios y disponibilidad) actualizada y precisa. Sin embargo, no garantizamos
    que dicha información esté libre de errores tipográficos, inexactitudes o desactualizaciones.
    
    Los precios están expresados en pesos colombianos (COP) e incluyen IVA cuando aplica, salvo que
    se indique lo contrario. Importa-Ya se reserva el derecho de modificar precios sin previo aviso.
    En caso de error de precio, nos comunicaremos con el comprador antes de procesar el envío.`,
  },
  {
    id: "compras",
    titulo: "4. Proceso de compra y pagos",
    contenido: `Al realizar un pedido en Importa-Ya, el usuario declara haber leído y aceptado estos
    términos. La confirmación del pedido se enviará al correo registrado y no implica por sí sola la
    aceptación definitiva de la orden; Importa-Ya podrá cancelar pedidos por razones de stock,
    errores de precio o sospecha de fraude.
    
    Los métodos de pago aceptados son los indicados en la pasarela de pago al momento de la compra.
    Importa-Ya no almacena datos de tarjetas de crédito o débito; el procesamiento es realizado por
    proveedores externos certificados.`,
  },
  {
    id: "envios",
    titulo: "5. Envíos y tiempos de entrega",
    contenido: `Los tiempos de entrega son estimados y pueden variar según la zona geográfica, la
    disponibilidad del producto y factores externos como huelgas, fenómenos naturales, festivos o
    demoras de las operadoras logísticas. Importa-Ya no se hace responsable por retrasos causados
    por terceros.
    
    El envío gratuito aplica únicamente en la primera compra y bajo las condiciones indicadas al
    momento de la transacción. Para compras posteriores, el costo de envío se calculará según peso,
    volumen y destino.`,
  },
  {
    id: "garantias",
    titulo: "6. Garantías y devoluciones — Léelo bien 👀",
    contenido: `Importa-Ya actúa como intermediario entre fabricantes, importadores y el usuario final.
    En consecuencia:
    
    • NO garantizamos el funcionamiento, la calidad ni la durabilidad de ningún producto vendido
      en la plataforma. Los productos se ofrecen "tal como están" y "según disponibilidad".
    
    • NO nos responsabilizamos por defectos de fábrica, daños en el transporte, incompatibilidades
      técnicas, alergias, uso indebido o expectativas del comprador que no correspondan a la
      descripción del producto.
    
    • En caso de producto defectuoso, el usuario deberá comunicarse directamente con el fabricante
      o importador. Importa-Ya podrá facilitar la gestión, pero no garantiza su resolución.
    
    • Las devoluciones se aceptarán únicamente dentro de los 5 días hábiles siguientes a la
      recepción, siempre que el producto esté sin uso, en su empaque original y acompañado de la
      factura. Los gastos de envío de devolución corren por cuenta del comprador.
    
    • Importa-Ya no reembolsará diferencias de precio por promociones posteriores a la compra,
      ni compensará por demoras en la entrega salvo que estas superen los 30 días hábiles.
    
    ¿Compraste un instrumento y suena horrible? Eso es arte. ¿Llegó con un tornillo de más?
    Considéralo un regalo. Bromas aparte: si tienes un problema real, escríbenos y haremos lo
    posible por ayudarte, pero legalmente no podemos prometerte nada más de lo indicado aquí.`,
    destacado: true,
  },
  {
    id: "privacidad",
    titulo: "7. Privacidad y datos personales",
    contenido: `El tratamiento de tus datos personales se rige por nuestra Política de Privacidad,
    disponible en /privacidad. Al registrarte y usar nuestra plataforma, autorizas la recolección
    y uso de tus datos para fines comerciales, de seguridad y mejora del servicio, conforme a la
    Ley 1581 de 2012 (Colombia) y demás normativa aplicable.
    
    Importa-Ya no venderá ni cederá tus datos a terceros con fines comerciales sin tu consentimiento
    previo, excepto cuando sea requerido por autoridades competentes.`,
  },
  {
    id: "propiedad",
    titulo: "8. Propiedad intelectual",
    contenido: `Todo el contenido de Importa-Ya — incluyendo logotipos, textos, imágenes, diseños
    y código fuente — es propiedad de Importa-Ya o de sus licenciantes y está protegido por las
    leyes de propiedad intelectual vigentes. Queda prohibida su reproducción total o parcial sin
    autorización escrita.`,
  },
  {
    id: "responsabilidad",
    titulo: "9. Limitación de responsabilidad",
    contenido: `En la máxima medida permitida por la ley, Importa-Ya no será responsable por:
    daños directos, indirectos, incidentales, especiales o consecuentes derivados del uso
    o la imposibilidad de uso de la plataforma; pérdida de datos; interrupciones del servicio;
    ni por actos u omisiones de terceros (transportistas, pasarelas de pago, proveedores).
    
    La responsabilidad total de Importa-Ya frente al usuario no superará, en ningún caso, el valor
    pagado por el producto o servicio que originó el reclamo.`,
  },
  {
    id: "ley",
    titulo: "10. Ley aplicable y jurisdicción",
    contenido: `Estos Términos y Condiciones se rigen por las leyes de la República de Colombia.
    Cualquier controversia que no pueda resolverse de forma amistosa será sometida a los tribunales
    competentes de la ciudad de Bogotá D.C., renunciando las partes a cualquier otro fuero que
    pudiera corresponderles.`,
  },
  {
    id: "contacto",
    titulo: "11. Contacto",
    contenido: `Si tienes dudas sobre estos términos, puedes escribirnos a través de nuestra página
    de contacto en /contacto o al correo soporte@importa-ya.com. Haremos lo posible por responderte
    en un plazo máximo de 5 días hábiles (o cuando consigamos el café).`,
  },
];

function Terminos() {
  const fechaActualizacion = "15 de octubre de 2026";

  return (
    <>
      <Navbar />

      <main className="terminos-page">
        {/* Hero */}
        <div className="terminos-hero">
          <div className="terminos-hero-inner">
            <h1>Términos y Condiciones</h1>
            <p>
              Última actualización: <strong>{fechaActualizacion}</strong>
            </p>
            <p className="terminos-hero-aviso">
              Sí, sabemos que nadie los lee. Pero si algo sale mal, aquí estará
              todo lo que aceptaste. 📄
            </p>
          </div>
        </div>

        <div className="terminos-layout">
          {/* Índice lateral */}
          <aside className="terminos-indice">
            <p className="terminos-indice-titulo">Contenido</p>
            <ul>
              {secciones.map((s) => (
                <li key={s.id}>
                  <a href={`#${s.id}`}>{s.titulo}</a>
                </li>
              ))}
            </ul>
          </aside>

          {/* Contenido */}
          <article className="terminos-contenido">
            {secciones.map((s) => (
              <section
                key={s.id}
                id={s.id}
                className={`terminos-seccion${s.destacado ? " destacada" : ""}`}
              >
                <h2>{s.titulo}</h2>
                {s.contenido.split("\n").map((linea, i) =>
                  linea.trim() === "" ? null : (
                    <p key={i}>{linea.trim()}</p>
                  )
                )}
              </section>
            ))}

            {/* Footer legal */}
            <div className="terminos-footer-legal">
              Al usar Importa-Ya, confirmas que has leído, entendido y aceptado
              estos términos. O al menos que fingiste haberlos leído, que para
              efectos legales es lo mismo. ✌️
            </div>
          </article>
        </div>
      </main>
    </>
  );
}

export default Terminos;
