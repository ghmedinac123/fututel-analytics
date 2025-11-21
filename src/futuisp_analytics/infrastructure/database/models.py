"""Modelos SQLAlchemy (solo lectura)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, String, Date, DateTime, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Clase base para modelos."""
    pass


class Usuario(Base):
    """Modelo de usuarios."""
    __tablename__ = "usuarios"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(400))
    estado: Mapped[str] = mapped_column(String(300))
    correo: Mapped[str] = mapped_column(String)  # ✅ AGREGADO
    telefono: Mapped[str] = mapped_column(String(50))  # ✅ AGREGADO
    movil: Mapped[str] = mapped_column(String)  # ✅ AGREGADO
    cedula: Mapped[str] = mapped_column(String(100))  # ✅ AGREGADO
    direccion_principal: Mapped[str] = mapped_column(String)  # ✅ AGREGADO
    fecha_instalacion: Mapped[date | None] = mapped_column(Date, nullable=True)  # ✅ AGREGADO
    
    # Relaciones
    facturas: Mapped[list["Factura"]] = relationship(back_populates="usuario")
    aviso: Mapped["TblAvisoUser"] = relationship(back_populates="usuario")


class Factura(Base):
    """Modelo de facturas."""
    __tablename__ = "facturas"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idcliente: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"))
    emitido: Mapped[date] = mapped_column(Date)
    vencimiento: Mapped[date] = mapped_column(Date)
    pago: Mapped[date] = mapped_column(Date)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    estado: Mapped[str] = mapped_column(String(10))
    cobrado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    
    # Relaciones
    usuario: Mapped["Usuario"] = relationship(back_populates="facturas")
    operaciones: Mapped[list["Operacion"]] = relationship(back_populates="factura")


class Operacion(Base):
    """Modelo de operaciones (pagos)."""
    __tablename__ = "operaciones"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nfactura: Mapped[int] = mapped_column(Integer, ForeignKey("facturas.id"))
    idcliente: Mapped[int] = mapped_column(Integer)
    fecha_pago: Mapped[datetime] = mapped_column(DateTime)
    operador: Mapped[int] = mapped_column(Integer, ForeignKey("login.id"))
    cobrado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    forma_pago: Mapped[str] = mapped_column(String)
    cedula: Mapped[str] = mapped_column(String(20))
    
    # Relaciones
    factura: Mapped["Factura"] = relationship(back_populates="operaciones")
    operador_info: Mapped["Login"] = relationship(back_populates="operaciones")


class TblAvisoUser(Base):
    """Modelo de configuración de usuarios."""
    __tablename__ = "tblavisouser"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"))
    corteautomatico: Mapped[int] = mapped_column(Integer)
    zona: Mapped[int] = mapped_column(Integer)
    
    # Relaciones
    usuario: Mapped["Usuario"] = relationship(back_populates="aviso")


class Login(Base):
    """Modelo de operadores."""
    __tablename__ = "login"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(300))
    username: Mapped[str] = mapped_column(String(50))
    
    # Relaciones
    operaciones: Mapped[list["Operacion"]] = relationship(back_populates="operador_info")