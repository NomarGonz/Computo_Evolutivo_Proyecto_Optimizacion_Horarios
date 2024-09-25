import pandas as pd
import random
from datetime import datetime, timedelta
import math

#Parámetros del algoritmo evolutivo
tamaño_poblacion = 40
tasa_mutacion = 0.2
num_generaciones = 10
semestre = 0
tamaño_cromosoma = 0
num_ejecuciones = 10  #Número de ejecuciones independientes para calcular MBF y SR
umbral_exito = 2  #Umbral de horas muertas para considerar una solución exitosa

#Variables para las métricas
mejores_fitness = []
ejecuciones_exitosas = 0

#Materias por semestre
materias_por_semestre = {
    1: ["I5288", "I5247", "IG738", "IL340", "IL342", "IL341"],
    2: ["IL352", "IL345", "IL344", "IL343", "IL353", "LT251"],
    3: ["I5289", "IB056", "IL347", "IL346", "IL363", "IL349"],
    4: ["IL354", "IB067", "IL348", "IL365", "IL362", "IL350"],
    5: ["IL355", "IL356", "IL366", "IL361", "IL364", "IL369"],
    6: ["IL351", "IL367", "CB224", "IL358"],
    7: ["IL357", "IL370", "IL372"],
    8: ["IL359", "IL368", "IL373"],
    9: ["IL360", "IL371", "IL374"],
}

#Solicitar semestre
def solicitar_semestre():
    global semestre
    semestre = int(input("Capture el semestre del alumno: "))
    validar_semestre()

def validar_semestre():
    global tamaño_cromosoma
    if semestre in [1, 2, 3, 4, 5]:
        tamaño_cromosoma = 6
    elif semestre == 6:
        tamaño_cromosoma = 4
    elif semestre in [7, 8, 9]:
        tamaño_cromosoma = 3
    else:
        print("Ingrese un semestre válido: ")
        solicitar_semestre()

solicitar_semestre()

#Cargar el archivo Excel
ruta_archivo = 'oferta_limpia2.xlsx'
df = pd.read_excel(ruta_archivo)
claves_semestre = materias_por_semestre[semestre]
df_filtrado = df[df['Clave'].isin(claves_semestre)]
conteo_claves = df_filtrado['Clave'].value_counts().reindex(claves_semestre, fill_value=0)

for clave in claves_semestre:
    nombre_materia = df_filtrado[df_filtrado['Clave'] == clave]['Materia'].iloc[0] if clave in conteo_claves else "Materia no encontrada"
    cantidad = conteo_claves[clave]
    #print(f"Clave: {clave}, Materia: {nombre_materia}, Cantidad: {cantidad}")

secciones_por_materia = df_filtrado.groupby('Clave').size()

def generar_cromosoma():
    cromosoma = []
    for clave in claves_semestre:
        num_secciones = secciones_por_materia.get(clave, 0)
        seccion_aleatoria = random.randint(0, num_secciones - 1) if num_secciones > 0 else 0
        cromosoma.append(seccion_aleatoria)
    return cromosoma

def obtener_horarios_por_dia(cromosoma, df_filtrado, claves_semestre):
    dias = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado']
    horarios_por_dia = {dia: [] for dia in dias}

    for i, seccion_index in enumerate(cromosoma):
        clave = claves_semestre[i]
        seccion = 'D' + f"{seccion_index + 1:02}"  #Convertir índice a código de sección
        horarios_seccion = df_filtrado[(df_filtrado['Clave'] == clave) & (df_filtrado['Sec'] == seccion)]

        if not horarios_seccion.empty:
            for _, fila in horarios_seccion.iterrows():
                for dia in dias:
                    for suffix in ['', '2', '3']:
                        dia_columna = str(fila[dia + suffix]).strip()
                        if dia_columna and dia_columna != '.':
                            inicio = parse_time(fila[f'Hora inicio{suffix or 1}'])
                            fin = parse_time(fila[f'Hora final{suffix or 1}'])
                            horarios_por_dia[dia].append((inicio, fin, clave, seccion))

    for dia in dias:
        horarios_por_dia[dia].sort(key=lambda x: x[0])

    return horarios_por_dia

def funcion_fitness(cromosoma, df_filtrado, claves_semestre):
    horas_semanales_libres = 0
    penalizacion = 0
    horarios_semanales = obtener_horarios_por_dia(cromosoma, df_filtrado, claves_semestre)

    for dia, horarios in horarios_semanales.items():
        horarios_del_dia = [(inicio, fin) for inicio, fin, _, _ in horarios]
        horas_libres = calcular_horas_libres(horarios_del_dia)
        horas_semanales_libres += horas_libres

        #Revisar si las materias cruzan horarios
        for i in range(len(horarios_del_dia)):
            for j in range(i + 1, len(horarios_del_dia)):
                inicio1, fin1 = horarios_del_dia[i]
                inicio2, fin2 = horarios_del_dia[j]
                if inicio1 < fin2 and inicio2 < fin1:  #Si se encuentra un conflicto de horario
                    penalizacion += 8  #Penalización por cruce de horario
    
    #print(f"Total de horas libres por semana: {horas_semanales_libres:.2f}, Penalización por solapamientos: {penalizacion}")
    fitness = horas_semanales_libres + penalizacion
    #print(f"Fitness: {fitness}")
    return fitness


def parse_time(time_str):
    time_str = time_str.strip().replace('a. m.', 'AM').replace('p. m.', 'PM')
    return datetime.strptime(time_str, '%I:%M:%S %p').time()

def calcular_horas_libres(horarios):
    if not horarios:
        return 0

    horarios.sort()
    total_libre = timedelta()
    fin_anterior = horarios[0][1]

    for inicio, fin in horarios[1:]:
        inicio_actual = datetime.combine(datetime.today(), inicio)
        fin_anterior_dt = datetime.combine(datetime.today(), fin_anterior)
        if inicio_actual > fin_anterior_dt:
            libre = inicio_actual - fin_anterior_dt
            total_libre += libre

        fin_anterior = fin 

    return total_libre.total_seconds() / 3600

def generar_poblacion_inicial(tamaño_poblacion, tamaño_cromosoma):
    return [generar_cromosoma() for _ in range(tamaño_poblacion)]

def seleccion_por_torneo(poblacion, k=4):
    seleccionados = []
    
    #Primer torneo
    torneo1 = random.sample(poblacion, k)
    #print("Torneo 1:")
    #print(torneo1)
    mejor1 = min(torneo1, key=lambda cromo: funcion_fitness(cromo, df_filtrado, claves_semestre))
    #print(f"Ganador del Torneo 1: {mejor1}")
    seleccionados.append(mejor1)  # Mejor del primer torneo

    #Remover los cromosomas que ya participaron en el primer torneo
    poblacion_restante = [cromo for cromo in poblacion if cromo not in torneo1]
    #Segundo torneo
    torneo2 = random.sample(poblacion_restante, k)
    #print("Torneo 2:")
    #print(torneo2)
    mejor2 = min(torneo2, key=lambda cromo: funcion_fitness(cromo, df_filtrado, claves_semestre))
    #print(f"Ganador del Torneo 2: {mejor2}")
    seleccionados.append(mejor2)  #Mejor del segundo torneo
    
    return seleccionados


def recombinacion_discreta(padre1, padre2):
    hijo = []
    for i in range(len(padre1)):
        if random.random() < 0.5:
            hijo.append(padre1[i])
        else:
            hijo.append(padre2[i])
    return hijo

def mutacion(hijo, tasa_mutacion):
    for i in range(len(hijo)):
        if random.random() < tasa_mutacion:
            clave = claves_semestre[i]
            secciones_unicas = df_filtrado[df_filtrado['Clave'] == clave]['Sec'].drop_duplicates().tolist()
            if secciones_unicas:
                nuevo_valor = random.randint(0, len(secciones_unicas) - 1)
                hijo[i] = nuevo_valor
    return hijo

def imprimir_horario(horarios_semanales):
    print("\nHorario generado:")
    for dia, horarios in horarios_semanales.items():
        if horarios:
            print(f"\n{dia}:")
            for inicio, fin, clave, seccion in horarios:
                print(f"  {clave} - Sección: {seccion}, de {inicio.strftime('%I:%M %p')} a {fin.strftime('%I:%M %p')}")

#Generar la población inicial
poblacion = generar_poblacion_inicial(tamaño_poblacion, tamaño_cromosoma)

for ejecucion in range(num_ejecuciones):
    print(f"\nEjecución {ejecucion + 1}/{num_ejecuciones}")
    
    #Generar la población inicial para esta ejecución
    poblacion = generar_poblacion_inicial(tamaño_poblacion, tamaño_cromosoma)
    
    #Algoritmo evolutivo
    for generacion in range(num_generaciones):
        print(f"\nGeneración {generacion+1}")
        
        padres = seleccion_por_torneo(poblacion)
        hijo = recombinacion_discreta(padres[0], padres[1])
        hijo_mutado = mutacion(hijo, tasa_mutacion)
        
        peor = max(poblacion, key=lambda cromo: funcion_fitness(cromo, df_filtrado, claves_semestre))
        poblacion.remove(peor)
        poblacion.append(hijo_mutado)
    
    #Encontrar el mejor cromosoma al final de la ejecución
    mejor_cromosoma = min(poblacion, key=lambda cromo: funcion_fitness(cromo, df_filtrado, claves_semestre))
    mejor_fitness = funcion_fitness(mejor_cromosoma, df_filtrado, claves_semestre)
    
    #Guardar el mejor valor de fitness para esta ejecución
    mejores_fitness.append(mejor_fitness)
    
    #Comprobar si la ejecución fue exitosa (menos de 8 horas muertas)
    if mejor_fitness < umbral_exito:
        ejecuciones_exitosas += 1
    
    #Imprimir el mejor horario generado en esta ejecución
    horarios_semanales = obtener_horarios_por_dia(mejor_cromosoma, df_filtrado, claves_semestre)
    imprimir_horario(horarios_semanales)
    print(f"Total de horas muertas: {mejor_fitness}")


#Calcular el MBF (Mean Best Fitness)
MBF = sum(mejores_fitness) / len(mejores_fitness)
print(f"\nMean Best Fitness (MBF) después de {num_ejecuciones} ejecuciones: {MBF}")

#Calcular el SR (Success Rate)
SR = ejecuciones_exitosas / num_ejecuciones
print(f"Success Rate (SR): {SR * 100}%")

#Cálculo de la varianza del mejor fitness
varianza_fitness = sum((fitness - MBF) ** 2 for fitness in mejores_fitness) / len(mejores_fitness)
desviacion_estandar_fitness = math.sqrt(varianza_fitness)

print(f"Varianza del Mejor Fitness: {varianza_fitness}")
print(f"Desviación estándar del Mejor Fitness: {desviacion_estandar_fitness}")



