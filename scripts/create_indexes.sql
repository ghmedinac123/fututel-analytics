-- Optimización para queries de análisis
CREATE INDEX IF NOT EXISTS idx_facturas_emitido_estado_idcliente 
ON facturas(emitido, estado, idcliente);

CREATE INDEX IF NOT EXISTS idx_operaciones_nfactura_fecha_cobrado 
ON operaciones(nfactura, fecha_pago, cobrado);

CREATE INDEX IF NOT EXISTS idx_tblavisouser_cliente 
ON tblavisouser(cliente);

CREATE INDEX IF NOT EXISTS idx_usuarios_estado 
ON usuarios(estado, id);

-- Ver índices creados
SHOW INDEX FROM facturas;
SHOW INDEX FROM operaciones;