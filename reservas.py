"""
Módulo de gestión de reservas para Software FJ.
Integra cliente, servicio, duración y estado con confirmación, cancelación,
procesamiento, manejo de excepciones, encadenamiento y registro en log.
"""

from datetime import datetime
import logging
from pathlib import Path


# Configura el archivo de logs en la raíz del proyecto para registrar eventos y errores
RUTA_LOG = Path("sistema_software_fj.log")
logging.basicConfig(
    filename=str(RUTA_LOG),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("SoftwareFJ.Reservas")


class ErrorReservaBase(Exception):
    """Excepción base para errores relacionados con la gestión de reservas."""


class ParametroInvalidoReservaError(ErrorReservaBase):
    """Se lanza cuando faltan parámetros obligatorios o tienen valores inválidos."""


class ServicioNoDisponibleError(ErrorReservaBase):
    """Se lanza cuando se intenta reservar o confirmar un servicio no disponible."""


class EstadoReservaInvalidoError(ErrorReservaBase):
    """Se lanza cuando la operación no es permitida para el estado actual de la reserva."""


class CalculoReservaError(ErrorReservaBase):
    """Se lanza cuando ocurre un error al calcular el costo de la reserva."""


class Reserva:
    """
    Representa una reserva dentro de Software FJ integrando cliente,
    servicio, duración en horas y estado del ciclo de vida.
    """

    ESTADOS_VALIDOS = ("PENDIENTE", "CONFIRMADA", "PROCESADA", "CANCELADA")

    def __init__(
        self,
        codigo_reserva: str,
        cliente: object,
        servicio: object,
        duracion: int,
        impuesto: float = 0.19,
        descuento: float = 0.0,
        recargo_extra: float = 0.0,
    ):
        # Valida y asigna atributos encapsulados de la reserva
        self._codigo = self._validar_codigo(codigo_reserva)
        self._cliente = self._validar_cliente(cliente)
        self._servicio = self._validar_servicio(servicio)
        self._duracion = self._validar_duracion(duracion)
        self._impuesto = impuesto
        self._descuento = descuento
        self._recargo_extra = recargo_extra
        # Toda reserva inicia en estado PENDIENTE
        self._estado = "PENDIENTE"
        self._fecha_creacion = datetime.now().isoformat(timespec="seconds")
        self._total_calculado = 0.0

        logger.info(
            f"Reserva creada | Código: {self._codigo} | Cliente: {getattr(self._cliente, 'nombre', 'N/A')} "
            f"| Servicio: {getattr(self._servicio, 'codigo', 'N/A')} | Duración: {self._duracion}h | Estado: {self._estado}"
        )

    @property
    def codigo(self) -> str:
        """Retorna el identificador único de la reserva."""
        return self._codigo

    @property
    def cliente(self) -> object:
        """Retorna el cliente asociado a la reserva."""
        return self._cliente

    @property
    def servicio(self) -> object:
        """Retorna el servicio asociado a la reserva."""
        return self._servicio

    @property
    def duracion(self) -> int:
        """Retorna la duración de la reserva en horas."""
        return self._duracion

    @property
    def estado(self) -> str:
        """Retorna el estado actual de la reserva."""
        return self._estado

    @property
    def total_calculado(self) -> float:
        """Retorna el último costo calculado para la reserva."""
        return self._total_calculado

    def _validar_codigo(self, codigo: str) -> str:
        """Valida que el código de reserva sea un texto no vacío."""
        if not isinstance(codigo, str) or not codigo.strip():
            raise ParametroInvalidoReservaError("El código de la reserva es obligatorio y debe ser un texto.")
        return codigo.strip()

    def _validar_cliente(self, cliente: object) -> object:
        """Valida que exista un cliente válido con atributos básicos."""
        if cliente is None:
            raise ParametroInvalidoReservaError("La reserva requiere un cliente válido (parámetro faltante).")
        nombre = getattr(cliente, "nombre", None)
        if not isinstance(nombre, str) or not nombre.strip():
            raise ParametroInvalidoReservaError("El cliente asociado no tiene un nombre válido.")
        return cliente

    def _validar_servicio(self, servicio: object) -> object:
        """Valida que exista un servicio válido y disponible."""
        if servicio is None:
            raise ParametroInvalidoReservaError("La reserva requiere un servicio válido (parámetro faltante).")
        if not hasattr(servicio, "calcular_costo") or not hasattr(servicio, "disponible"):
            raise ParametroInvalidoReservaError("El objeto proporcionado no es un servicio válido de Software FJ.")
        if not servicio.disponible:
            raise ServicioNoDisponibleError(
                f"El servicio '{getattr(servicio, 'nombre', servicio)}' no está disponible para reservas."
            )
        return servicio

    def _validar_duracion(self, duracion: int) -> int:
        """Valida que la duración sea un número entero positivo."""
        if isinstance(duracion, bool) or not isinstance(duracion, int) or duracion <= 0:
            raise ParametroInvalidoReservaError("La duración de la reserva debe ser un entero mayor a cero.")
        return duracion

    def calcular_total(self) -> float:
        """
        Calcula el costo total de la reserva encadenando excepciones si ocurre
        un error interno en el cálculo del servicio.
        """
        try:
            # Llama al método polimórfico calcular_costo del servicio con parámetros opcionales
            total = self._servicio.calcular_costo(
                duracion=self._duracion,
                impuesto=self._impuesto,
                descuento=self._descuento,
                recargo_extra=self._recargo_extra,
            )
        except Exception as exc:
            # Encadena la excepción original con una excepción de dominio de reserva
            logger.error(f"Error al calcular costo en reserva {self._codigo}: {exc}")
            raise CalculoReservaError(
                f"No se pudo calcular el costo de la reserva '{self._codigo}'."
            ) from exc
        else:
            # Solo se actualiza el total si no hubo excepciones en el bloque try
            self._total_calculado = float(total)
            return self._total_calculado
        finally:
            # Registra trazabilidad de que se intentó calcular el valor de la reserva
            logger.info(f"Intento de cálculo finalizado | Reserva: {self._codigo} | Total: {self._total_calculado}")

    def confirmar(self) -> str:
        """Confirma una reserva pendiente verificando disponibilidad y estado."""
        try:
            # Impide confirmar reservas canceladas o ya procesadas
            if self._estado == "CANCELADA":
                raise EstadoReservaInvalidoError(
                    f"No se puede confirmar la reserva '{self._codigo}' porque ya fue cancelada."
                )
            if self._estado == "PROCESADA":
                raise EstadoReservaInvalidoError(
                    f"No se puede confirmar la reserva '{self._codigo}' porque ya fue procesada."
                )
            if not self._servicio.disponible:
                raise ServicioNoDisponibleError(
                    f"No se puede confirmar la reserva '{self._codigo}': el servicio no está disponible."
                )

            # Calcula el valor actualizado antes de confirmar
            total = self.calcular_total()
        except ErrorReservaBase as exc:
            logger.error(f"Fallo al confirmar reserva {self._codigo}: {exc}")
            raise
        else:
            self._estado = "CONFIRMADA"
            mensaje = f"Reserva {self._codigo} CONFIRMADA por un total de ${total:.2f}."
            logger.info(mensaje)
            return mensaje
        finally:
            logger.info(f"Estado tras intentar confirmar {self._codigo}: {self._estado}")

    def cancelar(self, motivo: str = "Cancelación solicitada por el cliente") -> str:
        """Cancela una reserva si su estado actual permite la operación."""
        try:
            if not isinstance(motivo, str) or not motivo.strip():
                raise ParametroInvalidoReservaError("Debe indicar un motivo válido para cancelar la reserva.")
            if self._estado == "PROCESADA":
                raise EstadoReservaInvalidoError(
                    f"Operación no permitida: la reserva '{self._codigo}' ya fue procesada y no puede cancelarse."
                )
            if self._estado == "CANCELADA":
                raise EstadoReservaInvalidoError(
                    f"La reserva '{self._codigo}' ya se encuentra cancelada."
                )
        except ErrorReservaBase as exc:
            logger.error(f"Fallo al cancelar reserva {self._codigo}: {exc}")
            raise
        else:
            self._estado = "CANCELADA"
            mensaje = f"Reserva {self._codigo} CANCELADA. Motivo: {motivo.strip()}"
            logger.info(mensaje)
            return mensaje
        finally:
            logger.info(f"Estado tras intentar cancelar {self._codigo}: {self._estado}")

    def procesar(self) -> dict:
        """
        Procesa una reserva confirmada (o la confirma si estaba pendiente)
        y deja el registro final del procesamiento.
        """
        resultado = {}
        try:
            if self._estado == "CANCELADA":
                raise EstadoReservaInvalidoError(
                    f"No se puede procesar la reserva '{self._codigo}' porque está CANCELADA."
                )
            if self._estado == "PROCESADA":
                raise EstadoReservaInvalidoError(
                    f"La reserva '{self._codigo}' ya fue PROCESADA anteriormente."
                )
            if not self._servicio.disponible:
                raise ServicioNoDisponibleError(
                    f"No se puede procesar la reserva '{self._codigo}': servicio no disponible."
                )

            # Si estaba pendiente, se confirma primero
            if self._estado == "PENDIENTE":
                self.confirmar()

            total = self.calcular_total()
            self._estado = "PROCESADA"
            resultado = {
                "codigo_reserva": self._codigo,
                "cliente": getattr(self._cliente, "nombre", "N/A"),
                "servicio": getattr(self._servicio, "nombre", "N/A"),
                "duracion_horas": self._duracion,
                "total": total,
                "estado": self._estado,
            }
        except ErrorReservaBase as exc:
            logger.error(f"Error procesando reserva {self._codigo}: {exc}")
            raise
        else:
            logger.info(
                f"Reserva {self._codigo} PROCESADA exitosamente | Total: ${resultado['total']:.2f}"
            )
            return resultado
        finally:
            logger.info(f"Cierre de flujo procesar() | Reserva: {self._codigo} | Estado final: {self._estado}")

    def describir(self) -> str:
        """Retorna un resumen legible del estado actual de la reserva."""
        nombre_cliente = getattr(self._cliente, "nombre", "Desconocido")
        nombre_servicio = getattr(self._servicio, "nombre", "Desconocido")
        return (
            f"[Reserva {self._codigo}] Cliente: {nombre_cliente} | Servicio: {nombre_servicio} "
            f"| Duración: {self._duracion}h | Estado: {self._estado} | Total: ${self._total_calculado:.2f}"
        )


class GestorReservas:
    """Gestiona una colección en memoria (lista) de reservas sin usar base de datos."""

    def __init__(self):
        # Lista interna de objetos Reserva en memoria
        self._reservas: list[Reserva] = []

    @property
    def reservas(self) -> list[Reserva]:
        """Retorna la lista de reservas registradas."""
        return list(self._reservas)

    def agregar_reserva(self, reserva: Reserva) -> None:
        """Agrega una instancia válida de Reserva a la lista interna."""
        if not isinstance(reserva, Reserva):
            raise ParametroInvalidoReservaError("Solo se pueden agregar objetos de tipo Reserva.")
        self._reservas.append(reserva)
        logger.info(f"Reserva {reserva.codigo} agregada al gestor en memoria. Total en lista: {len(self._reservas)}")

    def buscar_por_codigo(self, codigo: str) -> Reserva:
        """Busca una reserva por código o lanza excepción si no existe."""
        for reserva in self._reservas:
            if reserva.codigo == codigo:
                return reserva
        raise ErrorReservaBase(f"No se encontró ninguna reserva con el código '{codigo}'.")
