"""
Módulo de entidades base y servicios especializados para Software FJ.
Implementa abstracción, herencia, polimorfismo y cálculo de costos con opciones.
"""

from abc import ABC, abstractmethod


class EntidadSistema(ABC):
    """Clase abstracta base que representa cualquier entidad del sistema."""

    def __init__(self, codigo: str):
        # Valida que el código identificador no esté vacío antes de asignarlo
        if not isinstance(codigo, str) or not codigo.strip():
            raise ValueError("El código de la entidad debe ser un texto no vacío.")
        # Encapsulación del código identificador de la entidad
        self._codigo = codigo.strip()

    @property
    def codigo(self) -> str:
        """Retorna el código identificador de la entidad."""
        return self._codigo

    @abstractmethod
    def describir(self) -> str:
        """Método abstracto que debe ser implementado por cada entidad."""
        pass


class Servicio(EntidadSistema, ABC):
    """Clase abstracta base para los servicios ofrecidos por Software FJ."""

    def __init__(self, codigo: str, nombre: str, tarifa_base: float, disponible: bool = True):
        # Inicializa el código heredado de EntidadSistema
        super().__init__(codigo)
        # Encapsulación de atributos principales del servicio
        self._nombre = nombre
        self._tarifa_base = tarifa_base
        self._disponible = disponible
        # Ejecuta la validación específica al crear el servicio
        self.validar_parametros()

    @property
    def nombre(self) -> str:
        """Retorna el nombre del servicio."""
        return self._nombre

    @property
    def tarifa_base(self) -> float:
        """Retorna la tarifa base del servicio."""
        return self._tarifa_base

    @property
    def disponible(self) -> bool:
        """Indica si el servicio está disponible para reservar."""
        return self._disponible

    @disponible.setter
    def disponible(self, estado: bool) -> None:
        """Actualiza la disponibilidad verificando que el valor sea booleano."""
        if not isinstance(estado, bool):
            raise ValueError("La disponibilidad debe ser un valor booleano (True o False).")
        self._disponible = estado

    @abstractmethod
    def validar_parametros(self) -> None:
        """Valida los parámetros propios de cada servicio especializado."""
        pass

    @abstractmethod
    def calcular_costo(
        self,
        duracion: int,
        impuesto: float = 0.19,
        descuento: float = 0.0,
        recargo_extra: float = 0.0
    ) -> float:
        """
        Calcula el costo total según duración y parámetros opcionales
        (impuesto, descuento y recargo extra).
        """
        pass

    def _validar_argumentos_costo(self, duracion: int, impuesto: float, descuento: float, recargo_extra: float) -> None:
        """Valida que los valores numéricos del cálculo de costo sean coherentes."""
        # Verifica duración válida mayor a cero
        if isinstance(duracion, bool) or not isinstance(duracion, (int, float)) or duracion <= 0:
            raise ValueError("La duración debe ser un número mayor que cero.")
        # Verifica que el porcentaje de impuesto no sea negativo
        if impuesto < 0:
            raise ValueError("El impuesto no puede ser negativo.")
        # Verifica que el descuento esté en un rango válido entre 0 y 1 (0% a 100%)
        if not (0.0 <= descuento <= 1.0):
            raise ValueError("El descuento debe estar entre 0.0 y 1.0.")
        # Verifica que el recargo adicional no sea negativo
        if recargo_extra < 0:
            raise ValueError("El recargo extra no puede ser negativo.")


class ReservaSala(Servicio):
    """Servicio especializado para reserva de salas en Software FJ."""

    def __init__(self, codigo: str, nombre: str, tarifa_base: float, capacidad: int, disponible: bool = True):
        # Almacena la capacidad máxima de personas de la sala
        self._capacidad = capacidad
        super().__init__(codigo, nombre, tarifa_base, disponible)

    @property
    def capacidad(self) -> int:
        """Retorna la capacidad máxima de la sala."""
        return self._capacidad

    def validar_parametros(self) -> None:
        """Valida nombre, tarifa base y capacidad de la sala."""
        if not isinstance(self._nombre, str) or not self._nombre.strip():
            raise ValueError("El nombre de la sala no puede estar vacío.")
        if isinstance(self._tarifa_base, bool) or not isinstance(self._tarifa_base, (int, float)) or self._tarifa_base <= 0:
            raise ValueError("La tarifa base de la sala debe ser mayor que cero.")
        if isinstance(self._capacidad, bool) or not isinstance(self._capacidad, int) or self._capacidad <= 0:
            raise ValueError("La capacidad de la sala debe ser un entero mayor que cero.")

    def calcular_costo(
        self,
        duracion: int,
        impuesto: float = 0.19,
        descuento: float = 0.0,
        recargo_extra: float = 0.0
    ) -> float:
        """Calcula el costo total de reservar la sala aplicando opciones."""
        self._validar_argumentos_costo(duracion, impuesto, descuento, recargo_extra)
        # Calcula subtotal por horas más recargos adicionales
        subtotal = (self._tarifa_base * duracion) + recargo_extra
        # Aplica el descuento porcentual
        con_descuento = subtotal * (1 - descuento)
        # Aplica el impuesto y redondea a dos decimales
        return round(con_descuento * (1 + impuesto), 2)

    def describir(self) -> str:
        """Retorna una descripción legible de la sala."""
        estado = "Disponible" if self._disponible else "No disponible"
        return (
            f"[Sala | Código: {self._codigo}] {self._nombre} - "
            f"Capacidad: {self._capacidad} personas - Tarifa/h: ${self._tarifa_base:.2f} - {estado}"
        )


class AlquilerEquipo(Servicio):
    """Servicio especializado para alquiler de equipos tecnológicos."""

    GAMAS_VALIDAS = ("Estándar", "Profesional", "Servidor")

    def __init__(self, codigo: str, nombre: str, tarifa_base: float, gama: str, disponible: bool = True):
        # Define la gama del equipo antes de validar parámetros
        self._gama = gama
        super().__init__(codigo, nombre, tarifa_base, disponible)

    @property
    def gama(self) -> str:
        """Retorna la gama del equipo."""
        return self._gama

    def validar_parametros(self) -> None:
        """Valida nombre, tarifa base y gama permitida del equipo."""
        if not isinstance(self._nombre, str) or not self._nombre.strip():
            raise ValueError("El nombre del equipo no puede estar vacío.")
        if isinstance(self._tarifa_base, bool) or not isinstance(self._tarifa_base, (int, float)) or self._tarifa_base <= 0:
            raise ValueError("La tarifa base del equipo debe ser mayor que cero.")
        if self._gama not in self.GAMAS_VALIDAS:
            raise ValueError(f"La gama del equipo debe ser una de: {', '.join(self.GAMAS_VALIDAS)}.")

    def calcular_costo(
        self,
        duracion: int,
        impuesto: float = 0.19,
        descuento: float = 0.0,
        recargo_extra: float = 0.0
    ) -> float:
        """Calcula el costo del alquiler considerando la gama del equipo."""
        self._validar_argumentos_costo(duracion, impuesto, descuento, recargo_extra)
        # Aplica un multiplicador adicional si el equipo es de gama Servidor
        factor_gama = 1.25 if self._gama == "Servidor" else 1.0
        subtotal = (self._tarifa_base * duracion * factor_gama) + recargo_extra
        con_descuento = subtotal * (1 - descuento)
        return round(con_descuento * (1 + impuesto), 2)

    def describir(self) -> str:
        """Retorna una descripción legible del equipo."""
        estado = "Disponible" if self._disponible else "No disponible"
        return (
            f"[Equipo | Código: {self._codigo}] {self._nombre} - "
            f"Gama: {self._gama} - Tarifa/h: ${self._tarifa_base:.2f} - {estado}"
        )


class AsesoriaEspecializada(Servicio):
    """Servicio especializado para asesorías técnicas y consultoría."""

    def __init__(self, codigo: str, nombre: str, tarifa_base: float, especialidad: str, disponible: bool = True):
        # Almacena el área de especialidad de la asesoría
        self._especialidad = especialidad
        super().__init__(codigo, nombre, tarifa_base, disponible)

    @property
    def especialidad(self) -> str:
        """Retorna el área de especialidad."""
        return self._especialidad

    def validar_parametros(self) -> None:
        """Valida nombre, tarifa base y especialidad de la asesoría."""
        if not isinstance(self._nombre, str) or not self._nombre.strip():
            raise ValueError("El nombre de la asesoría no puede estar vacío.")
        if isinstance(self._tarifa_base, bool) or not isinstance(self._tarifa_base, (int, float)) or self._tarifa_base <= 0:
            raise ValueError("La tarifa base de la asesoría debe ser mayor que cero.")
        if not isinstance(self._especialidad, str) or not self._especialidad.strip():
            raise ValueError("La especialidad de la asesoría no puede estar vacía.")

    def calcular_costo(
        self,
        duracion: int,
        impuesto: float = 0.19,
        descuento: float = 0.0,
        recargo_extra: float = 0.0
    ) -> float:
        """Calcula el costo de la asesoría según duración y parámetros opcionales."""
        self._validar_argumentos_costo(duracion, impuesto, descuento, recargo_extra)
        subtotal = (self._tarifa_base * duracion) + recargo_extra
        con_descuento = subtotal * (1 - descuento)
        return round(con_descuento * (1 + impuesto), 2)

    def describir(self) -> str:
        """Retorna una descripción legible de la asesoría."""
        estado = "Disponible" if self._disponible else "No disponible"
        return (
            f"[Asesoría | Código: {self._codigo}] {self._nombre} - "
            f"Especialidad: {self._especialidad} - Tarifa/h: ${self._tarifa_base:.2f} - {estado}"
        )
    
