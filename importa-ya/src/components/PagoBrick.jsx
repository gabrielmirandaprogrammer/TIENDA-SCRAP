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

                  // Desafío 3DS: MercadoPago pide validar en su página
                  if (data.tres_ds_url) {
                    window.location.href = data.tres_ds_url;
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
      {cargando && !error && <p className="pago-brick__estado">Cargando formulario de pago…</p>}
      {error && <p className="pago-brick__error">{error}</p>}
      {enviando && <p className="pago-brick__estado">Procesando el pago, no cierres esta página…</p>}
      <div id="paymentBrick_container" />
    </div>
  );
}