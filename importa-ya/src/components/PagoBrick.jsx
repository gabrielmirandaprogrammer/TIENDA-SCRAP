import { useEffect, useRef, useState } from "react";

const MP_SDK = "https://sdk.mercadopago.com/js/v2";

function cargarSdk() {
  if (window.MercadoPago) return Promise.resolve();
  if (window.__mpSdkPromise) return window.__mpSdkPromise;

  window.__mpSdkPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = MP_SDK;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("No se pudo cargar el SDK de MercadoPago"));
    document.head.appendChild(script);
  });

  return window.__mpSdkPromise;
}

export default function PagoBrick({ items, total, onResultado }) {
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [validando, setValidando] = useState(false);
  const [error, setError] = useState("");
  const controllerRef = useRef(null);
  const itemsRef = useRef(items);

  // Mantiene las cantidades actuales sin recrear el brick en cada render
  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    let activo = true;
    const publicKey = import.meta.env.VITE_MP_PUBLIC_KEY;

    if (!publicKey) {
      setError("Falta configurar VITE_MP_PUBLIC_KEY");
      setCargando(false);
      return;
    }

    (async () => {
      try {
        await cargarSdk();
        if (!activo) return;

        const mp = new window.MercadoPago(publicKey, { locale: "es-CO" });
        const bricksBuilder = mp.bricks();

        controllerRef.current = await bricksBuilder.create(
          "payment",
          "paymentBrick_container",
          {
            initialization: {
              amount: Number(total),
              payer: { email: "" },
            },
            customization: {
              visual: {
                style: { theme: "default" },
                texts: {
                  formTitle: "Paga con tarjeta",
                  emailSectionTitle: "Tus datos",
                  installmentsSectionTitle: "Cuotas",
                  cardNumber: { label: "Número de tarjeta" },
                  submit: "Pagar",
                },
              },
              paymentMethods: {
                creditCard: "all",
                debitCard: "all",
                maxInstallments: 12,
              },
            },
            callbacks: {
              onReady: () => {
                if (activo) setCargando(false);
              },
              onError: (err) => {
                console.error("Error del brick:", err);
                if (activo) setError("No se pudo cargar el formulario de pago.");
              },
              onSubmit: async ({ formData }) => {
                setError("");
                setEnviando(true);

                try {
                  const res = await fetch("/api/mercadopago/procesar-pago", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      items: itemsRef.current.map((i) => ({
                        id: i.id,
                        cantidad: i.cantidad,
                      })),
                      formData,
                    }),
                  });

                  const data = await res.json();

                  if (!res.ok) {
                    throw new Error(data.error || "No se pudo procesar el pago");
                  }

                  // Desafío 3DS: se valida en una ventana emergente para no
                  // salir de la tienda. Se sondea el estado del pago hasta
                  // que el banco apruebe o rechace.
                  if (data.tres_ds_url) {
                    const popup = window.open(
                      data.tres_ds_url,
                      "validacion_3ds",
                      "width=450,height=650"
                    );

                    if (!popup) {
                      // El navegador bloqueó la ventana emergente: no queda
                      // alternativa y hay que salir del sitio.
                      window.location.href = data.tres_ds_url;
                      return;
                    }

                    setValidando(true);

                    const pagoId = data.pago_id;
                    const inicio = Date.now();

                    const temporizador = setInterval(async () => {
                      try {
                        const resEstado = await fetch(
                          `/api/mercadopago/estado-pago?pago_id=${pagoId}`
                        );
                        const estado = await resEstado.json();

                        if (estado.estado && estado.estado !== "pendiente") {
                          clearInterval(temporizador);
                          popup.close();
                          setValidando(false);
                          onResultado({
                            estado: estado.estado,
                            pedido_id: estado.pedido_id,
                            mensaje: estado.detalle,
                          });
                          return;
                        }

                        if (popup.closed || Date.now() - inicio > 180000) {
                          clearInterval(temporizador);
                          setValidando(false);
                          onResultado({
                            estado: "pendiente",
                            pedido_id: estado.pedido_id,
                          });
                        }
                      } catch {
                        /* error puntual de red: reintenta en el siguiente tic */
                      }
                    }, 4000);

                    return;
                  }

                  onResultado?.(data);
                } catch (err) {
                  console.error("Error al procesar el pago:", err);
                  setError(err.message || "No se pudo procesar el pago.");
                } finally {
                  setEnviando(false);
                }
              },
            },
          }
        );
      } catch (err) {
        console.error("Error inicializando el brick:", err);
        if (activo) {
          setError(err.message || "No se pudo cargar el formulario de pago.");
          setCargando(false);
        }
      }
    })();

    return () => {
      activo = false;
      try {
        controllerRef.current?.unmount?.();
      } catch {
        /* el brick ya no existe */
      }
      controllerRef.current = null;
    };
  }, [total]);

  return (
    <div className="pago-brick">
      {cargando && !error && (
        <p className="pago-brick__estado">Cargando formulario de pago…</p>
      )}

      {error && <p className="pago-brick__error">{error}</p>}

      {enviando && (
        <p className="pago-brick__estado">
          Procesando el pago, no cierres esta página…
        </p>
      )}

      {validando && (
        <p className="pago-brick__estado" role="status">
          Validando tu tarjeta con el banco: completa la verificación en la
          ventana emergente, no cierres esta página…
        </p>
      )}

      <div id="paymentBrick_container" />
    </div>
  );
}

export { cargarSdk };