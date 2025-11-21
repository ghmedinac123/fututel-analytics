# domain/value_objects/score_cliente.py
"""Value Object para score de cliente."""
from dataclasses import dataclass

# ✅ IMPORTAR DOMAIN SERVICE
from futuisp_analytics.domain.services.score_calculator import ScoreCalculator


@dataclass(frozen=True)
class ScoreCliente:
    """Score de rendimiento del cliente."""
    
    total_facturas: int
    facturas_optimas: int
    facturas_aceptables: int
    facturas_criticas: int
    facturas_pendientes: int
    
    @property
    def score_total(self) -> float:
        """
        ✅ USA DOMAIN SERVICE para consistencia.
        """
        return ScoreCalculator.calcular_score(
            total_facturas=self.total_facturas,
            facturas_optimas=self.facturas_optimas,
            facturas_aceptables=self.facturas_aceptables,
            facturas_criticas=self.facturas_criticas,
            facturas_pendientes=self.facturas_pendientes,
        )
    
    @property
    def nivel_riesgo(self) -> str:
        """✅ USA DOMAIN SERVICE."""
        return ScoreCalculator.calcular_nivel_riesgo(self.score_total)
    
    @property
    def porcentaje_puntualidad(self) -> float:
        """✅ USA DOMAIN SERVICE."""
        return ScoreCalculator.calcular_porcentaje_puntualidad(
            total_facturas=self.total_facturas,
            facturas_optimas=self.facturas_optimas,
        )