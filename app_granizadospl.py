        if v.get("Medio de pago") != "Efectivo"
    )
    gastos_dia_total = sum(float(g.get("Valor", 0)) for g in gastos_dia)
    unidades_dia = sum(int(v.get("Cantidad", 0)) for v in ventas_dia)
    total_ventas_dia = efectivo_dia + transferencias_dia
    balance_dia = total_ventas_dia - gastos_dia_total

    st.write(f"Fecha de la jornada: **{fecha_cierre}**")
    met1, met2, met3, met4 = st.columns(4)
    met1.metric("Ventas del día", pesos(total_ventas_dia))
    met2.metric("Unidades vendidas", unidades_dia)
    met3.metric("Gastos efectivos del día", pesos(gastos_dia_total))
    met4.metric("Balance del día", pesos(balance_dia))
    met5, met6 = st.columns(2)
    met5.metric("Efectivo recibido", pesos(efectivo_dia))
    met6.metric("Transferencias recibidas", pesos(transferencias_dia))

    cierre_existente = next(
        (c for c in st.session_state.cierres_caja if c.get("Fecha") == fecha_cierre),
        None,
    )
    if cierre_existente:
        st.info(
            "La caja de hoy ya fue cerrada el "
            f"{cierre_existente.get('Fecha y hora', '')}. "
            "El cierre guardado se conserva en el historial."
        )
        st.json(cierre_existente)
    else:
        st.warning(
            "Al confirmar, se guardará una fotografía del resumen de hoy. "
            "Los movimientos nuevos posteriores no modificarán este cierre."
        )
        if st.button(
            "🔒 Confirmar y guardar cierre de caja",
            type="primary", use_container_width=True,
        ):
            cierre = {
                "Fecha": fecha_cierre,
                "Fecha y hora": ahora(),
                "Número de ventas": len(ventas_dia),
                "Unidades vendidas": unidades_dia,
                "Ventas totales": total_ventas_dia,
                "Efectivo": efectivo_dia,
                "Transferencias": transferencias_dia,
                "Gastos efectivos": gastos_dia_total,
                "Balance": balance_dia,
                "Detalle de ventas": [
                    {
                        "ID": v.get("ID"), "Sabor": v.get("Sabor"),
                        "Cantidad": v.get("Cantidad"), "Total": v.get("Total"),
                        "Medio de pago": v.get("Medio de pago"),
                    }
                    for v in ventas_dia
                ],
                "Detalle de gastos": [
                    {
                        "Concepto": g.get("Concepto"), "Valor": g.get("Valor"),
                        "Tipo": g.get("Tipo", "Gasto general"),
                    }
                    for g in gastos_dia
                ],
            }
            st.session_state.cierres_caja.append(cierre)
            guardar_datos()
            st.success("Cierre de caja guardado correctamente.")
            st.rerun()

    st.divider()
    st.subheader("📚 Cierres anteriores")
    if st.session_state.cierres_caja:
        cierres_ordenados = sorted(
            st.session_state.cierres_caja,
            key=lambda c: c.get("Fecha", ""),
            reverse=True,
        )
        resumen_cierres = [
            {
                "Fecha": c.get("Fecha", ""),
                "Fecha y hora": c.get("Fecha y hora", ""),
                "Ventas": pesos(c.get("Ventas totales", 0)),
                "Efectivo": pesos(c.get("Efectivo", 0)),
                "Transferencias": pesos(c.get("Transferencias", 0)),
                "Gastos": pesos(c.get("Gastos efectivos", 0)),
                "Balance": pesos(c.get("Balance", 0)),
                "Unidades": c.get("Unidades vendidas", 0),
            }
            for c in cierres_ordenados
        ]
        st.dataframe(
            pd.DataFrame(resumen_cierres),
            hide_index=True,
            use_container_width=True,
        )
        fechas_disponibles = [c.get("Fecha", "") for c in cierres_ordenados]
        fecha_consulta = st.selectbox(
            "Consultar detalle de un cierre anterior",
            fechas_disponibles,
            key="fecha_consultar_cierre",
        )
        detalle_cierre = next(
            c for c in cierres_ordenados if c.get("Fecha", "") == fecha_consulta
        )
        st.json(detalle_cierre)
        csv_cierres = pd.DataFrame(resumen_cierres).to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Descargar historial de cierres CSV",
            data=csv_cierres,
            file_name="cierres_caja_granizados_pl.csv",
            mime="text/csv",
        )
    else:
        st.info("Todavía no hay cierres de caja guardados.")

# =========================================================
# PIE DE PAGINA
# =========================================================
st.divider()
st.caption(
    "Granizados PL · Los datos se guardan localmente en "
    "la carpeta datos_granizados_pl."
