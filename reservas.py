import logging
from datetime import datetime
from typing import Dict, List, Optional


logger = logging.getLogger("SoftwareFJ")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    _file_handler = logging.FileHandler("sistema_software_fj.log", mode="a", encoding="utf-8")
    _file_handler.setFormatter(_formatter)
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_formatter)
    logger.addHandler(_file_handler)
    logger.addHandler(_stream_handler)


class ErrorReserva(Exception):
    """Excepcion base para errores del modulo de reservas."""


class ParametroReservaInvalidoError(ErrorReserva):
    """Datos de entrada invalidos en la reserva."""


class ServicioNoDisponibleError(ErrorReserva):
    """El servicio solicitado no esta disponible."""


class ReservaNoEncontradaError(ErrorReserva):
    """No existe la reserva consultada en memoria."""


class EstadoReservaInvalidoError(ErrorReserva):
    """Transicion o estado no permitido para la reserva."""


class Reserva:
    """Representa una reserva en memoria para Software FJ."""

    def __init__(
        self,
        codigo_reserva: str,
        cliente: str,
        servicio: object,
        duracion: int,
        impuesto: float = 0.19,
        descuento: float = 0.0,
        recargo_extra: float = 0.0,
        fecha_registro: Optional[str] = None
    ):
        if not isinstance(codigo_reserva, str) or not codigo_reserva.strip():
            raise ParametroReservaInvalidoError("El codigo de reserva debe ser un texto no vacio.")
        if not isinstance(cliente, str) or not cliente.strip():
            raise ParametroReservaInvalidoError("El nombre del cliente debe ser un texto no vacio.")
        if servicio is None or not hasattr(servicio, "calcular_costo") or not hasattr(servicio, "describir"):
            raise ParametroReservaInvalidoError("El servicio asociado no es valido.")
        if isinstance(duracion, bool) or not isinstance(duracion, (int, float)) or duracion <= 0:
            raise ParametroReservaInvalidoError("La duracion debe ser mayor que cero.")
        if getattr(servicio, "disponible", True) is False:
            raise ServicioNoDisponibleError(
                f"El servicio '{getattr(servicio, 'codigo', 'SIN_CODIGO')}' no esta disponible."
            )

        self._codigo_reserva = codigo_reserva.strip()
        self._cliente = cliente.strip()
        self._servicio = servicio
        self._duracion = duracion
        self._impuesto = impuesto
        self._descuento = descuento
        self._recargo_extra = recargo_extra
        self._estado = "PENDIENTE"
        self._fecha_registro = fecha_registro or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            self._costo_total = self._servicio.calcular_costo(
                duracion=self._duracion,
                impuesto=self._impuesto,
                descuento=self._descuento,
                recargo_extra=self._recargo_extra
            )
        except Exception as exc:
            # Encadenamiento de excepciones para conservar la causa original
            raise ParametroReservaInvalidoError(
                f"Error al calcular el costo de la reserva '{self._codigo_reserva}'."
            ) from exc

    @property
    def codigo_reserva(self) -> str:
        return self._codigo_reserva

    @property
    def cliente(self) -> str:
        return self._cliente

    @property
    def servicio(self) -> object:
        return self._servicio

    @property
    def estado(self) -> str:
        return self._estado

    @property
    def costo_total(self) -> float:
        return self._costo_total

    def confirmar(self) -> None:
        if self._estado == "CANCELADA":
            raise EstadoReservaInvalidoError(
                f"No se puede confirmar '{self._codigo_reserva}' porque esta cancelada."
            )
        if self._estado == "CONFIRMADA":
            raise EstadoReservaInvalidoError(
                f"La reserva '{self._codigo_reserva}' ya esta confirmada."
            )
        self._estado = "CONFIRMADA"
        if hasattr(self._servicio, "disponible"):
            self._servicio.disponible = False

    def cancelar(self) -> None:
        if self._estado == "CANCELADA":
            raise EstadoReservaInvalidoError(
                f"La reserva '{self._codigo_reserva}' ya fue cancelada."
            )
        self._estado = "CANCELADA"
        if hasattr(self._servicio, "disponible"):
            self._servicio.disponible = True

    def resumen(self) -> str:
        cod_srv = getattr(self._servicio, "codigo", "SRV")
        nom_srv = getattr(self._servicio, "nombre", "Servicio")
        return (
            f"[{self._codigo_reserva}] Cliente: {self._cliente} | Servicio: {cod_srv} ({nom_srv}) | "
            f"Total: ${self._costo_total:.2f} | Estado: {self._estado}"
        )


class GestorReservas:
    """Administra reservas en memoria con trazabilidad en log."""

    def __init__(self):
        self._reservas: Dict[str, Reserva] = {}

    def crear_reserva(
        self,
        codigo_reserva: str,
        cliente: str,
        servicio: object,
        duracion: int,
        impuesto: float = 0.19,
        descuento: float = 0.0,
        recargo_extra: float = 0.0
    ) -> Reserva:
        try:
            codigo_limpio = codigo_reserva.strip() if isinstance(codigo_reserva, str) else ""
            if codigo_limpio in self._reservas:
                raise ParametroReservaInvalidoError(
                    f"Ya existe una reserva con el codigo '{codigo_limpio}'."
                )
            reserva = Reserva(
                codigo_reserva=codigo_reserva,
                cliente=cliente,
                servicio=servicio,
                duracion=duracion,
                impuesto=impuesto,
                descuento=descuento,
                recargo_extra=recargo_extra
            )
        except ErrorReserva as exc:
            logger.error(f"CREAR_RESERVA fallo | codigo={codigo_reserva} | motivo={exc}")
            raise
        except Exception as exc:
            logger.critical(f"CREAR_RESERVA inesperado | codigo={codigo_reserva} | detalle={exc}")
            raise ParametroReservaInvalidoError("Fallo interno al crear la reserva.") from exc
        else:
            self._reservas[reserva.codigo_reserva] = reserva
            logger.info(
                f"CREAR_RESERVA ok | codigo={reserva.codigo_reserva} | "
                f"cliente={reserva.cliente} | total={reserva.costo_total:.2f}"
            )
            return reserva
        finally:
            logger.info(f"AUDITORIA crear_reserva finalizada | intento_codigo={codigo_reserva}")

    def obtener_reserva(self, codigo_reserva: str) -> Reserva:
        if not isinstance(codigo_reserva, str) or codigo_reserva.strip() not in self._reservas:
            msg = f"No se encontro la reserva '{codigo_reserva}'."
            logger.warning(f"CONSULTAR_RESERVA no_encontrada | {msg}")
            raise ReservaNoEncontradaError(msg)
        return self._reservas[codigo_reserva.strip()]

    def confirmar_reserva(self, codigo_reserva: str) -> Reserva:
        try:
            reserva = self.obtener_reserva(codigo_reserva)
            reserva.confirmar()
        except ErrorReserva as exc:
            logger.error(f"CONFIRMAR_RESERVA fallo | codigo={codigo_reserva} | motivo={exc}")
            raise
        else:
            logger.info(f"CONFIRMAR_RESERVA ok | codigo={reserva.codigo_reserva}")
            return reserva
        finally:
            logger.info(f"AUDITORIA confirmar_reserva finalizada | codigo={codigo_reserva}")

    def cancelar_reserva(self, codigo_reserva: str) -> Reserva:
        try:
            reserva = self.obtener_reserva(codigo_reserva)
            reserva.cancelar()
        except ErrorReserva as exc:
            logger.error(f"CANCELAR_RESERVA fallo | codigo={codigo_reserva} | motivo={exc}")
            raise
        else:
            logger.info(f"CANCELAR_RESERVA ok | codigo={reserva.codigo_reserva}")
            return reserva
        finally:
            logger.info(f"AUDITORIA cancelar_reserva finalizada | codigo={codigo_reserva}")

    def listar_reservas(self) -> List[Reserva]:
        return list(self._reservas.values())


if __name__ == "__main__":
    class _ServicioSimulacion:
        def __init__(self, codigo: str, nombre: str, tarifa: float, disponible: bool = True, romper_calculo: bool = False):
            self.codigo = codigo
            self.nombre = nombre
            self.tarifa = tarifa
            self.disponible = disponible
            self.romper_calculo = romper_calculo

        def calcular_costo(self, duracion: int, impuesto: float = 0.19, descuento: float = 0.0, recargo_extra: float = 0.0) -> float:
            if self.romper_calculo:
                raise ZeroDivisionError("Simulacion de falla matematica en tarifa")
            base = (self.tarifa * duracion) + recargo_extra
            return round(base * (1 - descuento) * (1 + impuesto), 2)

        def describir(self) -> str:
            return f"{self.codigo} - {self.nombre}"

    gestor = GestorReservas()
    sala = _ServicioSimulacion("SAL-01", "Sala Conferencias", 60000, True)
    equipo = _ServicioSimulacion("EQP-01", "Laptop Profesional", 25000, True)
    no_disp = _ServicioSimulacion("SRV-09", "Servidor Dedicado", 120000, False)
    bug_srv = _ServicioSimulacion("BUG-01", "Servicio con Falla", 40000, True, romper_calculo=True)

    simulaciones = [
        ("Sim 1 - Reserva valida sala", lambda: print("OK:", gestor.crear_reserva("R01", "Andres Garcia", sala, 3, descuento=0.1).resumen())),
        ("Sim 2 - Confirmar reserva R01", lambda: print("OK:", gestor.confirmar_reserva("R01").resumen())),
        ("Sim 3 - Reserva valida equipo", lambda: print("OK:", gestor.crear_reserva("R02", "Laura Perez", equipo, 2).resumen())),
        ("Sim 4 - Cancelar reserva R02", lambda: print("OK:", gestor.cancelar_reserva("R02").resumen())),
        ("Sim 5 - Error servicio no disponible", lambda: gestor.crear_reserva("R03", "Carlos Ruiz", no_disp, 1)),
        ("Sim 6 - Error duracion invalida", lambda: gestor.crear_reserva("R04", "Sofia Gomez", sala, -2)),
        ("Sim 7 - Error cliente vacio", lambda: gestor.crear_reserva("R05", "   ", sala, 2)),
        ("Sim 8 - Error codigo duplicado", lambda: gestor.crear_reserva("R01", "Pedro Diaz", equipo, 1)),
        ("Sim 9 - Error confirmar ya cancelada", lambda: gestor.confirmar_reserva("R02")),
        ("Sim 10 - Error encadenado en calculo", lambda: gestor.crear_reserva("R06", "Elena Castro", bug_srv, 2)),
    ]

    for titulo, accion in simulaciones:
        try:
            accion()
        except ErrorReserva as err:
            print(f"{titulo} -> Controlado ({type(err).__name__}): {err}")
            if err.__cause__ is not None:
                print(f"   Causa encadenada: {type(err.__cause__).__name__}: {err.__cause__}")

    print("\n--- CONTENIDO DEL LOG (ultimas lineas) ---")
    with open("sistema_software_fj.log", "r", encoding="utf-8") as f:
        lineas = f.readlines()
        for linea in lineas[-25:]:
            print(linea.strip())
