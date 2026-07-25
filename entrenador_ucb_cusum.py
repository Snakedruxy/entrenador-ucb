import math

class EntrenadorRitmoUnico:
    def __init__(self, nivel_actual="Normal"):
        # ---------- DATOS DE LA CANCION ----------
        self.cancion = None
        self.nivel_actual = nivel_actual
        self.niveles = ["Normal", "Hard", "Expert", "Master"]
        self.historial_completo = []
        self.historial_ronda = []
        self.INTENTOS_MINIMOS_PARA_SUBIR = 2

        # ---------- PARAMETROS UCB ----------
        self.umbral_subir = 95
        self.umbral_bajar = 85
        self.intentos_maximos = 10
        self.factor_exploracion = 2
        self.intentos_totales = 0

        # ---------- PARAMETROS CUSUM ----------
        self.cusum_alza = 0.0
        self.cusum_bajada = 0.0
        self.cusum_umbral = 3.0
        self.cusum_media_referencia = None
        self.ventana_cusum = 5

        # ---------- PARAMETROS DE TENDENCIA ----------
        self.ventana_tendencia = 4
        self.umbral_pendiente = -3.0

        # ---------- ESTADO DE ALERTA ----------
        self.alerta_empeoramiento = False
        self.cambio_detectado = False

    # ================================================
    # 1. GESTION DE LA CANCION
    # ================================================

    def iniciar_cancion(self, nombre, precision_inicial):
        self.cancion = {
            "nombre": nombre,
            "precision_inicial": precision_inicial,
            "precision_actual": precision_inicial,
            "intentos": 0,
            "historial": [precision_inicial],
            "mejoras": [0],
            "recompensa_acumulada": 0
        }
        self.historial_ronda = [precision_inicial]
        self.intentos_totales = 0

        # Resetear CUSUM para nueva cancion
        self.cusum_alza = 0.0
        self.cusum_bajada = 0.0
        self.cusum_media_referencia = precision_inicial
        self.alerta_empeoramiento = False
        self.cambio_detectado = False

    def agregar_intento(self, nueva_precision):
        if not self.cancion:
            return False

        anterior = self.cancion["precision_actual"]
        mejora = nueva_precision - anterior

        self.cancion["precision_actual"] = nueva_precision
        self.cancion["intentos"] += 1
        self.cancion["historial"].append(nueva_precision)
        self.cancion["mejoras"].append(mejora)
        self.historial_ronda.append(nueva_precision)
        self.intentos_totales += 1

        # Actualizar CUSUM
        self._actualizar_cusum(nueva_precision)

        return True

    # ================================================
    # 2. CALCULO DE UCB ADAPTADO
    # ================================================

    def calcular_ucb_continuar(self):
        if not self.cancion or self.cancion["intentos"] == 0:
            return 999.0

        # Recompensa: precision actual normalizada
        recompensa = self.cancion["precision_actual"] / 100

        # Exploracion dinamica
        if self.cancion["intentos"] <= 3:
            exploracion = 1.5 * math.sqrt(
                self.factor_exploracion * math.log(self.intentos_totales + 1) /
                max(self.cancion["intentos"], 1)
            )
        else:
            exploracion = math.sqrt(
                self.factor_exploracion * math.log(self.intentos_totales + 1) /
                self.cancion["intentos"]
            )

        # Penalizacion si esta empeorando
        penalizacion = 0.0
        if self.alerta_empeoramiento:
            penalizacion = -1.0

        return recompensa + exploracion + penalizacion

    def calcular_ucb_parar(self):
        if not self.cancion:
            return 999.0

        # UCB ADAPTADO: Contexto del minimo de intentos
        intentos_realizados = len(self.historial_ronda) - 1
        if intentos_realizados < self.INTENTOS_MINIMOS_PARA_SUBIR:
            return 0.5  # Muy bajo, fuerza a "continuar"

        # Si ya tiene muchos intentos
        if self.cancion["intentos"] >= self.intentos_maximos:
            return 10.0

        # UCB ADAPTADO: Contexto del dominio de la cancion
        if self.cancion["precision_actual"] >= self.umbral_subir:
            return 5.0

        if self.alerta_empeoramiento:
            return 4.0

        return 1.0

    # ================================================
    # 3. CUSUM - DETECCION DE CAMBIOS
    # ================================================

    def _actualizar_cusum(self, precision):
        """Actualiza los acumuladores CUSUM para detectar cambios"""
        if self.cusum_media_referencia is None:
            self.cusum_media_referencia = precision
            return

        desviacion_alza = precision - self.cusum_media_referencia
        self.cusum_alza = max(0, self.cusum_alza + desviacion_alza)

        desviacion_bajada = self.cusum_media_referencia - precision
        self.cusum_bajada = max(0, self.cusum_bajada + desviacion_bajada)

        if self.cusum_alza > self.cusum_umbral:
            self.cambio_detectado = True
            self.cusum_alza = 0.0
            self.cusum_media_referencia = precision

        if self.cusum_bajada > self.cusum_umbral:
            self.cambio_detectado = True
            self.alerta_empeoramiento = True
            self.cusum_bajada = 0.0
            self.cusum_media_referencia = precision

    def detectar_cambio_estadistico(self):
        """Detecta cambios significativos usando CUSUM"""
        if not self.cancion or len(self.cancion["historial"]) < self.ventana_cusum:
            return False

        ultimos = self.cancion["historial"][-self.ventana_cusum:]
        anteriores = self.cancion["historial"][:-self.ventana_cusum]

        if not anteriores:
            return False

        media_anterior = sum(anteriores) / len(anteriores)
        media_actual = sum(ultimos) / len(ultimos)

        if len(anteriores) > 1:
            varianza = sum((x - media_anterior) ** 2 for x in anteriores) / len(anteriores)
            desviacion = math.sqrt(varianza)
        else:
            desviacion = 5.0

        desviacion = max(desviacion, 2.0)

        cambio = (media_actual - media_anterior) / desviacion

        if cambio < -1.5:
            print(f"\n[CUSUM] EMPEORAMIENTO DETECTADO")
            print(f"   Media anterior: {media_anterior:.1f}%")
            print(f"   Media actual: {media_actual:.1f}%")
            print(f"   Cambio: {cambio:.2f} desviaciones")
            self.alerta_empeoramiento = True
            return True

        if cambio > 1.5:
            print(f"\n[CUSUM] MEJORA DETECTADA")
            print(f"   Media anterior: {media_anterior:.1f}%")
            print(f"   Media actual: {media_actual:.1f}%")
            print(f"   Cambio: {cambio:.2f} desviaciones")
            self.alerta_empeoramiento = False
            return True

        return False

    # ================================================
    # 4. DETECCION DE TENDENCIA (REGRESION)
    # ================================================

    def detectar_tendencia(self):
        """Detecta empeoramiento progresivo usando regresion lineal simple"""
        if not self.cancion or len(self.cancion["historial"]) < self.ventana_tendencia:
            return False

        datos = self.cancion["historial"][1:][-self.ventana_tendencia:]
        if len(datos) < self.ventana_tendencia:
            return False

        n = len(datos)
        x = list(range(n))
        y = datos

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] * x[i] for i in range(n))

        denominador = n * sum_x2 - sum_x * sum_x
        if denominador == 0:
            return False

        pendiente = (n * sum_xy - sum_x * sum_y) / denominador

        if pendiente < self.umbral_pendiente:
            print(f"\n[TENDENCIA DETECTADA]")
            print(f"   Pendiente: {pendiente:.2f} puntos/intento")
            print(f"   Ultimos {n}: {datos}")
            self.alerta_empeoramiento = True
            return True

        return False

    # ================================================
    # 5. CALCULO DE PROMEDIO
    # ================================================

    def calcular_promedio_ronda(self):
        if len(self.historial_ronda) <= 1:
            return 0
        intentos = self.historial_ronda[1:]
        return sum(intentos) / len(intentos) if intentos else 0

    # ================================================
    # 6. RECOMENDACION PRINCIPAL
    # ================================================

    def recomendar(self):
        if not self.cancion:
            return "No hay cancion activa", None

        if self.detectar_cambio_estadistico():
            print("\n[CUSUM] detecto un cambio en tu rendimiento")

        if self.detectar_tendencia():
            print("\n[ALERTA] Estas empeorando progresivamente")

        ucb_continuar = self.calcular_ucb_continuar()
        ucb_parar = self.calcular_ucb_parar()

        self._mostrar_info(ucb_continuar, ucb_parar)

        if self.alerta_empeoramiento:
            print("\n[ALERTA] Estas empeorando")
            print("   Recomendacion: Cambia de cancion")
            return self._evaluar_cambio()

        if self.cancion["intentos"] >= self.intentos_maximos:
            print("\n[INFO] Has llegado al maximo de intentos")
            return self._evaluar_cambio()

        if ucb_continuar > ucb_parar:
            print(f"\nRECOMENDACION: Sigue practicando")
            return "continuar", None
        else:
            print("\nRecomendacion: Cambia de cancion")
            return self._evaluar_cambio()

    # ================================================
    # 7. EVALUACION DE NIVEL
    # ================================================

    def _evaluar_cambio(self):
        """Evalua si sube, baja o se queda en el nivel (basado en el promedio de TODA la sesion)"""
        promedio = self.calcular_promedio_ronda()
        idx_actual = self.niveles.index(self.nivel_actual)

        intentos_realizados = len(self.historial_ronda) - 1
        if intentos_realizados < self.INTENTOS_MINIMOS_PARA_SUBIR:
            print(f"\n[INFO] Necesitas al menos {self.INTENTOS_MINIMOS_PARA_SUBIR} intentos para evaluar")
            print(f"   Intentos actuales: {intentos_realizados}")
            print(f"   Te faltan: {self.INTENTOS_MINIMOS_PARA_SUBIR - intentos_realizados} intento(s)")
            return "quedarse", self.nivel_actual

        print(f"\n{'='*60}")
        print("[EVALUACION DE NIVEL]")
        print(f"{'='*60}")
        print(f"   Promedio de la SESION: {promedio:.1f}%")
        print(f"   Objetivo para subir: {self.umbral_subir}%")
        print(f"   Bajarias si promedio < {self.umbral_bajar}%")
        print(f"   Nivel actual: {self.nivel_actual}")

        if promedio >= self.umbral_subir and idx_actual < len(self.niveles) - 1:
            nuevo = self.niveles[idx_actual + 1]
            print(f"   SUBES -> {nuevo}")
            self.nivel_actual = nuevo
            return "subir", nuevo

        elif promedio < self.umbral_bajar and idx_actual > 0:
            nuevo = self.niveles[idx_actual - 1]
            print(f"   BAJAS -> {nuevo}")
            self.nivel_actual = nuevo
            return "bajar", nuevo

        else:
            print(f"   Te quedas en {self.nivel_actual}")
            return "quedarse", self.nivel_actual

    # ================================================
    # 8. MOSTRAR INFORMACION
    # ================================================

    def _mostrar_info(self, ucb_continuar, ucb_parar):
        print(f"\n{'='*60}")
        print(f"ENTRENADOR UCB + CUSUM")
        print(f"{'='*60}")
        print(f"Cancion: {self.cancion['nombre']}")
        print(f"Nivel: {self.nivel_actual}")
        print(f"Intento: {self.cancion['intentos']}")
        print(f"Precision: {self.cancion['precision_actual']:.1f}%")
        print(f"{'='*60}")

        print("\nHISTORIAL RECIENTE:")
        historial = self.cancion["historial"][1:]
        mostrar = historial[-5:] if len(historial) > 5 else historial
        for i, p in enumerate(mostrar, len(historial) - len(mostrar) + 1):
            estado = "[OK]" if p >= self.umbral_subir else "[MEDIO]" if p >= 80 else "[BAJO]"
            print(f"   Intento {i}: {p:.1f}% {estado}")

        print(f"\nCUSUM:")
        print(f"   Alza acumulada: {self.cusum_alza:.2f}")
        print(f"   Bajada acumulada: {self.cusum_bajada:.2f}")
        print(f"   Umbral: {self.cusum_umbral}")

        print(f"\nUCB ADAPTADO:")
        print(f"   UCB continuar: {ucb_continuar:.3f}")
        print(f"   UCB parar: {ucb_parar:.3f}")

        intentos_realizados = len(self.historial_ronda) - 1
        if intentos_realizados < self.INTENTOS_MINIMOS_PARA_SUBIR:
            print(f"\nContexto:")
            print(f"   Necesitas {self.INTENTOS_MINIMOS_PARA_SUBIR} intentos para evaluar")
            print(f"   Intentos actuales: {intentos_realizados}")
            print(f"   Te faltan: {self.INTENTOS_MINIMOS_PARA_SUBIR - intentos_realizados}")

        if self.alerta_empeoramiento:
            print(f"\n[ALERTA] Estas empeorando")

    # ================================================
    # 9. RESUMEN FINAL
    # ================================================

    def mostrar_resumen_final(self):
        print(f"\n{'='*70}")
        print("[RESUMEN COMPLETO]")
        print(f"{'='*70}")

        if self.cancion:
            print(f"\nCancion: {self.cancion['nombre']}")
            print(f"   Nivel final: {self.nivel_actual}")
            print(f"   Mejora total: +{self.cancion['precision_actual'] - self.cancion['precision_inicial']:.1f}%")
            print(f"   Intentos: {self.cancion['intentos']}")

            print("\nEvolucion:")
            for i, p in enumerate(self.cancion['historial'][1:], 1):
                estado = "[OK]" if p >= self.umbral_subir else "[MEDIO]" if p >= 80 else "[BAJO]"
                print(f"   Intento {i}: {p:.1f}% {estado}")

            if self.alerta_empeoramiento:
                print("\n[ADVERTENCIA] Se detecto empeoramiento durante la sesion")

        print(f"\n{'='*70}")
        print("Sigue asi. La constancia es la clave.")
        print(f"{'='*70}")


# ================================================
# PROGRAMA PRINCIPAL
# ================================================

def main():
    print(f"{'='*60}")
    print("ENTRENADOR UCB + CUSUM (ADAPTADO)")
    print(f"{'='*60}")
    print("UCB Adaptado al contexto del usuario")
    print("   Subes al 95% de promedio")
    print("   Bajas si promedio < 85%")
    print("   Detecta empeoramiento y recomienda parar")
    print("   Minimo 2 intentos para subir de nivel")
    print("   UCB se adapta a tus necesidades")
    print(f"{'='*60}")

    print("\nNIVELES DISPONIBLES:")
    print("   1. Normal")
    print("   2. Hard")
    print("   3. Expert")
    print("   4. Master")

    while True:
        try:
            opcion = int(input("\nElige tu nivel actual (1-4): "))
            if 1 <= opcion <= 4:
                niveles = ["Normal", "Hard", "Expert", "Master"]
                nivel_actual = niveles[opcion - 1]
                break
            print("[ERROR] Debe ser 1-4")
        except ValueError:
            print("[ERROR] Numero valido")

    entrenador = EntrenadorRitmoUnico(nivel_actual=nivel_actual)

    print(f"\n--- Cancion ---")
    nombre = input("Nombre: ").strip()
    while not nombre:
        nombre = input("Nombre (no vacio): ").strip()

    while True:
        try:
            precision = float(input("Precision actual (0-100): "))
            if 0 <= precision <= 100:
                break
            print("[ERROR] Debe ser 0-100")
        except ValueError:
            print("[ERROR] Numero valido")

    entrenador.iniciar_cancion(nombre, precision)

    print(f"\nComienza a practicar")
    print(f"   UCB + CUSUM adaptados te guiaran")
    print(f"   Objetivo: Llegar a 95% para subir")
    print(f"   Necesitas {entrenador.INTENTOS_MINIMOS_PARA_SUBIR} intentos para subir")
    print(f"   El sistema se adapta a tu progreso")
    print(f"{'='*60}")

    while True:
        decision, nuevo_nivel = entrenador.recomendar()

        if decision == "continuar":
            while True:
                try:
                    nueva = float(input(f"\nNueva precision: "))
                    if 0 <= nueva <= 100:
                        break
                    print("[ERROR] Debe ser 0-100")
                except ValueError:
                    print("[ERROR] Numero valido")

            entrenador.agregar_intento(nueva)

            print(f"\nProgreso:")
            print(f"   Precision: {entrenador.cancion['precision_actual']:.1f}%")
            print(f"   Intentos: {entrenador.cancion['intentos']}")

            if not input("\nContinuar? (s/n): ").lower() == 's':
                print("\nHasta luego")
                entrenador.mostrar_resumen_final()
                break

        elif decision in ["subir", "bajar", "quedarse"]:
            print(f"\nNivel actualizado: {entrenador.nivel_actual}")

            if decision == "subir":
                print("Felicidades. Subiste de nivel")
            elif decision == "bajar":
                print("No te preocupes, baja de nivel y sigue practicando")

            print(f"\nQuieres empezar con otra cancion?")
            if not input("(s/n): ").lower() == 's':
                entrenador.mostrar_resumen_final()
                break

            print(f"\n--- Nueva Cancion ---")
            nombre = input("Nombre: ").strip()
            while not nombre:
                nombre = input("Nombre (no vacio): ").strip()

            while True:
                try:
                    precision = float(input("Precision actual (0-100): "))
                    if 0 <= precision <= 100:
                        break
                    print("[ERROR] Debe ser 0-100")
                except ValueError:
                    print("[ERROR] Numero valido")

            entrenador.iniciar_cancion(nombre, precision)
            print(f"\nNueva cancion. Nivel: {entrenador.nivel_actual}")
            print(f"   Necesitas {entrenador.INTENTOS_MINIMOS_PARA_SUBIR} intentos para subir")

        else:
            break


if __name__ == "__main__":
    main()import math

class EntrenadorRitmoUnico:
    def __init__(self, nivel_actual="Normal"):
        # ---------- DATOS DE LA CANCION ----------
        self.cancion = None
        self.nivel_actual = nivel_actual
        self.niveles = ["Normal", "Hard", "Expert", "Master"]
        self.historial_completo = []
        self.historial_ronda = []
        self.INTENTOS_MINIMOS_PARA_SUBIR = 2

        # ---------- PARAMETROS UCB ----------
        self.umbral_subir = 95
        self.umbral_bajar = 85
        self.intentos_maximos = 10
        self.factor_exploracion = 2
        self.intentos_totales = 0

        # ---------- PARAMETROS CUSUM ----------
        self.cusum_alza = 0.0
        self.cusum_bajada = 0.0
        self.cusum_umbral = 3.0
        self.cusum_media_referencia = None
        self.ventana_cusum = 5

        # ---------- PARAMETROS DE TENDENCIA ----------
        self.ventana_tendencia = 4
        self.umbral_pendiente = -3.0

        # ---------- ESTADO DE ALERTA ----------
        self.alerta_empeoramiento = False
        self.cambio_detectado = False

    # ================================================
    # 1. GESTION DE LA CANCION
    # ================================================

    def iniciar_cancion(self, nombre, precision_inicial):
        self.cancion = {
            "nombre": nombre,
            "precision_inicial": precision_inicial,
            "precision_actual": precision_inicial,
            "intentos": 0,
            "historial": [precision_inicial],
            "mejoras": [0],
            "recompensa_acumulada": 0
        }
        self.historial_ronda = [precision_inicial]
        self.intentos_totales = 0

        # Resetear CUSUM para nueva cancion
        self.cusum_alza = 0.0
        self.cusum_bajada = 0.0
        self.cusum_media_referencia = precision_inicial
        self.alerta_empeoramiento = False
        self.cambio_detectado = False

    def agregar_intento(self, nueva_precision):
        if not self.cancion:
            return False

        anterior = self.cancion["precision_actual"]
        mejora = nueva_precision - anterior

        self.cancion["precision_actual"] = nueva_precision
        self.cancion["intentos"] += 1
        self.cancion["historial"].append(nueva_precision)
        self.cancion["mejoras"].append(mejora)
        self.historial_ronda.append(nueva_precision)
        self.intentos_totales += 1

        # Actualizar CUSUM
        self._actualizar_cusum(nueva_precision)

        return True

    # ================================================
    # 2. CALCULO DE UCB ADAPTADO
    # ================================================

    def calcular_ucb_continuar(self):
        if not self.cancion or self.cancion["intentos"] == 0:
            return 999.0

        # Recompensa: precision actual normalizada
        recompensa = self.cancion["precision_actual"] / 100

        # Exploracion dinamica
        if self.cancion["intentos"] <= 3:
            exploracion = 1.5 * math.sqrt(
                self.factor_exploracion * math.log(self.intentos_totales + 1) /
                max(self.cancion["intentos"], 1)
            )
        else:
            exploracion = math.sqrt(
                self.factor_exploracion * math.log(self.intentos_totales + 1) /
                self.cancion["intentos"]
            )

        # Penalizacion si esta empeorando
        penalizacion = 0.0
        if self.alerta_empeoramiento:
            penalizacion = -1.0

        return recompensa + exploracion + penalizacion

    def calcular_ucb_parar(self):
        if not self.cancion:
            return 999.0

        # UCB ADAPTADO: Contexto del minimo de intentos
        intentos_realizados = len(self.historial_ronda) - 1
        if intentos_realizados < self.INTENTOS_MINIMOS_PARA_SUBIR:
            return 0.5  # Muy bajo, fuerza a "continuar"

        # Si ya tiene muchos intentos
        if self.cancion["intentos"] >= self.intentos_maximos:
            return 10.0

        # UCB ADAPTADO: Contexto del dominio de la cancion
        if self.cancion["precision_actual"] >= self.umbral_subir:
            return 5.0

        if self.alerta_empeoramiento:
            return 4.0

        return 1.0

    # ================================================
    # 3. CUSUM - DETECCION DE CAMBIOS
    # ================================================

    def _actualizar_cusum(self, precision):
        """Actualiza los acumuladores CUSUM para detectar cambios"""
        if self.cusum_media_referencia is None:
            self.cusum_media_referencia = precision
            return

        desviacion_alza = precision - self.cusum_media_referencia
        self.cusum_alza = max(0, self.cusum_alza + desviacion_alza)

        desviacion_bajada = self.cusum_media_referencia - precision
        self.cusum_bajada = max(0, self.cusum_bajada + desviacion_bajada)

        if self.cusum_alza > self.cusum_umbral:
            self.cambio_detectado = True
            self.cusum_alza = 0.0
            self.cusum_media_referencia = precision

        if self.cusum_bajada > self.cusum_umbral:
            self.cambio_detectado = True
            self.alerta_empeoramiento = True
            self.cusum_bajada = 0.0
            self.cusum_media_referencia = precision

    def detectar_cambio_estadistico(self):
        """Detecta cambios significativos usando CUSUM"""
        if not self.cancion or len(self.cancion["historial"]) < self.ventana_cusum:
            return False

        ultimos = self.cancion["historial"][-self.ventana_cusum:]
        anteriores = self.cancion["historial"][:-self.ventana_cusum]

        if not anteriores:
            return False

        media_anterior = sum(anteriores) / len(anteriores)
        media_actual = sum(ultimos) / len(ultimos)

        if len(anteriores) > 1:
            varianza = sum((x - media_anterior) ** 2 for x in anteriores) / len(anteriores)
            desviacion = math.sqrt(varianza)
        else:
            desviacion = 5.0

        desviacion = max(desviacion, 2.0)

        cambio = (media_actual - media_anterior) / desviacion

        if cambio < -1.5:
            print(f"\n[CUSUM] EMPEORAMIENTO DETECTADO")
            print(f"   Media anterior: {media_anterior:.1f}%")
            print(f"   Media actual: {media_actual:.1f}%")
            print(f"   Cambio: {cambio:.2f} desviaciones")
            self.alerta_empeoramiento = True
            return True

        if cambio > 1.5:
            print(f"\n[CUSUM] MEJORA DETECTADA")
            print(f"   Media anterior: {media_anterior:.1f}%")
            print(f"   Media actual: {media_actual:.1f}%")
            print(f"   Cambio: {cambio:.2f} desviaciones")
            self.alerta_empeoramiento = False
            return True

        return False

    # ================================================
    # 4. DETECCION DE TENDENCIA (REGRESION)
    # ================================================

    def detectar_tendencia(self):
        """Detecta empeoramiento progresivo usando regresion lineal simple"""
        if not self.cancion or len(self.cancion["historial"]) < self.ventana_tendencia:
            return False

        datos = self.cancion["historial"][1:][-self.ventana_tendencia:]
        if len(datos) < self.ventana_tendencia:
            return False

        n = len(datos)
        x = list(range(n))
        y = datos

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] * x[i] for i in range(n))

        denominador = n * sum_x2 - sum_x * sum_x
        if denominador == 0:
            return False

        pendiente = (n * sum_xy - sum_x * sum_y) / denominador

        if pendiente < self.umbral_pendiente:
            print(f"\n[TENDENCIA DETECTADA]")
            print(f"   Pendiente: {pendiente:.2f} puntos/intento")
            print(f"   Ultimos {n}: {datos}")
            self.alerta_empeoramiento = True
            return True

        return False

    # ================================================
    # 5. CALCULO DE PROMEDIO
    # ================================================

    def calcular_promedio_ronda(self):
        if len(self.historial_ronda) <= 1:
            return 0
        intentos = self.historial_ronda[1:]
        return sum(intentos) / len(intentos) if intentos else 0

    # ================================================
    # 6. RECOMENDACION PRINCIPAL
    # ================================================

    def recomendar(self):
        if not self.cancion:
            return "No hay cancion activa", None

        if self.detectar_cambio_estadistico():
            print("\n[CUSUM] detecto un cambio en tu rendimiento")

        if self.detectar_tendencia():
            print("\n[ALERTA] Estas empeorando progresivamente")

        ucb_continuar = self.calcular_ucb_continuar()
        ucb_parar = self.calcular_ucb_parar()

        self._mostrar_info(ucb_continuar, ucb_parar)

        if self.alerta_empeoramiento:
            print("\n[ALERTA] Estas empeorando")
            print("   Recomendacion: Cambia de cancion")
            return self._evaluar_cambio()

        if self.cancion["intentos"] >= self.intentos_maximos:
            print("\n[INFO] Has llegado al maximo de intentos")
            return self._evaluar_cambio()

        if ucb_continuar > ucb_parar:
            print(f"\nRECOMENDACION: Sigue practicando")
            return "continuar", None
        else:
            print("\nRecomendacion: Cambia de cancion")
            return self._evaluar_cambio()

    # ================================================
    # 7. EVALUACION DE NIVEL
    # ================================================

    def _evaluar_cambio(self):
        """Evalua si sube, baja o se queda en el nivel (basado en el promedio de TODA la sesion)"""
        promedio = self.calcular_promedio_ronda()
        idx_actual = self.niveles.index(self.nivel_actual)

        intentos_realizados = len(self.historial_ronda) - 1
        if intentos_realizados < self.INTENTOS_MINIMOS_PARA_SUBIR:
            print(f"\n[INFO] Necesitas al menos {self.INTENTOS_MINIMOS_PARA_SUBIR} intentos para evaluar")
            print(f"   Intentos actuales: {intentos_realizados}")
            print(f"   Te faltan: {self.INTENTOS_MINIMOS_PARA_SUBIR - intentos_realizados} intento(s)")
            return "quedarse", self.nivel_actual

        print(f"\n{'='*60}")
        print("[EVALUACION DE NIVEL]")
        print(f"{'='*60}")
        print(f"   Promedio de la SESION: {promedio:.1f}%")
        print(f"   Objetivo para subir: {self.umbral_subir}%")
        print(f"   Bajarias si promedio < {self.umbral_bajar}%")
        print(f"   Nivel actual: {self.nivel_actual}")

        if promedio >= self.umbral_subir and idx_actual < len(self.niveles) - 1:
            nuevo = self.niveles[idx_actual + 1]
            print(f"   SUBES -> {nuevo}")
            self.nivel_actual = nuevo
            return "subir", nuevo

        elif promedio < self.umbral_bajar and idx_actual > 0:
            nuevo = self.niveles[idx_actual - 1]
            print(f"   BAJAS -> {nuevo}")
            self.nivel_actual = nuevo
            return "bajar", nuevo

        else:
            print(f"   Te quedas en {self.nivel_actual}")
            return "quedarse", self.nivel_actual

    # ================================================
    # 8. MOSTRAR INFORMACION
    # ================================================

    def _mostrar_info(self, ucb_continuar, ucb_parar):
        print(f"\n{'='*60}")
        print(f"ENTRENADOR UCB + CUSUM")
        print(f"{'='*60}")
        print(f"Cancion: {self.cancion['nombre']}")
        print(f"Nivel: {self.nivel_actual}")
        print(f"Intento: {self.cancion['intentos']}")
        print(f"Precision: {self.cancion['precision_actual']:.1f}%")
        print(f"{'='*60}")

        print("\nHISTORIAL RECIENTE:")
        historial = self.cancion["historial"][1:]
        mostrar = historial[-5:] if len(historial) > 5 else historial
        for i, p in enumerate(mostrar, len(historial) - len(mostrar) + 1):
            estado = "[OK]" if p >= self.umbral_subir else "[MEDIO]" if p >= 80 else "[BAJO]"
            print(f"   Intento {i}: {p:.1f}% {estado}")

        print(f"\nCUSUM:")
        print(f"   Alza acumulada: {self.cusum_alza:.2f}")
        print(f"   Bajada acumulada: {self.cusum_bajada:.2f}")
        print(f"   Umbral: {self.cusum_umbral}")

        print(f"\nUCB ADAPTADO:")
        print(f"   UCB continuar: {ucb_continuar:.3f}")
        print(f"   UCB parar: {ucb_parar:.3f}")

        intentos_realizados = len(self.historial_ronda) - 1
        if intentos_realizados < self.INTENTOS_MINIMOS_PARA_SUBIR:
            print(f"\nContexto:")
            print(f"   Necesitas {self.INTENTOS_MINIMOS_PARA_SUBIR} intentos para evaluar")
            print(f"   Intentos actuales: {intentos_realizados}")
            print(f"   Te faltan: {self.INTENTOS_MINIMOS_PARA_SUBIR - intentos_realizados}")

        if self.alerta_empeoramiento:
            print(f"\n[ALERTA] Estas empeorando")

    # ================================================
    # 9. RESUMEN FINAL
    # ================================================

    def mostrar_resumen_final(self):
        print(f"\n{'='*70}")
        print("[RESUMEN COMPLETO]")
        print(f"{'='*70}")

        if self.cancion:
            print(f"\nCancion: {self.cancion['nombre']}")
            print(f"   Nivel final: {self.nivel_actual}")
            print(f"   Mejora total: +{self.cancion['precision_actual'] - self.cancion['precision_inicial']:.1f}%")
            print(f"   Intentos: {self.cancion['intentos']}")

            print("\nEvolucion:")
            for i, p in enumerate(self.cancion['historial'][1:], 1):
                estado = "[OK]" if p >= self.umbral_subir else "[MEDIO]" if p >= 80 else "[BAJO]"
                print(f"   Intento {i}: {p:.1f}% {estado}")

            if self.alerta_empeoramiento:
                print("\n[ADVERTENCIA] Se detecto empeoramiento durante la sesion")

        print(f"\n{'='*70}")
        print("Sigue asi. La constancia es la clave.")
        print(f"{'='*70}")


# ================================================
# PROGRAMA PRINCIPAL
# ================================================

def main():
    print(f"{'='*60}")
    print("ENTRENADOR UCB + CUSUM (ADAPTADO)")
    print(f"{'='*60}")
    print("UCB Adaptado al contexto del usuario")
    print("   Subes al 95% de promedio")
    print("   Bajas si promedio < 85%")
    print("   Detecta empeoramiento y recomienda parar")
    print("   Minimo 2 intentos para subir de nivel")
    print("   UCB se adapta a tus necesidades")
    print(f"{'='*60}")

    print("\nNIVELES DISPONIBLES:")
    print("   1. Normal")
    print("   2. Hard")
    print("   3. Expert")
    print("   4. Master")

    while True:
        try:
            opcion = int(input("\nElige tu nivel actual (1-4): "))
            if 1 <= opcion <= 4:
                niveles = ["Normal", "Hard", "Expert", "Master"]
                nivel_actual = niveles[opcion - 1]
                break
            print("[ERROR] Debe ser 1-4")
        except ValueError:
            print("[ERROR] Numero valido")

    entrenador = EntrenadorRitmoUnico(nivel_actual=nivel_actual)

    print(f"\n--- Cancion ---")
    nombre = input("Nombre: ").strip()
    while not nombre:
        nombre = input("Nombre (no vacio): ").strip()

    while True:
        try:
            precision = float(input("Precision actual (0-100): "))
            if 0 <= precision <= 100:
                break
            print("[ERROR] Debe ser 0-100")
        except ValueError:
            print("[ERROR] Numero valido")

    entrenador.iniciar_cancion(nombre, precision)

    print(f"\nComienza a practicar")
    print(f"   UCB + CUSUM adaptados te guiaran")
    print(f"   Objetivo: Llegar a 95% para subir")
    print(f"   Necesitas {entrenador.INTENTOS_MINIMOS_PARA_SUBIR} intentos para subir")
    print(f"   El sistema se adapta a tu progreso")
    print(f"{'='*60}")

    while True:
        decision, nuevo_nivel = entrenador.recomendar()

        if decision == "continuar":
            while True:
                try:
                    nueva = float(input(f"\nNueva precision: "))
                    if 0 <= nueva <= 100:
                        break
                    print("[ERROR] Debe ser 0-100")
                except ValueError:
                    print("[ERROR] Numero valido")

            entrenador.agregar_intento(nueva)

            print(f"\nProgreso:")
            print(f"   Precision: {entrenador.cancion['precision_actual']:.1f}%")
            print(f"   Intentos: {entrenador.cancion['intentos']}")

            if not input("\nContinuar? (s/n): ").lower() == 's':
                print("\nHasta luego")
                entrenador.mostrar_resumen_final()
                break

        elif decision in ["subir", "bajar", "quedarse"]:
            print(f"\nNivel actualizado: {entrenador.nivel_actual}")

            if decision == "subir":
                print("Felicidades. Subiste de nivel")
            elif decision == "bajar":
                print("No te preocupes, baja de nivel y sigue practicando")

            print(f"\nQuieres empezar con otra cancion?")
            if not input("(s/n): ").lower() == 's':
                entrenador.mostrar_resumen_final()
                break

            print(f"\n--- Nueva Cancion ---")
            nombre = input("Nombre: ").strip()
            while not nombre:
                nombre = input("Nombre (no vacio): ").strip()

            while True:
                try:
                    precision = float(input("Precision actual (0-100): "))
                    if 0 <= precision <= 100:
                        break
                    print("[ERROR] Debe ser 0-100")
                except ValueError:
                    print("[ERROR] Numero valido")

            entrenador.iniciar_cancion(nombre, precision)
            print(f"\nNueva cancion. Nivel: {entrenador.nivel_actual}")
            print(f"   Necesitas {entrenador.INTENTOS_MINIMOS_PARA_SUBIR} intentos para subir")

        else:
            break


if __name__ == "__main__":
    main()
